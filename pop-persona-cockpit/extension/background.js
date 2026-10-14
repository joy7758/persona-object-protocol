const DEFAULT_BACKEND_URL = "http://127.0.0.1:8765";
const HEARTBEAT_INTERVAL_MS = 15000;
const MAX_SESSION_FINGERPRINTS = 500;
const CHATGPT_URL_PATTERNS = [
  "https://chatgpt.com/*",
  "https://chat.openai.com/*"
];

const runtimeState = {
  captureEnabled: true,
  showDebugOverlay: false,
  backendUrl: DEFAULT_BACKEND_URL,
  backendAvailable: false,
  lastSyncStatus: "等待连接",
  sentCount: 0,
  sentFingerprints: new Set(),
  sentFingerprintOrder: [],
  lastCapturedMessageId: "—",
  lastSendStatus: "idle",
  lastCaptureAt: "",
  lastBackendCheckAt: ""
};

const hydratePromise = hydrateState();
let heartbeatHandle = null;

chrome.runtime.onInstalled.addListener(async () => {
  await chrome.storage.local.set({
    captureEnabled: true,
    showDebugOverlay: false,
    backendUrl: DEFAULT_BACKEND_URL
  });
});

void bootstrap();

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  (async () => {
    await hydratePromise;

    if (message?.type === "POP_GET_STATUS") {
      sendResponse(getPopupStatus());
      return;
    }

    if (message?.type === "POP_UPDATE_SETTINGS") {
      await updateSettings(message.payload || {});
      sendResponse(getPopupStatus());
      return;
    }

    if (message?.type === "POP_PING_BACKEND" || message?.type === "POP_HEARTBEAT_REQUEST") {
      await refreshBackendStatus();
      sendResponse(getPopupStatus());
      return;
    }

    if (message?.type === "POP_CAPTURE_MESSAGE") {
      sendResponse(await handleCapturePayload(message.payload, sender));
      return;
    }

    sendResponse({ ok: false, reason: "unknown_message_type" });
  })().catch((error) => {
    sendResponse({ ok: false, reason: error.message || "unexpected_error" });
  });

  return true;
});

async function bootstrap() {
  await hydratePromise;
  startHeartbeat();
  await refreshBackendStatus();
  await broadcastRuntimeState();
}

async function hydrateState() {
  const storedSettings = await chrome.storage.local.get({
    captureEnabled: true,
    showDebugOverlay: false,
    backendUrl: DEFAULT_BACKEND_URL
  });
  runtimeState.captureEnabled = Boolean(storedSettings.captureEnabled);
  runtimeState.showDebugOverlay = Boolean(storedSettings.showDebugOverlay);
  runtimeState.backendUrl = normalizeBackendUrl(storedSettings.backendUrl);

  if (chrome.storage.session) {
    const sessionData = await chrome.storage.session.get({
      sentCount: 0,
      sentFingerprints: [],
      lastSyncStatus: "等待连接",
      backendAvailable: false,
      lastCapturedMessageId: "—",
      lastSendStatus: "idle",
      lastCaptureAt: "",
      lastBackendCheckAt: ""
    });
    runtimeState.sentCount = Number(sessionData.sentCount || 0);
    runtimeState.sentFingerprintOrder = Array.isArray(sessionData.sentFingerprints)
      ? sessionData.sentFingerprints
      : [];
    runtimeState.sentFingerprints = new Set(runtimeState.sentFingerprintOrder);
    runtimeState.lastSyncStatus = sessionData.lastSyncStatus || "等待连接";
    runtimeState.backendAvailable = Boolean(sessionData.backendAvailable);
    runtimeState.lastCapturedMessageId = sessionData.lastCapturedMessageId || "—";
    runtimeState.lastSendStatus = sessionData.lastSendStatus || "idle";
    runtimeState.lastCaptureAt = sessionData.lastCaptureAt || "";
    runtimeState.lastBackendCheckAt = sessionData.lastBackendCheckAt || "";
  }
}

async function updateSettings(payload) {
  if (typeof payload.captureEnabled !== "undefined") {
    runtimeState.captureEnabled = Boolean(payload.captureEnabled);
  }
  if (typeof payload.showDebugOverlay !== "undefined") {
    runtimeState.showDebugOverlay = Boolean(payload.showDebugOverlay);
  }
  runtimeState.backendUrl = normalizeBackendUrl(payload.backendUrl || runtimeState.backendUrl);
  await chrome.storage.local.set({
    captureEnabled: runtimeState.captureEnabled,
    showDebugOverlay: runtimeState.showDebugOverlay,
    backendUrl: runtimeState.backendUrl
  });
  await refreshBackendStatus();
  await broadcastRuntimeState();
}

function getPopupStatus() {
  return {
    captureEnabled: runtimeState.captureEnabled,
    showDebugOverlay: runtimeState.showDebugOverlay,
    backendUrl: runtimeState.backendUrl,
    backendAvailable: runtimeState.backendAvailable,
    lastSyncStatus: runtimeState.lastSyncStatus,
    sentCount: runtimeState.sentCount,
    lastCapturedMessageId: runtimeState.lastCapturedMessageId,
    lastSendStatus: runtimeState.lastSendStatus,
    lastCaptureAt: runtimeState.lastCaptureAt,
    lastBackendCheckAt: runtimeState.lastBackendCheckAt
  };
}

function startHeartbeat() {
  if (heartbeatHandle) {
    return;
  }
  heartbeatHandle = setInterval(() => {
    void refreshBackendStatus();
  }, HEARTBEAT_INTERVAL_MS);
}

async function refreshBackendStatus() {
  try {
    const response = await fetch(`${runtimeState.backendUrl}/api/capture/status?source=extension`, {
      method: "GET"
    });
    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }
    const payload = await response.json();
    runtimeState.backendAvailable = Boolean(payload.capture_endpoint_available);
    runtimeState.lastBackendCheckAt = new Date().toISOString();
    if (!runtimeState.backendAvailable) {
      runtimeState.lastSyncStatus = "POP backend not running";
    } else if (payload.last_capture_at) {
      runtimeState.lastSyncStatus = `已连接，最近记录 ${formatShortTime(payload.last_capture_at)}`;
    } else {
      runtimeState.lastSyncStatus = "已连接，等待新消息";
    }
  } catch (error) {
    runtimeState.backendAvailable = false;
    runtimeState.lastBackendCheckAt = new Date().toISOString();
    runtimeState.lastSyncStatus = "POP backend not running";
  }
  await persistSessionState();
  await broadcastRuntimeState();
}

async function handleCapturePayload(payload, sender) {
  if (!runtimeState.captureEnabled) {
    runtimeState.lastSendStatus = "off";
    await persistSessionState();
    await broadcastRuntimeState();
    return { ok: false, reason: "capture_disabled" };
  }

  const fingerprint = payload?.message_fingerprint;
  if (!fingerprint) {
    runtimeState.lastSendStatus = "failed";
    await persistSessionState();
    await broadcastRuntimeState();
    return { ok: false, reason: "missing_fingerprint" };
  }

  if (runtimeState.sentFingerprints.has(fingerprint)) {
    runtimeState.lastCapturedMessageId = shortFingerprint(fingerprint);
    runtimeState.lastSendStatus = "duplicate";
    await persistSessionState();
    await broadcastRuntimeState();
    return { ok: true, accepted: false, reason: "session_duplicate" };
  }

  try {
    const response = await fetch(`${runtimeState.backendUrl}/api/capture/chat-message`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });
    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    const result = await response.json();
    if (result.status === "imported" || result.status === "duplicate") {
      rememberFingerprint(fingerprint);
      runtimeState.sentCount += 1;
      runtimeState.lastCapturedMessageId = shortFingerprint(fingerprint);
      runtimeState.lastCaptureAt = payload.captured_at || new Date().toISOString();
      runtimeState.lastSendStatus = result.status === "duplicate" ? "duplicate" : "ok";
    } else {
      runtimeState.lastSendStatus = "failed";
    }
    runtimeState.backendAvailable = true;
    runtimeState.lastSyncStatus = describeIngestionResult(result);
    await persistSessionState();
    await broadcastRuntimeState();
    return {
      ok: true,
      accepted: result.status === "imported",
      result
    };
  } catch (error) {
    runtimeState.backendAvailable = false;
    runtimeState.lastSendStatus = "failed";
    runtimeState.lastSyncStatus = "POP backend not running";
    await persistSessionState();
    await broadcastRuntimeState();
    return {
      ok: false,
      reason: runtimeState.lastSyncStatus,
      tabId: sender?.tab?.id || null
    };
  }
}

function rememberFingerprint(fingerprint) {
  if (runtimeState.sentFingerprints.has(fingerprint)) {
    return;
  }
  runtimeState.sentFingerprints.add(fingerprint);
  runtimeState.sentFingerprintOrder.push(fingerprint);
  if (runtimeState.sentFingerprintOrder.length > MAX_SESSION_FINGERPRINTS) {
    const removed = runtimeState.sentFingerprintOrder.shift();
    if (removed) {
      runtimeState.sentFingerprints.delete(removed);
    }
  }
}

async function persistSessionState() {
  if (!chrome.storage.session) {
    return;
  }
  await chrome.storage.session.set({
    sentCount: runtimeState.sentCount,
    sentFingerprints: runtimeState.sentFingerprintOrder,
    lastSyncStatus: runtimeState.lastSyncStatus,
    backendAvailable: runtimeState.backendAvailable,
    lastCapturedMessageId: runtimeState.lastCapturedMessageId,
    lastSendStatus: runtimeState.lastSendStatus,
    lastCaptureAt: runtimeState.lastCaptureAt,
    lastBackendCheckAt: runtimeState.lastBackendCheckAt
  });
}

async function broadcastRuntimeState() {
  const tabs = await chrome.tabs.query({ url: CHATGPT_URL_PATTERNS });
  await Promise.all(
    tabs.map(async (tab) => {
      if (!tab.id) {
        return;
      }
      try {
        await chrome.tabs.sendMessage(tab.id, {
          type: "POP_CAPTURE_STATE",
          payload: getPopupStatus()
        });
      } catch (_error) {
        // Content script may not be ready on this tab yet.
      }
    })
  );
}

function describeIngestionResult(result) {
  if (result.status === "imported") {
    return "已发送到 POP";
  }
  if (result.status === "duplicate") {
    return "消息已记录，跳过重复发送";
  }
  if (result.status === "skipped") {
    return "消息为空，已跳过";
  }
  return `发送失败：${result.reason || "未知错误"}`;
}

function shortFingerprint(value) {
  if (!value) {
    return "—";
  }
  return value.length <= 14 ? value : `${value.slice(0, 14)}…`;
}

function formatShortTime(value) {
  try {
    return new Date(value).toLocaleTimeString();
  } catch (_error) {
    return value;
  }
}

function normalizeBackendUrl(value) {
  return (value || DEFAULT_BACKEND_URL).replace(/\/+$/, "");
}
