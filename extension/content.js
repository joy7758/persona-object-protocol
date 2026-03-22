(function () {
  if (window.__POP_CAPTURE_INITIALIZED) {
    return;
  }
  window.__POP_CAPTURE_INITIALIZED = true;

  const SELECTORS = {
    messageNodes: "[data-message-author-role]",
    titleCandidates: ["main h1", "header h1"]
  };
  const HEARTBEAT_INTERVAL_MS = 15000;
  const OVERLAY_ID = "pop-capture-debug-overlay";

  const pageFingerprints = new Set();
  const overlayState = {
    captureEnabled: true,
    showDebugOverlay: false,
    sentCount: 0,
    lastCapturedMessageId: "—",
    lastSendStatus: "等待",
    backendAvailable: false,
    lastSyncStatus: ""
  };

  let observer = null;
  let debounceHandle = null;
  let heartbeatHandle = null;
  let overlayNode = null;

  void init();

  chrome.runtime.onMessage.addListener((message) => {
    if (message?.type === "POP_CAPTURE_STATE") {
      updateRuntimeState(message.payload || {});
    }
  });

  async function init() {
    await hydrateState();
    attachObserver();
    scheduleScan();
    startHeartbeat();
  }

  async function hydrateState() {
    try {
      const status = await sendRuntimeMessage({ type: "POP_GET_STATUS" });
      updateRuntimeState(status);
    } catch (_error) {
      updateOverlay();
    }
  }

  function attachObserver() {
    if (observer) {
      return;
    }
    observer = new MutationObserver(() => scheduleScan());
    observer.observe(document.documentElement, {
      childList: true,
      subtree: true
    });
  }

  function startHeartbeat() {
    if (heartbeatHandle) {
      return;
    }
    heartbeatHandle = window.setInterval(async () => {
      try {
        const status = await sendRuntimeMessage({ type: "POP_HEARTBEAT_REQUEST" });
        updateRuntimeState(status);
      } catch (_error) {
        updateOverlay();
      }
    }, HEARTBEAT_INTERVAL_MS);
  }

  function scheduleScan() {
    clearTimeout(debounceHandle);
    debounceHandle = window.setTimeout(() => {
      void scanAndCapture();
    }, 500);
  }

  async function scanAndCapture() {
    const messages = await collectMessages();
    for (const payload of messages) {
      if (pageFingerprints.has(payload.message_fingerprint)) {
        continue;
      }

      try {
        const response = await sendRuntimeMessage({
          type: "POP_CAPTURE_MESSAGE",
          payload
        });
        if (response?.ok || response?.reason === "session_duplicate") {
          pageFingerprints.add(payload.message_fingerprint);
        }
      } catch (_error) {
        updateOverlay();
      }
    }
  }

  async function collectMessages() {
    const nodes = Array.from(document.querySelectorAll(SELECTORS.messageNodes));
    if (!nodes.length) {
      return [];
    }

    const conversationTitle = getConversationTitle();
    const payloads = await Promise.all(
      nodes.map((node, index) => buildPayload(node, index, conversationTitle))
    );
    return payloads.filter(Boolean);
  }

  async function buildPayload(node, index, conversationTitle) {
    const role = normalizeRole(node.getAttribute("data-message-author-role") || "");
    if (!role) {
      return null;
    }

    const text = extractMessageText(node);
    if (!text) {
      return null;
    }

    return {
      role,
      text,
      page_url: window.location.href,
      conversation_title: conversationTitle,
      captured_at: new Date().toISOString(),
      message_fingerprint: await buildFingerprint(role, text, index),
      dom_index: index
    };
  }

  function extractMessageText(node) {
    const rawText = node.innerText || node.textContent || "";
    return rawText
      .replace(/\r\n/g, "\n")
      .replace(/\r/g, "\n")
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .join("\n")
      .trim();
  }

  function getConversationTitle() {
    for (const selector of SELECTORS.titleCandidates) {
      const candidate = document.querySelector(selector);
      if (candidate?.textContent?.trim()) {
        return candidate.textContent.trim();
      }
    }

    return document.title.replace(/\s*[-–]\s*ChatGPT\s*$/i, "").trim();
  }

  function normalizeRole(value) {
    const normalized = value.trim().toLowerCase();
    if (normalized === "user" || normalized === "assistant") {
      return normalized;
    }
    return "";
  }

  async function buildFingerprint(role, text, domIndex) {
    const basis = [
      normalizeRole(role),
      normalizeText(text),
      String(domIndex)
    ].join("::");
    try {
      const buffer = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(basis));
      const hex = Array.from(new Uint8Array(buffer))
        .map((value) => value.toString(16).padStart(2, "0"))
        .join("");
      return `pop-${hex.slice(0, 20)}`;
    } catch (_error) {
      return fallbackFingerprint(basis);
    }
  }

  function fallbackFingerprint(basis) {
    let hash = 2166136261;
    for (let index = 0; index < basis.length; index += 1) {
      hash ^= basis.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }
    return `pop-${Math.abs(hash).toString(16)}`;
  }

  function normalizeText(value) {
    return value.replace(/\r\n/g, "\n").replace(/\r/g, "\n").trim();
  }

  async function sendRuntimeMessage(message) {
    return chrome.runtime.sendMessage(message);
  }

  function updateRuntimeState(payload) {
    overlayState.captureEnabled = Boolean(payload.captureEnabled);
    overlayState.showDebugOverlay = Boolean(payload.showDebugOverlay);
    overlayState.sentCount = Number(payload.sentCount || 0);
    overlayState.lastCapturedMessageId = payload.lastCapturedMessageId || "—";
    overlayState.lastSendStatus = humanizeSendStatus(payload.lastSendStatus || "idle");
    overlayState.backendAvailable = Boolean(payload.backendAvailable);
    overlayState.lastSyncStatus = payload.lastSyncStatus || "";
    updateOverlay();
  }

  function ensureOverlay() {
    if (overlayNode) {
      return overlayNode;
    }
    if (!document.body) {
      return null;
    }
    overlayNode = document.createElement("div");
    overlayNode.id = OVERLAY_ID;
    overlayNode.style.position = "fixed";
    overlayNode.style.top = "16px";
    overlayNode.style.right = "16px";
    overlayNode.style.zIndex = "999999";
    overlayNode.style.maxWidth = "260px";
    overlayNode.style.padding = "12px 14px";
    overlayNode.style.borderRadius = "14px";
    overlayNode.style.background = "rgba(26, 22, 18, 0.92)";
    overlayNode.style.color = "#fff9f0";
    overlayNode.style.font = "12px/1.5 -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
    overlayNode.style.boxShadow = "0 14px 30px rgba(0, 0, 0, 0.24)";
    overlayNode.innerHTML = `
      <div style="font-weight:700; margin-bottom:6px;">POP 调试浮层</div>
      <div>自动记录：<span data-pop-field="capture">开启</span></div>
      <div>最近消息：<span data-pop-field="message-id">—</span></div>
      <div>已发送：<span data-pop-field="sent-count">0</span></div>
      <div>发送状态：<span data-pop-field="send-status">等待</span></div>
      <div style="margin-top:6px; color:#d8cdbd;" data-pop-field="sync-status"></div>
    `;
    document.body.appendChild(overlayNode);
    return overlayNode;
  }

  function updateOverlay() {
    const node = ensureOverlay();
    if (!node) {
      return;
    }
    node.style.display = overlayState.showDebugOverlay ? "block" : "none";
    node.querySelector('[data-pop-field="capture"]').textContent = overlayState.captureEnabled
      ? "开启"
      : "关闭";
    node.querySelector('[data-pop-field="message-id"]').textContent =
      overlayState.lastCapturedMessageId;
    node.querySelector('[data-pop-field="sent-count"]').textContent = String(overlayState.sentCount);
    node.querySelector('[data-pop-field="send-status"]').textContent = overlayState.lastSendStatus;
    node.querySelector('[data-pop-field="sync-status"]').textContent = overlayState.lastSyncStatus;
  }

  function humanizeSendStatus(value) {
    if (value === "ok") {
      return "成功";
    }
    if (value === "duplicate") {
      return "重复";
    }
    if (value === "failed") {
      return "失败";
    }
    if (value === "off") {
      return "已关闭";
    }
    return "等待";
  }
})();
