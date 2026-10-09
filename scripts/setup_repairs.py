"""Add disabled repair configuration without printing secrets or replacing existing values."""

from pathlib import Path

from cryptography.fernet import Fernet


def main():
    path = Path(__file__).resolve().parents[1] / "backend" / ".env"
    if not path.exists():
        raise SystemExit(
            "Existing backend .env required; run the original setup first."
        )
    existing = path.read_text(encoding="utf-8")
    keys = {
        line.split("=", 1)[0].strip() for line in existing.splitlines() if "=" in line
    }
    values = {
        "REPAIRS_ENABLED": "false",
        "REPAIR_WORKFLOW_IDS": "",
        "N8N_WRITE_API_KEY": "",
        "SNAPSHOT_ENCRYPTION_KEY": Fernet.generate_key().decode(),
    }
    additions = [f"{key}={value}" for key, value in values.items() if key not in keys]
    if additions:
        with path.open("a", encoding="utf-8") as stream:
            stream.write(
                "\n# Controlled repair configuration\n" + "\n".join(additions) + "\n"
            )
    print(
        "Repair configuration checked. Existing settings preserved. Secrets were not printed."
    )
    print(
        "New repair settings default to disabled. Back up .env securely with the database."
    )


if __name__ == "__main__":
    main()
