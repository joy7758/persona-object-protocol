document.addEventListener("DOMContentLoaded", async () => {
  const captureEnabled = document.getElementById("capture-enabled");
  const showDebugOverlay = document.getElementById("show-debug-overlay");
  const backendUrl = document.getElementById("backend-url");
  const backendStatus = document.getElementById("backend-status");
  const lastSyncStatus = document.getElementById("last-sync-status");
  const lastMessageId = document.getElementById("last-message-id");
  const sentCount = document.getElementById("sent-count");
  const saveButton = document.getElementById("save-settings");
  const refreshButton = document.getElementById("refresh-status");

  async function refreshStatus(pingBackend = false) {
    const message = { type: pingBackend ? "POP_PING_BACKEND" : "POP_GET_STATUS" };
    const status = await chrome.runtime.sendMessage(message);
    captureEnabled.checked = Boolean(status.captureEnabled);
    showDebugOverlay.checked = Boolean(status.showDebugOverlay);
    backendUrl.value = status.backendUrl || "http://127.0.0.1:8765";
    backendStatus.textContent = status.backendAvailable ? "已连接" : "POP backend not running";
    lastSyncStatus.textContent = status.lastSyncStatus || "等待连接";
    lastMessageId.textContent = status.lastCapturedMessageId || "—";
    sentCount.textContent = String(status.sentCount || 0);
  }

  saveButton.addEventListener("click", async () => {
    await chrome.runtime.sendMessage({
      type: "POP_UPDATE_SETTINGS",
      payload: {
        captureEnabled: captureEnabled.checked,
        showDebugOverlay: showDebugOverlay.checked,
        backendUrl: backendUrl.value
      }
    });
    await refreshStatus(true);
  });

  refreshButton.addEventListener("click", async () => {
    await refreshStatus(true);
  });

  await refreshStatus(true);
});
