"""Create local secrets once. Never overwrite existing configuration."""
from pathlib import Path
import secrets

root = Path(__file__).resolve().parents[1]
backend = root / "backend/.env"
frontend = root / "frontend/.env.local"
if backend.exists() or frontend.exists():
    raise SystemExit("Configuration already exists; edit it manually. Nothing was overwritten.")
admin, ingest = secrets.token_urlsafe(48), secrets.token_urlsafe(48)
text = (root / "backend/.env.example").read_text()
backend.write_text(text.replace("ADMIN_API_TOKEN=", f"ADMIN_API_TOKEN={admin}")
                   .replace("INGEST_API_TOKEN=", f"INGEST_API_TOKEN={ingest}"))
frontend.write_text(f"AGENTSENTINEL_API_URL=http://127.0.0.1:8000\nADMIN_API_TOKEN={admin}\n")
(root / "backend/data").mkdir(exist_ok=True)
print("Local configuration created. Secrets were not printed. Kill switch is enabled.")
