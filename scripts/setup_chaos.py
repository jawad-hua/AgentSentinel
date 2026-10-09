"""Add opt-in Chaos settings; preserve every existing setting and never print secrets."""
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "backend" / ".env"
if not path.exists():
    raise SystemExit("Existing backend .env required.")
existing = path.read_text(encoding="utf-8")
keys = {line.split("=", 1)[0].strip() for line in existing.splitlines() if "=" in line}
values = {"CHAOS_ENABLED": "false", "CHAOS_WORKFLOW_IDS": ""}
additions = [f"{key}={value}" for key, value in values.items() if key not in keys]
if additions:
    with path.open("a", encoding="utf-8") as stream:
        stream.write("\n# Explicitly designated local Chaos experiments\n" + "\n".join(additions) + "\n")
print("Chaos settings checked. New settings default to disabled. Existing settings preserved.")
print("No secrets printed, workflow changes, fault injections or provider calls.")
