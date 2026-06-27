from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class Template:
    id: int = 0
    name: str = ""
    description: str = ""
    content_sid: str = ""
    variables: List[str] = field(default_factory=list)
    examples: Dict[str, str] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "Template":
        return cls(
            id=data.get("id", 0),
            name=data.get("name", ""),
            description=data.get("description", ""),
            content_sid=data.get("content_sid", ""),
            variables=eval(data.get("variables", "[]")),
            examples=eval(data.get("examples", "{}")),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "content_sid": self.content_sid,
            "variables": self.variables,
            "examples": self.examples,
        }

    @property
    def variable_count(self) -> int:
        return len(self.variables)


@dataclass
class Campaign:
    id: int = 0
    name: str = ""
    description: str = ""
    template_id: int = 0
    template_name: str = ""
    status: str = "draft"
    recipients: int = 0
    sent: int = 0
    failed: int = 0
    delivered: int = 0
    total: int = 0
    duration_secs: float = 0.0
    scheduled_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "Campaign":
        return cls(
            id=data.get("id", 0),
            name=data.get("name", ""),
            description=data.get("description", ""),
            template_id=data.get("template_id", 0),
            template_name=data.get("template_name", ""),
            status=data.get("status", "draft"),
            recipients=data.get("recipients", 0),
            sent=data.get("sent", 0),
            failed=data.get("failed", 0),
            delivered=data.get("delivered", 0),
            total=data.get("total", 0),
            duration_secs=data.get("duration_secs", 0.0),
            scheduled_at=data.get("scheduled_at"),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return round((self.sent + self.delivered) / self.total * 100, 2)

    @property
    def is_running(self) -> bool:
        return self.status in ("sending", "queued")

    @property
    def is_completed(self) -> bool:
        return self.status in ("completed", "cancelled")


@dataclass
class CampaignResult:
    id: int = 0
    campaign_id: int = 0
    phone: str = ""
    status: str = "queued"
    error_message: str = ""
    twilio_sid: str = ""
    variables_used: dict = field(default_factory=dict)
    attempt_count: int = 0
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "CampaignResult":
        return cls(
            id=data.get("id", 0),
            campaign_id=data.get("campaign_id", 0),
            phone=data.get("phone", ""),
            status=data.get("status", "queued"),
            error_message=data.get("error_message", ""),
            twilio_sid=data.get("twilio_sid", ""),
            variables_used=eval(data.get("variables_used", "{}")),
            attempt_count=data.get("attempt_count", 0),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


@dataclass
class LogEntry:
    id: int = 0
    campaign_id: Optional[int] = None
    timestamp: str = ""
    level: str = "INFO"
    phone: str = ""
    message: str = ""
    twilio_sid: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "LogEntry":
        return cls(
            id=data.get("id", 0),
            campaign_id=data.get("campaign_id"),
            timestamp=data.get("timestamp", ""),
            level=data.get("level", "INFO"),
            phone=data.get("phone", ""),
            message=data.get("message", ""),
            twilio_sid=data.get("twilio_sid", ""),
        )


@dataclass
class Setting:
    key: str = ""
    value: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "Setting":
        return cls(key=data.get("key", ""), value=data.get("value", ""))
