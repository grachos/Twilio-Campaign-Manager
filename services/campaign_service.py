import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Callable
from database.database import DatabaseManager
from database.models import Campaign, CampaignResult
from services.template_service import TemplateService
from services.twilio_service import TwilioService
from utils.logger import AppLogger
from config.config import ConfigManager


class CampaignService:
    """Manages campaigns: creation, execution, tracking, and history.

    Coordinates between the database, templates, and Twilio service
    to execute message campaigns with full lifecycle management.
    """

    def __init__(self) -> None:
        self.db = DatabaseManager()
        self.template_service = TemplateService()
        self.twilio_service = TwilioService()
        self.logger = AppLogger()
        self.config = ConfigManager()

    def create_campaign(
        self, name: str, description: str = "",
        template_id: int = 0, template_name: str = ""
    ) -> int:
        campaign_id = self.db.create_campaign(name, description, template_id, template_name)
        self.logger.info(f"Campaign created: {name} (ID: {campaign_id})")
        return campaign_id

    def get_campaign(self, campaign_id: int) -> Optional[Campaign]:
        data = self.db.get_campaign(campaign_id)
        return Campaign.from_dict(data) if data else None

    def get_all_campaigns(self, limit: int = 100, offset: int = 0) -> List[Campaign]:
        return [Campaign.from_dict(d) for d in self.db.get_all_campaigns(limit, offset)]

    def search_campaigns(self, query: str) -> List[Campaign]:
        return [Campaign.from_dict(d) for d in self.db.search_campaigns(query)]

    def delete_campaign(self, campaign_id: int) -> None:
        self.db.delete_campaign(campaign_id)
        self.logger.info(f"Campaign deleted (ID: {campaign_id})")

    def duplicate_campaign(self, campaign_id: int, new_name: str) -> int:
        new_id = self.db.duplicate_campaign(campaign_id, new_name)
        self.logger.info(f"Campaign duplicated: {new_name} (ID: {new_id})")
        return new_id

    def import_recipients(
        self, campaign_id: int, recipients: List[Dict[str, Any]],
        phone_column: str = "phone", variable_mapping: Optional[Dict[str, str]] = None,
    ) -> int:
        """Import recipients into a campaign.

        Returns count of imported recipients.
        """
        count = 0
        for row in recipients:
            phone = str(row.get(phone_column, "")).strip()
            if not phone or phone.lower() == "nan":
                continue

            variables_used = {}
            if variable_mapping:
                for var_key, col_name in variable_mapping.items():
                    val = str(row.get(col_name, "")).strip()
                    if val.lower() != "nan":
                        variables_used[var_key] = val

            self.db.add_campaign_result(
                campaign_id=campaign_id,
                phone=phone,
                variables_used=json.dumps(variables_used),
            )
            count += 1

        self.db.update_campaign(campaign_id, recipients=count, total=count)
        self.logger.info(f"Imported {count} recipients to campaign (ID: {campaign_id})")
        return count

    def get_campaign_results(self, campaign_id: int) -> List[CampaignResult]:
        return [CampaignResult.from_dict(d) for d in self.db.get_campaign_results(campaign_id)]

    def get_results_stats(self, campaign_id: int) -> Dict[str, int]:
        return self.db.get_results_stats(campaign_id)

    def update_campaign(self, campaign_id: int, **kwargs) -> None:
        self.db.update_campaign(campaign_id, **kwargs)
        self.logger.info(f"Campaign updated (ID: {campaign_id}): {kwargs}")

    def update_campaign_status(self, campaign_id: int, status: str) -> None:
        self.db.update_campaign(campaign_id, status=status)
        if status == "sending":
            self.db.update_campaign(campaign_id, started_at=datetime.now().isoformat())
        elif status in ("completed", "cancelled"):
            self.db.update_campaign(campaign_id, completed_at=datetime.now().isoformat())

    def get_retry_failed_results(self, campaign_id: int) -> List[CampaignResult]:
        return [CampaignResult.from_dict(d) for d in self.db.get_retry_failed_results(campaign_id)]

    def update_result_status(self, result_id: int, status: str) -> None:
        self.db.update_result_status(result_id, status)

    def get_sent_results_with_sid(self, campaign_id: int) -> List[Dict[str, Any]]:
        return self.db.get_sent_results_with_sid(campaign_id)

    def check_and_update_delivery_status(self, campaign_id: int) -> int:
        """Check delivery status of all sent messages with Twilio SIDs.
        Returns count of status changes.
        """
        results = self.get_sent_results_with_sid(campaign_id)
        changes = 0
        for r in results:
            success, status, error = self.twilio_service.get_message_status(r["twilio_sid"])
            if success and status != "sent":
                self.db.update_campaign_result(r["id"], status, error_message=error)
                changes += 1
        return changes

    def fetch_and_store_replies(self, campaign_id: int, since_minutes: int = 1440) -> int:
        """Fetch incoming replies from Twilio for a campaign's recipients.
        Matches replies by sender phone number against campaign recipients.
        Returns count of new replies stored.
        """
        to_number = self.config.get("DEFAULT_SENDER", "")
        replies = self.twilio_service.fetch_incoming_replies(since_minutes=since_minutes, to_number=to_number)

        if not replies:
            return 0

        results = self.db.get_sent_results_with_sid(campaign_id)
        recipient_phones = {r["phone"] for r in results}

        existing = self.db.get_campaign_replies(campaign_id)
        existing_sids = {r["twilio_sid"] for r in existing}

        stored = 0
        for reply in replies:
            if reply["sid"] in existing_sids:
                continue
            from_phone = reply.get("from_", "")
            if from_phone in recipient_phones:
                self.db.add_campaign_reply(
                    campaign_id=campaign_id,
                    from_phone=from_phone,
                    body=reply.get("body", ""),
                    twilio_sid=reply["sid"],
                    received_at=reply.get("date_sent", ""),
                )
                stored += 1

        if stored:
            self.logger.info(f"Stored {stored} new replies for campaign (ID: {campaign_id})")
        return stored

    def get_campaign_replies(self, campaign_id: int) -> List[Dict[str, Any]]:
        return self.db.get_campaign_replies(campaign_id)

    def get_dashboard_stats(self) -> Dict[str, Any]:
        return self.db.get_dashboard_stats()

    def mark_campaign_completed(self, campaign_id: int) -> None:
        stats = self.get_results_stats(campaign_id)
        duration = 0.0
        campaign = self.get_campaign(campaign_id)
        if campaign and campaign.started_at:
            try:
                start = datetime.fromisoformat(campaign.started_at)
                end = datetime.now()
                duration = (end - start).total_seconds()
            except (ValueError, TypeError):
                pass

        self.db.update_campaign(
            campaign_id,
            status="completed",
            sent=stats.get("sent", 0) + stats.get("delivered", 0),
            failed=stats.get("failed", 0),
            delivered=stats.get("delivered", 0),
            total=stats.get("total", 0),
            duration_secs=round(duration, 2),
            completed_at=datetime.now().isoformat(),
        )
        self.logger.info(f"Campaign completed (ID: {campaign_id}) - Sent: {stats.get('sent', 0)}, Failed: {stats.get('failed', 0)}")
