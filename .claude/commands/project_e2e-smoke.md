---
description: Create or update a Playwright MCP smoke test for the RF02→RF04→RF05 flow
---

Goal: Have a basic end-to-end test using Playwright MCP that covers:
- Submitting a new "Solicitação de Evento"
- Approving the request
- Creating an event (mock or stub Google Calendar if real creds are unavailable)

Steps:
1) Ensure the dev server is running (Docker).
2) Use Playwright MCP to open the app and navigate the core path.
3) Add resilient selectors and timeouts.
4) Save a minimal report artifact.
(think harder)
