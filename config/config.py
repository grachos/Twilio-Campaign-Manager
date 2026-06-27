import json
import os
import base64
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


load_dotenv()


class ConfigManager:
    """Singleton configuration manager for the application.

    Loads environment variables, manages encrypted credential storage,
    and provides a centralized settings dictionary backed by SQLite.
    """

    _instance: Optional["ConfigManager"] = None

    def __new__(cls) -> "ConfigManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._config: Dict[str, Any] = {}
        self._cipher: Optional[Fernet] = None
        self._load_defaults()
        self._init_encryption()

    def _load_defaults(self) -> None:
        base_dir = Path(__file__).resolve().parent.parent
        self._config.update({
            "APP_NAME": "Twilio Campaign Manager",
            "APP_VERSION": "1.0.0",
            "BASE_DIR": str(base_dir),
            "DB_PATH": str(base_dir / "campaign_manager.db"),
            "LOG_DIR": str(base_dir / "logs"),
            "CAMPAIGNS_DIR": str(base_dir / "campaigns"),
            "TEMPLATES_DIR": str(base_dir / "templates"),
            "EXPORTS_DIR": str(base_dir / "exports"),
            "TWILIO_ACCOUNT_SID": os.getenv("TWILIO_ACCOUNT_SID", ""),
            "TWILIO_AUTH_TOKEN": os.getenv("TWILIO_AUTH_TOKEN", ""),
            "TWILIO_MESSAGING_SERVICE_SID": os.getenv("TWILIO_MESSAGING_SERVICE_SID", ""),
            "DEFAULT_SENDER": os.getenv("TWILIO_DEFAULT_SENDER", ""),
            "STATUS_CALLBACK_URL": os.getenv("STATUS_CALLBACK_URL", ""),
            "RETRY_ATTEMPTS": int(os.getenv("RETRY_ATTEMPTS", "3")),
            "DELAY_BETWEEN_MSGS": float(os.getenv("DELAY_BETWEEN_MSGS", "0.5")),
            "MAX_PARALLEL_WORKERS": int(os.getenv("MAX_PARALLEL_WORKERS", "5")),
            "THEME_MODE": "Dark",
            "COLOR_THEME": "green",
        })

    def _init_encryption(self) -> None:
        key_file = Path(self._config["BASE_DIR"]) / ".key"
        if key_file.exists():
            key = key_file.read_bytes()
        else:
            machine_id = os.environ.get("COMPUTERNAME", "twilio-cm-default")
            salt = b"twilio-cm-salt-2024"
            kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
            key = base64.urlsafe_b64encode(kdf.derive(machine_id.encode()))
            key_file.write_bytes(key)
        self._cipher = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            return ""
        return self._cipher.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        return self._cipher.decrypt(ciphertext.encode()).decode()

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._config[key] = value

    def get_all(self) -> Dict[str, Any]:
        return dict(self._config)

    def update_from_db(self, db_settings: Dict[str, str]) -> None:
        for key, value in db_settings.items():
            if value:
                self._config[key.upper()] = value

    def export_config(self) -> str:
        safe = {k: v for k, v in self._config.items() if "TOKEN" not in k.upper() and "SID" not in k.upper()}
        return json.dumps(safe, indent=2)

    @property
    def twilio_credentials_valid(self) -> bool:
        return bool(
            self._config.get("TWILIO_ACCOUNT_SID")
            and self._config.get("TWILIO_AUTH_TOKEN")
            and self._config.get("TWILIO_MESSAGING_SERVICE_SID")
        )

    @property
    def app_name(self) -> str:
        return self._config.get("APP_NAME", "Twilio Campaign Manager")

    @property
    def app_version(self) -> str:
        return self._config.get("APP_VERSION", "1.0.0")

    @property
    def db_path(self) -> str:
        return self._config.get("DB_PATH", "campaign_manager.db")

    @property
    def log_dir(self) -> str:
        return self._config.get("LOG_DIR", "logs")

    @property
    def campaigns_dir(self) -> str:
        return self._config.get("CAMPAIGNS_DIR", "campaigns")

    @property
    def templates_dir(self) -> str:
        return self._config.get("TEMPLATES_DIR", "templates")

    @property
    def exports_dir(self) -> str:
        return self._config.get("EXPORTS_DIR", "exports")
