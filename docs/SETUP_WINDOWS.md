# Windows setup — small checkpoints

Extract the ZIP so the repository is at `C:\AgentSentinel` and this file is at
`C:\AgentSentinel\docs\SETUP_WINDOWS.md`. Use **Command Prompt (CMD)** for these commands.
Do one checkpoint at a time. Stop and share the error if any command fails.

## 1. Prepare and start the API

```bat
cd /d C:\AgentSentinel
python scripts\setup.py
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements-lock.txt
python -m pip install -e . --no-deps
alembic upgrade head
python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/health/ready. Expected:
`{"status":"ready","database":"reachable"}`. Leave this terminal running.
The setup script creates both environment files with matching admin tokens and a separate
ingest token. It refuses to overwrite either file. Never paste those tokens into chat.

## 2. Start the console in a second CMD window

```bat
cd /d C:\AgentSentinel\frontend
npm ci
npm run build
npm start
```

Open http://127.0.0.1:3000 (use this exact origin; set `CONSOLE_ORIGIN` in
`frontend\.env.local` if intentionally changing it). With a fresh database, heartbeat count is zero and last heartbeat
is not received. Connections remain unconfigured until you add your keys.
For editing only, `npm run dev` replaces build/start; do not run both simultaneously.

## 3. Connect your existing n8n and Groq

Edit `backend\.env` locally:
- `N8N_BASE_URL`: your n8n origin, normally `http://127.0.0.1:5678`.
- `N8N_API_KEY`: create from n8n Settings → n8n API.
- `GROQ_API_KEY`: your actual Groq key.
- `GROQ_MODEL`: keep the configured model if available to your account, otherwise set one
  supporting JSON mode. Structured inference compatibility is checked in Phase 3.

Restart the API with the same uvicorn command, refresh the console and use each **Check
connection** button. A model visibility check does not run inference or create incidents.
Do not share your environment file or API keys.

## 4. Import the single workflow

1. In n8n, import `n8n\AgentSentinel_Master.json` and save it.
2. Open `AGENTSENTINEL API · Record heartbeat`.
3. Select/create **Header Auth** credentials with header name `Authorization` and value
   `Bearer ` followed by the `INGEST_API_TOKEN` from `backend\.env`.
4. If n8n runs natively on the same Windows machine, retain the node URL. If it runs in
   Docker, `127.0.0.1` is the container: use `http://host.docker.internal:8000` and configure
   narrowly scoped host access. Do not expose the API to the internet to solve this.
5. Execute manually. Only an actual successful API response should show `recorded`.
6. Refresh the console: the stored heartbeat count and last receipt time should update.

Workflow import/execution on your n8n version is a required acceptance check. The bundled
JSON uses built-in Manual Trigger, HTTP Request v4.2 and Sticky Note nodes; static validation
alone does not prove compatibility with every n8n version.

## 5. Run local acceptance checks

Stop the API if RAM is tight. In an activated backend CMD:

```bat
ruff check .
pytest -q
alembic check
```

In `frontend`:

```bat
npm run lint
npm run typecheck
```

Once both connection checks and the real n8n heartbeat pass, send **Phase 1 complete**.
No monitoring or self-healing should be expected yet.

## Troubleshooting

- `python` missing: install Python 3.12 or 3.13 with PATH enabled.
- Unsupported Node: install Node 22 LTS or newer, reopen CMD.
- Auth error: admin token in frontend must match backend; ingest token must be different.
- Database not ready: run commands from `backend` and apply `alembic upgrade head`.
- Port occupied: close the other process or consistently change API/console URLs.
- 502 connection check: check service reachability, key permission and model name.
- Setup refuses overwrite: configuration already exists. Edit it; do not regenerate secrets
  without also updating Next.js and n8n credentials.
