// Service worker: renames each download to the expected file name inside a
// subfolder of the browser's Downloads folder.

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg && msg.type === "expect") {
    const exp = {
      folder: msg.folder || "",
      name: msg.name,
      ts: Date.now(),
      tabId: sender.tab ? sender.tab.id : null,
      downloadId: null,
    };
    chrome.storage.session.set({ exp }).then(() => sendResponse({ ok: true }));
    return true;
  }
  if (msg && msg.type === "clear") {
    chrome.storage.session.remove("exp").then(() => sendResponse({ ok: true }));
    return true;
  }
});

// Must call suggest exactly once; returning true keeps the event open for async work.
chrome.downloads.onDeterminingFilename.addListener((item, suggest) => {
  chrome.storage.session.get("exp").then(async ({ exp }) => {
    if (exp && Date.now() - exp.ts < 90000 && exp.downloadId === null) {
      const folder = (exp.folder || "").replace(/^[\\/]+|[\\/]+$/g, "");
      const filename = (folder ? folder + "/" : "") + exp.name;
      exp.downloadId = item.id;
      await chrome.storage.session.set({ exp });
      suggest({ filename, conflictAction: "overwrite" });
    } else {
      suggest();
    }
  });
  return true;
});

chrome.downloads.onChanged.addListener(async (delta) => {
  const { exp } = await chrome.storage.session.get("exp");
  if (!exp || exp.downloadId !== delta.id || !delta.state) return;
  const state = delta.state.current;
  if (state !== "complete" && state !== "interrupted") return;
  if (exp.tabId !== null) {
    chrome.tabs
      .sendMessage(exp.tabId, { type: "downloadDone", ok: state === "complete", name: exp.name })
      .catch(() => {});
  }
  await chrome.storage.session.remove("exp");
});
