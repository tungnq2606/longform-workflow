const $ = (id) => document.getElementById(id);
// Fixed settings: no configuration needed.
const OPTIONS = { folder: "tts", ext: "mp3", pause: 3, genTimeout: 180, downloadPick: "first" };
let items = [];
let armed = false;
let armTimer = null;
let running = false;

const log = (s) => {
  const el = $("log");
  el.textContent += s + "\n";
  el.scrollTop = el.scrollHeight;
};

const save = () => chrome.storage.local.set({ items });

function render() {
  const ul = $("list");
  ul.innerHTML = "";
  items.forEach((it) => {
    const li = document.createElement("li");
    const a = document.createElement("span");
    a.textContent = it.name + ".mp3";
    const b = document.createElement("span");
    b.textContent = it.text.length + " ký tự";
    const x = document.createElement("button");
    x.textContent = "×";
    x.title = "Xóa file này";
    x.className = "x";
    x.disabled = running;
    x.onclick = async () => {
      items = items.filter((i) => i.name !== it.name);
      await save();
      render();
    };
    li.append(a, b, x);
    ul.appendChild(li);
  });
  const total = items.reduce((n, i) => n + i.text.length, 0);
  $("total").textContent = items.length ? `${items.length} file, ${total} ký tự (mỗi lần Generate tốn credit)` : "";
  $("run").disabled = !items.length || running;
  $("clearAll").style.display = items.length && !running ? "inline" : "none";
}

async function addFiles(files) {
  for (const f of files) {
    if (!/\.txt$/i.test(f.name)) continue;
    const text = (await f.text()).replace(/\r\n/g, "\n").trim();
    const name = f.name.replace(/\.txt$/i, "").replace(/[^\w.\-]+/g, "_");
    items = items.filter((x) => x.name !== name);
    if (text) items.push({ name, text });
  }
  items.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));
  await save();
  render();
}

async function findTab() {
  const urls = ["https://elevenlabs.io/*", "https://*.elevenlabs.io/*"];
  const [active] = await chrome.tabs.query({ active: true, currentWindow: true, url: urls });
  if (active) return active.id;
  const any = await chrome.tabs.query({ url: urls });
  return any.length ? any[0].id : null;
}

async function ensureContent(tabId) {
  try {
    const r = await chrome.tabs.sendMessage(tabId, { type: "ping" });
    if (r && r.ok) return true;
  } catch (e) {}
  try {
    await chrome.scripting.executeScript({ target: { tabId }, files: ["content.js"] });
    const r = await chrome.tabs.sendMessage(tabId, { type: "ping" });
    return !!(r && r.ok);
  } catch (e) {
    return false;
  }
}

function disarm() {
  armed = false;
  clearTimeout(armTimer);
  const total = items.reduce((n, i) => n + i.text.length, 0);
  $("run").textContent = "Run";
}

$("pick").onchange = (e) => addFiles(e.target.files);
document.body.ondragover = (e) => e.preventDefault();
document.body.ondrop = (e) => {
  e.preventDefault();
  addFiles(e.dataTransfer.files);
};

$("run").onclick = async () => {
  if (!items.length) return;
  if (!armed) {
    armed = true;
    const total = items.reduce((n, i) => n + i.text.length, 0);
    $("run").textContent = `Bấm lần nữa để chạy ${items.length} file (${total} ký tự)`;
    armTimer = setTimeout(disarm, 6000);
    return;
  }
  disarm();
  const tabId = await findTab();
  if (!tabId) return log("Mở trang Text to Speech của ElevenLabs (đã chọn giọng) rồi bấm Run lại.");
  if (!(await ensureContent(tabId))) return log("Không kết nối được trang. Tải lại trang ElevenLabs rồi thử lại.");
  $("log").textContent = "";
  $("stop").style.display = "block";
  running = true;
  render();
  $("run").disabled = true;
  log(`Bắt đầu ${items.length} file. Lưu vào Downloads/${OPTIONS.folder}/`);
  await chrome.tabs.sendMessage(tabId, { type: "start", items, options: OPTIONS });
  chrome.storage.session.set({ lastTab: tabId });
};

$("stop").onclick = async () => {
  const { lastTab } = await chrome.storage.session.get("lastTab");
  if (lastTab) chrome.tabs.sendMessage(lastTab, { type: "stop" }).catch(() => {});
  log("Đã yêu cầu dừng.");
};

$("clearAll").onclick = async () => {
  items = [];
  await save();
  render();
};

$("win").onclick = () => {
  chrome.windows.create({ url: chrome.runtime.getURL("popup.html"), type: "popup", width: 360, height: 520 });
  window.close();
};

chrome.runtime.onMessage.addListener((msg) => {
  if (!msg) return;
  if (msg.type === "progress") log(msg.msg);
  if (msg.type === "finished") {
    const bad = msg.results.filter((r) => !r.ok).length;
    log(`Xong: ${msg.results.length - bad} ok, ${bad} lỗi.`);
    $("stop").style.display = "none";
    running = false;
    render();
  }
});

chrome.storage.local.get("items").then((st) => {
  items = st.items || [];
  render();
});
