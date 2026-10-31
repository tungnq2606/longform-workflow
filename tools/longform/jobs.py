"""Disk-backed job queue for Studio: every long step (Claude box, agy, render) is a job.

  jobs.register(jobs.Kind("claude", "claude", build_argv))      # done once by the module that owns the kind
  jobs.enqueue("claude", {"message": "..."}, "001-bach-dang", "Claude: ...")
  jobs.Runner({"claude": 1, "agy": 4}).start()                  # Studio only

Each job is <state>/jobs/<id>.json plus <id>.log. A kind's `build` turns params into argv at enqueue time, so the
browser never sends a command. Lanes cap how many jobs of one sort run at once. Pause starts nothing new and lets
running jobs finish. A job left "running" by a Studio that died becomes "interrupted" (never rerun silently).
"""
import glob
import json
import os
import signal
import subprocess
import threading
import time
import uuid

from tools.longform import inbox, paths

WS = paths.WS
STATUS_VI = {"queued": "chờ", "running": "đang chạy", "done": "xong", "failed": "hỏng", "stopped": "đã dừng",
             "interrupted": "bị ngắt"}


class Kind:
    def __init__(self, name, lane, build, cwd=WS, on_line=None, on_end=None):
        self.name, self.lane, self.build, self.cwd, self.on_line, self.on_end = name, lane, build, cwd, on_line, on_end


KINDS = {}
_lock = threading.Lock()
_procs = {}  # job id -> Popen, for jobs running in this process
_stopping = set()


def register(kind):
    KINDS[kind.name] = kind


def _dir():
    d = os.path.join(paths.state(), "jobs")
    os.makedirs(d, exist_ok=True)
    return d


def _write(job):
    path = os.path.join(_dir(), job["id"] + ".json")
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(job, f, ensure_ascii=False, indent=1)
    os.replace(path + ".tmp", path)


def get(job_id):
    try:
        with open(os.path.join(_dir(), job_id + ".json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _all():
    out = []
    for p in glob.glob(os.path.join(_dir(), "*.json")):
        try:
            with open(p, encoding="utf-8") as f:
                out.append(json.load(f))
        except (OSError, ValueError):
            pass
    return out


def _update(job_id, **kw):
    job = get(job_id)
    job.update(kw)
    _write(job)
    return job


def enqueue(kind, params, project, label):
    if kind not in KINDS:
        raise ValueError("không có loại job %s" % kind)
    k = KINDS[kind]
    argv = k.build(params)
    job = {"id": uuid.uuid4().hex, "kind": kind, "lane": k.lane, "params": params, "argv": argv, "project": project,
           "label": label, "status": "queued", "seq": time.time_ns(), "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "started": None, "ended": None, "exit": None, "error": None, "pid": None}
    _write(job)
    return job


def list_jobs(limit=50):
    jobs = _all()
    running = sorted((j for j in jobs if j["status"] == "running"), key=lambda j: j["seq"])
    queued = sorted((j for j in jobs if j["status"] == "queued"), key=lambda j: j["seq"])
    ended = sorted((j for j in jobs if j["status"] not in ("running", "queued")), key=lambda j: -j["seq"])
    return (running + queued + ended)[:limit]


def read_log(job_id, offset=0):
    try:
        with open(os.path.join(_dir(), job_id + ".log"), "rb") as f:
            f.seek(offset)
            data = f.read()
    except OSError:
        return "", offset
    return data.decode("utf-8", "replace"), offset + len(data)


def _pause_file():
    return os.path.join(paths.state(), "pause.json")


def paused():
    try:
        with open(_pause_file(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"on": False, "reason": "", "since": None}


def set_paused(on, reason=""):
    with open(_pause_file() + ".tmp", "w", encoding="utf-8") as f:
        json.dump({"on": bool(on), "reason": reason if on else "", "since": time.strftime("%Y-%m-%dT%H:%M:%S") if on else None},
                  f, ensure_ascii=False)
    os.replace(_pause_file() + ".tmp", _pause_file())


def _signal_group(p, sig):
    """Jobs run in their own process group, so a stop also reaches the tools a job started."""
    try:
        os.killpg(p.pid, sig)
    except OSError:
        pass


def _kill_later(p):
    try:
        p.wait(5)
    except subprocess.TimeoutExpired:
        _signal_group(p, signal.SIGKILL)


def _terminate(p):
    _signal_group(p, signal.SIGTERM)
    threading.Thread(target=_kill_later, args=(p,), daemon=True).start()


def stop(job_id):
    with _lock:
        job = get(job_id)
        if not job:
            return False
        if job["status"] == "queued":
            _update(job_id, status="stopped", ended=time.strftime("%Y-%m-%dT%H:%M:%S"))
            return True
        if job["status"] != "running":
            return False
        _stopping.add(job_id)  # _run checks this right after it starts the process, so an early stop is not lost
        p = _procs.get(job_id)
    if p is not None:
        _terminate(p)
    return True


def _fail(job, error=None, code=None):
    job = _update(job["id"], status="failed", ended=time.strftime("%Y-%m-%dT%H:%M:%S"), exit=code, error=error)
    msg = "Job hỏng: %s (%s)" % (job["label"], error or "mã %s" % code)
    inbox.add(job["project"], "job_failed", msg, key="job:%s" % job["id"])
    return job


def _execute(job, k, log):
    try:
        cwd = k.cwd(job) if callable(k.cwd) else k.cwd
        p = subprocess.Popen(job["argv"], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                             encoding="utf-8", errors="replace", bufsize=1, start_new_session=True)
    except FileNotFoundError:
        return _fail(job, error="không tìm thấy lệnh %s" % job["argv"][0])
    except (OSError, ValueError) as e:
        return _fail(job, error="không chạy được lệnh %s: %s" % (job["argv"][0], getattr(e, "strerror", None) or e))
    with _lock:
        _procs[job["id"]] = p
        early_stop = job["id"] in _stopping
    if early_stop:
        _terminate(p)
    try:
        job = _update(job["id"], pid=p.pid)
        with open(log, "a", encoding="utf-8") as fh:
            for line in p.stdout:
                text = line.rstrip("\n")
                if k.on_line:
                    text = k.on_line(job, text)
                if text is None:
                    continue
                fh.write(text if text.endswith("\n") else text + "\n")
                fh.flush()
        code = p.wait()
    except Exception:
        _terminate(p)
        raise
    finally:
        with _lock:
            _procs.pop(job["id"], None)
            stopped = job["id"] in _stopping
            _stopping.discard(job["id"])
    ended = time.strftime("%Y-%m-%dT%H:%M:%S")
    if stopped:
        return _update(job["id"], status="stopped", ended=ended, exit=code)
    if code == 0:
        return _update(job["id"], status="done", ended=ended, exit=0)
    return _fail(job, code=code)


def _run(job):
    k = KINDS.get(job["kind"])
    log = os.path.join(_dir(), job["id"] + ".log")
    if k is None:
        return _fail(job, error="loại job %s không còn" % job["kind"])
    try:
        job = _execute(job, k, log)
    except Exception as e:  # noqa: BLE001  any crash ends the job as failed, so its lane never stays blocked
        job = _fail(job, error="lỗi trong Studio: %s" % e)
    if k.on_end:
        try:
            k.on_end(job)
        except Exception as e:  # noqa: BLE001  a broken callback must not kill the runner
            with open(log, "a", encoding="utf-8") as fh:
                fh.write("[on_end lỗi: %s]\n" % e)
    return job


def recover():
    n = 0
    for job in _all():
        if job["status"] == "running":
            _update(job["id"], status="interrupted", ended=time.strftime("%Y-%m-%dT%H:%M:%S"))
            inbox.add(job["project"], "job_interrupted", "Job bị ngắt (Studio tắt giữa chừng): %s" % job["label"],
                      key="job:%s" % job["id"])
            n += 1
    return n


class Runner:
    def __init__(self, lanes, poll=0.5):
        self.lanes, self.poll = dict(lanes), poll
        self._halt = threading.Event()
        self._thread = None

    def tick(self):
        if paused()["on"]:
            return
        with _lock:
            jobs = _all()
            busy = {}
            for j in jobs:
                if j["status"] == "running":
                    busy[j["lane"]] = busy.get(j["lane"], 0) + 1
            for j in sorted((j for j in jobs if j["status"] == "queued"), key=lambda j: j["seq"]):
                if busy.get(j["lane"], 0) >= self.lanes.get(j["lane"], 1):
                    continue
                busy[j["lane"]] = busy.get(j["lane"], 0) + 1
                j = _update(j["id"], status="running", started=time.strftime("%Y-%m-%dT%H:%M:%S"))
                threading.Thread(target=_run, args=(j,), daemon=True).start()

    def _loop(self):
        while not self._halt.wait(self.poll):
            try:
                self.tick()
            except Exception as e:  # noqa: BLE001  keep scheduling; the next tick retries
                print("jobs: tick failed: %s" % e)

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._halt.set()
