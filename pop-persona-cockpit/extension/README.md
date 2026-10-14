# POP Capture Extension

Load this directory as an unpacked extension in Chrome.

Supported pages:

- `https://chatgpt.com/*`
- `https://chat.openai.com/*`

The extension watches for `data-message-author-role` message nodes, extracts user and assistant turns, and sends them to:

- `POST http://127.0.0.1:8765/api/capture/chat-message`

Status checks use:

- `GET http://127.0.0.1:8765/api/capture/status`
