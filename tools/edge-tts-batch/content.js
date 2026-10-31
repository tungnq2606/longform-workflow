// Runs on elevenlabs.io. Pastes each text into the Text to Speech box, clicks
// Generate, waits for the audio, clicks Download. The service worker renames
// the file. Selectors are found by heuristics and can be overridden in the panel.
(() => {
  if (window.__ttsBatchLoaded) return;
  window.__ttsBatchLoaded = true;

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  let stopFlag = false;
  let running = false;
  let downloadWaiter = null;
  let overlay = null;

  const area = (el) => {
    const r = el.getBoundingClientRect();
    return r.width * r.height;
  };
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none";
  };
  const queryAll = (sel) => {
    try {
      return [...document.querySelectorAll(sel)].filter(visible);
    } catch (e) {
      return [];
    }
  };
  const labelOf = (el) =>
    ((el.getAttribute("aria-label") || "") + " " + (el.getAttribute("title") || "") + " " + (el.innerText || "")).trim();

  // Stable test ids seen in the saved ElevenLabs page (checked 2026-10-21).
  const DEFAULT_SEL = {
    text: '[data-testid="tts-editor"]',
    generate: '[data-testid="tts-generate"]',
    download: '[data-testid="tts-download-latest-button"]',
  };

  function findTextInput(o) {
    for (const sel of [o.textSelector, DEFAULT_SEL.text]) {
      if (!sel) continue;
      const l = queryAll(sel);
      if (l[0]) return l[0];
    }
    const c = [...queryAll("textarea"), ...queryAll('[contenteditable="true"]'), ...queryAll('[role="textbox"]')];
    c.sort((a, b) => area(b) - area(a));
    return c[0] || null;
  }

  // Loading = a generation is running (not just disabled).
  function isLoading(btn) {
    return (
      btn.getAttribute("data-loading") === "true" ||
      btn.getAttribute("aria-busy") === "true" ||
      /generating|processing/i.test(btn.innerText || "")
    );
  }

  function isBusy(btn) {
    return (
      btn.disabled ||
      btn.getAttribute("data-loading") === "true" ||
      btn.getAttribute("aria-disabled") === "true" ||
      btn.getAttribute("aria-busy") === "true" ||
      /generating|loading|processing/i.test(btn.innerText || "")
    );
  }

  function findGenerate(o) {
    for (const sel of [o.generateSelector, DEFAULT_SEL.generate]) {
      if (!sel) continue;
      const l = queryAll(sel);
      if (l[0]) return l[0];
    }
    const btns = queryAll('button,[role="button"]').filter((b) => {
      const t = labelOf(b);
      return t.length < 60 && /\bgenerate\b/i.test(t);
    });
    return btns.find((b) => !isBusy(b)) || btns[0] || null;
  }

  function findDownloads(o) {
    for (const sel of [o.downloadSelector, DEFAULT_SEL.download]) {
      if (!sel) continue;
      const l = queryAll(sel);
      if (l.length) return l;
    }
    return queryAll('button,a,[role="button"],[role="menuitem"]').filter((b) => {
      const t = labelOf(b);
      return t.length < 40 && /download/i.test(t);
    });
  }

  function setText(el, text) {
    el.focus();
    if (el.tagName === "TEXTAREA" || el.tagName === "INPUT") {
      const proto = el.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
      Object.getOwnPropertyDescriptor(proto, "value").set.call(el, text);
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
    } else {
      document.execCommand("selectAll", false, null);
      document.execCommand("insertText", false, text);
    }
  }
  const readText = (el) => (el.value !== undefined ? el.value : el.innerText || "");

  function report(msg) {
    chrome.runtime.sendMessage({ type: "progress", msg }).catch(() => {});
    if (overlay) overlay.querySelector(".msg").textContent = msg;
  }

  function showOverlay() {
    if (overlay) return;
    overlay = document.createElement("div");
    overlay.style.cssText =
      "position:fixed;right:16px;bottom:16px;z-index:2147483647;background:#111;color:#fff;font:13px/1.4 system-ui;padding:10px 12px;border-radius:8px;max-width:340px;box-shadow:0 2px 10px rgba(0,0,0,.4)";
    overlay.innerHTML = '<div style="font-weight:600;margin-bottom:4px">TTS Batch Runner</div><div class="msg"></div><button style="margin-top:8px;padding:4px 10px;cursor:pointer">Stop</button>';
    overlay.querySelector("button").onclick = () => {
      stopFlag = true;
      report("Stopping after the current step...");
    };
    document.body.appendChild(overlay);
  }
  function hideOverlay() {
    if (overlay) overlay.remove();
    overlay = null;
  }

  function waitDownload(ms) {
    return new Promise((resolve) => {
      const t = setTimeout(() => {
        downloadWaiter = null;
        resolve({ ok: false, timeout: true });
      }, ms);
      downloadWaiter = (r) => {
        clearTimeout(t);
        downloadWaiter = null;
        resolve(r);
      };
    });
  }

  async function runOne(item, o, idx, total) {
    const label = `[${idx}/${total}] ${item.name}`;
    const input = findTextInput(o);
    if (!input) return { ok: false, why: "text box not found" };
    for (let i = 0; i < 20 && input.disabled; i++) await sleep(500);
    if (input.disabled) return { ok: false, why: "text box is disabled (page still loading?)" };
    report(`${label}: pasting ${item.text.length} characters`);
    setText(input, item.text);
    await sleep(600);
    const back = readText(input).replace(/\s+/g, " ").trim();
    const want = item.text.replace(/\s+/g, " ").trim();
    if (back.length < want.length * 0.98) return { ok: false, why: "text did not stick in the box (length mismatch)" };

    let gen = findGenerate(o);
    for (let i = 0; i < 20 && gen && isBusy(gen); i++) {
      await sleep(500);
      gen = findGenerate(o);
    }
    if (!gen || isBusy(gen)) return { ok: false, why: "Generate button not found or disabled" };

    report(`${label}: clicking Generate (this spends credits)`);
    gen.click();

    // Done = the Generate button was seen loading, stopped loading, and the
    // Download button is enabled. A Download button left enabled from the
    // previous file is therefore never mistaken for the new audio.
    const started = Date.now();
    let sawLoading = false;
    let ready = null;
    while (Date.now() - started < o.genTimeout * 1000) {
      if (stopFlag) return { ok: false, why: "stopped" };
      await sleep(400);
      const g = findGenerate(o);
      const loading = !!(g && isLoading(g));
      if (loading) sawLoading = true;
      if (!sawLoading && Date.now() - started > 20000) {
        return { ok: false, why: "Generate did not start (no loading state in 20 s): check credits or a dialog on the page" };
      }
      if (sawLoading && !loading) {
        const d = findDownloads(o);
        const pick = o.downloadPick === "last" ? d[d.length - 1] : d[0];
        if (pick && !isBusy(pick)) {
          ready = pick;
          break;
        }
      }
    }

    const outName = item.name + "." + (o.ext || "mp3");
    await chrome.runtime.sendMessage({ type: "expect", folder: o.folder, name: outName });

    if (!ready) {
      report(`${label}: could not detect finished audio. Click Download yourself within 90 s; it will be renamed to ${outName}.`);
      const r = await waitDownload(90000);
      return r.ok ? { ok: true } : { ok: false, why: "no download detected (not retried, to avoid spending credits)" };
    }

    await sleep(500);
    report(`${label}: downloading as ${outName}`);
    ready.click();
    if (o.menuItemText) {
      await sleep(700);
      const re = new RegExp(o.menuItemText, "i");
      const m = queryAll('[role="menuitem"],button,a,li,div').find((e) => e.children.length < 3 && re.test((e.innerText || "").trim()) && (e.innerText || "").length < 40);
      if (m) m.click();
    }
    const r = await waitDownload(60000);
    if (!r.ok) {
      await chrome.runtime.sendMessage({ type: "clear" });
      return { ok: false, why: r.timeout ? "download did not finish in 60 s" : "download interrupted" };
    }
    return { ok: true };
  }

  async function runAll(items, o) {
    if (running) return;
    running = true;
    stopFlag = false;
    showOverlay();
    const results = [];
    for (let i = 0; i < items.length; i++) {
      if (stopFlag) break;
      let r;
      try {
        r = await runOne(items[i], o, i + 1, items.length);
      } catch (e) {
        r = { ok: false, why: String(e && e.message ? e.message : e) };
      }
      results.push({ name: items[i].name, ...r });
      report(`${items[i].name}: ${r.ok ? "done" : "FAILED - " + r.why}`);
      if (!r.ok && r.why !== "stopped") {
        // Do not keep spending credits after a failure.
        report(`${items[i].name}: FAILED - ${r.why}. Run stopped so no more credits are spent.`);
        break;
      }
      if (i < items.length - 1) await sleep((o.pause || 3) * 1000);
    }
    running = false;
    chrome.runtime.sendMessage({ type: "finished", results }).catch(() => {});
    setTimeout(hideOverlay, 6000);
  }

  function probe(o) {
    const input = findTextInput(o);
    const gen = findGenerate(o);
    const dl = findDownloads(o);
    const mark = (el, color) => {
      if (!el) return;
      const old = el.style.outline;
      el.style.outline = `3px solid ${color}`;
      setTimeout(() => (el.style.outline = old), 4000);
    };
    mark(input, "#e11");
    mark(gen, "#1a1");
    dl.slice(0, 3).forEach((d) => mark(d, "#16c"));
    const d = (el) => (el ? `${el.tagName.toLowerCase()} "${labelOf(el).slice(0, 40)}"` : "NOT FOUND");
    return {
      textBox: d(input),
      generate: d(gen),
      downloads: dl.length ? dl.slice(0, 3).map(d) : ["none visible (generate once, then test again)"],
    };
  }

  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (!msg) return;
    if (msg.type === "ping") sendResponse({ ok: true });
    else if (msg.type === "probe") sendResponse(probe(msg.options || {}));
    else if (msg.type === "start") {
      runAll(msg.items, msg.options || {});
      sendResponse({ ok: true });
    } else if (msg.type === "stop") {
      stopFlag = true;
      sendResponse({ ok: true });
    } else if (msg.type === "downloadDone") {
      if (downloadWaiter) downloadWaiter({ ok: msg.ok });
    }
  });
})();
