import sqlite3
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from config.config import ConfigManager


class DatabaseManager:
    """Manages SQLite database connection and schema.

    Thread-safe singleton that provides CRUD operations for all
    application entities. Creates tables on first initialization.
    """

    _instance: Optional["DatabaseManager"] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "DatabaseManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self.config = ConfigManager()
        self._conn: Optional[sqlite3.Connection] = None
        self._local = threading.local()
        self._connect()
        self._create_tables()

    def _connect(self) -> None:
        db_path = self.config.db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

    @property
    def conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = self._conn
        return self._local.conn

    def _create_tables(self) -> None:
        cursor = self.conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY NOT NULL,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS templates (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL UNIQUE,
                description TEXT DEFAULT '',
                content_sid TEXT NOT NULL,
                variables   TEXT DEFAULT '[]',
                examples    TEXT DEFAULT '{}',
                created_at  TEXT DEFAULT (datetime('now')),
                updated_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS campaigns (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT NOT NULL,
                description     TEXT DEFAULT '',
                template_id     INTEGER,
                template_name   TEXT DEFAULT '',
                status          TEXT DEFAULT 'draft',
                recipients      INTEGER DEFAULT 0,
                sent            INTEGER DEFAULT 0,
                failed          INTEGER DEFAULT 0,
                delivered       INTEGER DEFAULT 0,
                total           INTEGER DEFAULT 0,
                duration_secs   REAL DEFAULT 0,
                scheduled_at    TEXT,
                started_at      TEXT,
                completed_at    TEXT,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS campaign_results (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id     INTEGER NOT NULL,
                phone           TEXT NOT NULL,
                status          TEXT DEFAULT 'queued',
                error_message   TEXT DEFAULT '',
                twilio_sid      TEXT DEFAULT '',
                variables_used  TEXT DEFAULT '{}',
                attempt_count   INTEGER DEFAULT 0,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS campaign_replies (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id     INTEGER NOT NULL,
                from_phone      TEXT NOT NULL,
                body            TEXT DEFAULT '',
                twilio_sid      TEXT DEFAULT '',
                received_at     TEXT DEFAULT (datetime('now')),
                created_at      TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER,
                timestamp   TEXT DEFAULT (datetime('now')),
                level       TEXT DEFAULT 'INFO',
                phone       TEXT DEFAULT '',
                message     TEXT DEFAULT '',
                twilio_sid  TEXT DEFAULT '',
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_campaign_results_campaign
                ON campaign_results(campaign_id);
            CREATE INDEX IF NOT EXISTS idx_campaign_results_status
                ON campaign_results(status);
            CREATE INDEX IF NOT EXISTS idx_campaign_replies_campaign
                ON campaign_replies(campaign_id);
            CREATE INDEX IF NOT EXISTS idx_logs_campaign
                ON logs(campaign_id);
            CREATE INDEX IF NOT EXISTS idx_logs_timestamp
                ON logs(timestamp);
        """)
        self.conn.commit()

    # ----- Settings -----

    def get_setting(self, key: str, default: str = "") -> str:
        cursor = self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
        self.conn.commit()

    def get_all_settings(self) -> Dict[str, str]:
        cursor = self.conn.execute("SELECT key, value FROM settings")
        return {row["key"]: row["value"] for row in cursor.fetchall()}

    # ----- Templates -----

    def save_template(
        self, name: str, description: str, content_sid: str,
        variables: List[str], examples: Dict[str, str]
    ) -> int:
        cursor = self.conn.execute(
            """INSERT INTO templates (name, description, content_sid, variables, examples)
               VALUES (?, ?, ?, ?, ?)""",
            (name, description, content_sid, str(variables), str(examples)),
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_template(
        self, template_id: int, name: str, description: str,
        content_sid: str, variables: List[str], examples: Dict[str, str]
    ) -> None:
        self.conn.execute(
            """UPDATE templates
               SET name=?, description=?, content_sid=?, variables=?, examples=?, updated_at=datetime('now')
               WHERE id=?""",
            (name, description, content_sid, str(variables), str(examples), template_id),
        )
        self.conn.commit()

    def delete_template(self, template_id: int) -> None:
        self.conn.execute("DELETE FROM templates WHERE id = ?", (template_id,))
        self.conn.commit()

    def get_template(self, template_id: int) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_templates(self) -> List[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM templates ORDER BY updated_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    # ----- Campaigns -----

    def create_campaign(
        self, name: str, description: str = "",
        template_id: Optional[int] = None, template_name: str = ""
    ) -> int:
        cursor = self.conn.execute(
            """INSERT INTO campaigns (name, description, template_id, template_name)
               VALUES (?, ?, ?, ?)""",
            (name, description, template_id if template_id and template_id > 0 else None, template_name),
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_campaign(self, campaign_id: int, **kwargs) -> None:
        allowed = {
            "name", "description", "template_id", "template_name", "status",
            "recipients", "sent", "failed", "delivered", "total",
            "duration_secs", "scheduled_at", "started_at", "completed_at",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return
        updates["updated_at"] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k}=?" for k in updates)
        values = list(updates.values()) + [campaign_id]
        self.conn.execute(
            f"UPDATE campaigns SET {set_clause} WHERE id=?", values
        )
        self.conn.commit()

    def get_campaign(self, campaign_id: int) -> Optional[Dict[str, Any]]:
        cursor = self.conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_campaigns(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        cursor = self.conn.execute(
            "SELECT * FROM campaigns ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return [dict(row) for row in cursor.fetchall()]

    def search_campaigns(self, query: str) -> List[Dict[str, Any]]:
        pattern = f"%{query}%"
        cursor = self.conn.execute(
            "SELECT * FROM campaigns WHERE name LIKE ? OR description LIKE ? ORDER BY created_at DESC",
            (pattern, pattern),
        )
        return [dict(row) for row in cursor.fetchall()]

    def delete_campaign(self, campaign_id: int) -> None:
        self.conn.execute("DELETE FROM campaign_results WHERE campaign_id = ?", (campaign_id,))
        self.conn.execute("DELETE FROM campaigns WHERE id = ?", (campaign_id,))
        self.conn.commit()

    def delete_all_campaigns(self) -> None:
        self.conn.execute("DELETE FROM campaign_results")
        self.conn.execute("DELETE FROM campaigns")
        self.conn.commit()

    def duplicate_campaign(self, campaign_id: int, new_name: str) -> int:
        original = self.get_campaign(campaign_id)
        if not original:
            raise ValueError(f"Campaign {campaign_id} not found")
        new_id = self.create_campaign(
            name=new_name,
            description=original["description"],
            template_id=original["template_id"],
            template_name=original["template_name"],
        )
        results = self.get_campaign_results(campaign_id)
        for r in results:
            self.add_campaign_result(
                campaign_id=new_id,
                phone=r["phone"],
                variables_used=r.get("variables_used", "{}"),
            )
        return new_id

    # ----- Campaign Results -----

    def add_campaign_result(
        self, campaign_id: int, phone: str,
        variables_used: str = "{}"
    ) -> int:
        cursor = self.conn.execute(
            """INSERT INTO campaign_results (campaign_id, phone, variables_used)
               VALUES (?, ?, ?)""",
            (campaign_id, phone, variables_used),
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_campaign_result(
        self, result_id: int, status: str,
        error_message: str = "", twilio_sid: str = ""
    ) -> None:
        self.conn.execute(
            """UPDATE campaign_results
               SET status=?, error_message=?, twilio_sid=?, attempt_count=attempt_count+1, updated_at=datetime('now')
               WHERE id=?""",
            (status, error_message, twilio_sid, result_id),
        )
        self.conn.commit()

    def update_result_status(self, result_id: int, status: str) -> None:
        self.conn.execute(
            "UPDATE campaign_results SET status=?, updated_at=datetime('now') WHERE id=?",
            (status, result_id),
        )
        self.conn.commit()

    def get_campaign_results(self, campaign_id: int) -> List[Dict[str, Any]]:
        cursor = self.conn.execute(
            "SELECT * FROM campaign_results WHERE campaign_id = ? ORDER BY id",
            (campaign_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_sent_results_with_sid(self, campaign_id: int) -> List[Dict[str, Any]]:
        cursor = self.conn.execute(
            "SELECT id, phone, twilio_sid FROM campaign_results WHERE campaign_id = ? AND twilio_sid != '' AND twilio_sid IS NOT NULL ORDER BY id",
            (campaign_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_campaign_results_paginated(
        self, campaign_id: int, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        cursor = self.conn.execute(
            "SELECT * FROM campaign_results WHERE campaign_id = ? ORDER BY id LIMIT ? OFFSET ?",
            (campaign_id, limit, offset),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_results_stats(self, campaign_id: int) -> Dict[str, int]:
        cursor = self.conn.execute(
            """SELECT status, COUNT(*) as count
               FROM campaign_results WHERE campaign_id = ?
               GROUP BY status""",
            (campaign_id,),
        )
        stats = {"queued": 0, "sending": 0, "sent": 0, "delivered": 0, "failed": 0, "total": 0}
        for row in cursor.fetchall():
            stats[row["status"]] = row["count"]
            stats["total"] += row["count"]
        return stats

    def get_retry_failed_results(self, campaign_id: int) -> List[Dict[str, Any]]:
        cursor = self.conn.execute(
            "SELECT * FROM campaign_results WHERE campaign_id = ? AND status = 'failed'",
            (campaign_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    # ----- Campaign Replies -----

    def add_campaign_reply(
        self, campaign_id: int, from_phone: str,
        body: str = "", twilio_sid: str = "", received_at: str = ""
    ) -> int:
        cursor = self.conn.execute(
            """INSERT INTO campaign_replies (campaign_id, from_phone, body, twilio_sid, received_at)
               VALUES (?, ?, ?, ?, ?)""",
            (campaign_id, from_phone, body, twilio_sid, received_at or datetime.now().isoformat()),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_campaign_replies(self, campaign_id: int) -> List[Dict[str, Any]]:
        cursor = self.conn.execute(
            "SELECT * FROM campaign_replies WHERE campaign_id = ? ORDER BY received_at DESC",
            (campaign_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def delete_campaign_replies(self, campaign_id: int) -> None:
        self.conn.execute("DELETE FROM campaign_replies WHERE campaign_id = ?", (campaign_id,))
        self.conn.commit()

    # ----- Logs -----

    def add_log(
        self, level: str, message: str,
        campaign_id: int = 0, phone: str = "", twilio_sid: str = ""
    ) -> None:
        self.conn.execute(
            """INSERT INTO logs (campaign_id, level, phone, message, twilio_sid)
               VALUES (?, ?, ?, ?, ?)""",
            (campaign_id if campaign_id else None, level, phone, message, twilio_sid),
        )
        self.conn.commit()

    def get_logs(
        self, campaign_id: Optional[int] = None, limit: int = 500, offset: int = 0
    ) -> List[Dict[str, Any]]:
        if campaign_id:
            cursor = self.conn.execute(
                "SELECT * FROM logs WHERE campaign_id = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                (campaign_id, limit, offset),
            )
        else:
            cursor = self.conn.execute(
                "SELECT * FROM logs ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
        return [dict(row) for row in cursor.fetchall()]

    def clear_logs(self, campaign_id: Optional[int] = None) -> None:
        if campaign_id:
            self.conn.execute("DELETE FROM logs WHERE campaign_id = ?", (campaign_id,))
        else:
            self.conn.execute("DELETE FROM logs")
        self.conn.commit()

    def export_logs(self, campaign_id: Optional[int] = None) -> List[Dict[str, Any]]:
        return self.get_logs(campaign_id, limit=10000)

    # ----- Dashboard Stats -----

    def get_dashboard_stats(self) -> Dict[str, Any]:
        today = datetime.now().strftime("%Y-%m-%d")
        stats = {
            "today_campaigns": 0,
            "total_messages_sent": 0,
            "total_failures": 0,
            "pending_messages": 0,
            "avg_delivery_seconds": 0.0,
            "total_campaigns": 0,
        }
        cursor = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM campaigns WHERE date(created_at) = ?",
            (today,),
        )
        row = cursor.fetchone()
        stats["today_campaigns"] = row["cnt"] if row else 0

        cursor = self.conn.execute("SELECT COUNT(*) as cnt FROM campaigns")
        row = cursor.fetchone()
        stats["total_campaigns"] = row["cnt"] if row else 0

        cursor = self.conn.execute("SELECT COALESCE(SUM(sent), 0) as total FROM campaigns")
        row = cursor.fetchone()
        stats["total_messages_sent"] = row["total"] if row else 0

        cursor = self.conn.execute("SELECT COALESCE(SUM(failed), 0) as total FROM campaigns")
        row = cursor.fetchone()
        stats["total_failures"] = row["total"] if row else 0

        cursor = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM campaign_results WHERE status IN ('queued','sending')"
        )
        row = cursor.fetchone()
        stats["pending_messages"] = row["cnt"] if row else 0

        cursor = self.conn.execute(
            "SELECT COALESCE(AVG(duration_secs), 0) as avg_dur FROM campaigns WHERE duration_secs > 0"
        )
        row = cursor.fetchone()
        stats["avg_delivery_seconds"] = round(row["avg_dur"], 2) if row else 0.0

        return stats

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
