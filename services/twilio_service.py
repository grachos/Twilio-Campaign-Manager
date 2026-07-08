import json
import time
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime, timedelta
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from config.config import ConfigManager
from utils.logger import AppLogger


class TwilioService:
    """Handles all Twilio API communication.

    Manages client lifecycle, message sending with retry logic,
    and provides methods for checking delivery status.
    """

    def __init__(self) -> None:
        self.config = ConfigManager()
        self.logger = AppLogger()
        self._client: Optional[Client] = None

    def _build_client(self) -> Optional[Client]:
        sid = self.config.get("TWILIO_ACCOUNT_SID", "")
        token = self.config.get("TWILIO_AUTH_TOKEN", "")
        if not sid or not token:
            return None
        return Client(sid, token)

    @property
    def client(self) -> Optional[Client]:
        if self._client is None:
            self._client = self._build_client()
        return self._client

    def reset_client(self) -> None:
        self._client = None

    def test_connection(self) -> Tuple[bool, str]:
        try:
            client = self.client
            if not client:
                return False, "Missing credentials - fill Account SID and Auth Token"
            client.api.account.fetch()
            return True, "Connection successful"
        except TwilioRestException as e:
            msg = e.msg or str(e)
            if "Authenticate" in msg or "authentication" in msg.lower() or "20003" in str(e.status):
                return False, "Invalid Account SID or Auth Token. Verify them in your Twilio Console."
            return False, f"Twilio error: {msg}"
        except Exception as e:
            return False, f"Connection failed: {e}"

    def send_message(
        self,
        to: str,
        content_sid: str,
        content_variables: Dict[str, str],
        messaging_service_sid: Optional[str] = None,
        from_number: Optional[str] = None,
        status_callback: Optional[str] = None,
        attempt: int = 1,
        max_retries: int = None,
    ) -> Tuple[bool, str, str]:
        """Send a single Twilio message with retry logic.
        Uses messaging_service_sid if available, otherwise falls back to from_number.
        Returns (success, message_sid_or_error, status).
        """
        if max_retries is None:
            max_retries = int(self.config.get("RETRY_ATTEMPTS", 3))

        client = self.client
        if not client:
            return False, "", "No Twilio client available"

        if messaging_service_sid is None:
            messaging_service_sid = self.config.get("TWILIO_MESSAGING_SERVICE_SID", "")
        if from_number is None:
            from_number = self.config.get("DEFAULT_SENDER", "")

        if status_callback is None:
            status_callback = self.config.get("STATUS_CALLBACK_URL", "")

        if not messaging_service_sid and not from_number:
            return False, "", "Either Messaging Service SID or Default Sender number is required"

        last_error = ""
        for retry in range(max_retries):
            try:
                kwargs: Dict[str, Any] = {
                    "to": to,
                    "content_sid": content_sid,
                    "content_variables": json.dumps(content_variables),
                }
                if messaging_service_sid:
                    kwargs["messaging_service_sid"] = messaging_service_sid
                else:
                    kwargs["from_"] = from_number
                if status_callback:
                    kwargs["status_callback"] = status_callback

                message = client.messages.create(**kwargs)
                return True, message.sid, "sent"

            except TwilioRestException as e:
                last_error = e.msg or str(e)
                status = "failed"
                if e.status == 429:
                    wait = min(2 ** retry, 30)
                    self.logger.warning(f"Rate limited, waiting {wait}s (attempt {retry + 1}/{max_retries})")
                    time.sleep(wait)
                    continue
                elif e.status in (401, 403):
                    return False, "", f"Auth error: {last_error}"
                elif e.status >= 500:
                    if retry < max_retries - 1:
                        wait = 2 ** retry
                        self.logger.warning(f"Server error, retrying in {wait}s (attempt {retry + 1}/{max_retries})")
                        time.sleep(wait)
                        continue
                return False, "", last_error

            except Exception as e:
                last_error = str(e)
                if retry < max_retries - 1:
                    wait = 2 ** retry
                    self.logger.warning(f"Network error, retrying in {wait}s (attempt {retry + 1}/{max_retries})")
                    time.sleep(wait)
                    continue
                return False, "", last_error

        return False, "", last_error

    def get_message_status(self, twilio_sid: str) -> Tuple[bool, str, str]:
        """Fetch the actual delivery status of a sent message from Twilio.
        Returns (success, status, error_message).
        """
        client = self.client
        if not client:
            return False, "", "No Twilio client available"
        try:
            message = client.messages(twilio_sid).fetch()
            return True, message.status, message.error_message or ""
        except TwilioRestException as e:
            return False, "error", e.msg or str(e)
        except Exception as e:
            return False, "error", str(e)

    def fetch_incoming_replies(
        self, since_minutes: int = 60, to_number: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch incoming messages (replies) sent TO our Twilio number.

        Uses client.messages.list() filtered by direction='inbound'
        and date_sent_after. Returns list of reply dicts with
        from_, body, sid, date_sent keys.
        """
        client = self.client
        if not client:
            return []

        if to_number is None:
            to_number = self.config.get("DEFAULT_SENDER", "")

        if not to_number:
            return []

        if not str(to_number).startswith("whatsapp:"):
            to_number = f"whatsapp:{to_number}"

        since = datetime.utcnow() - timedelta(minutes=since_minutes)
        try:
            messages = client.messages.list(
                to=to_number,
                date_sent_after=since,
                limit=200,
            )
            replies = []
            for msg in messages:
                if msg.direction == "inbound":
                    replies.append({
                        "from_": msg.from_,
                        "body": msg.body,
                        "sid": msg.sid,
                        "date_sent": msg.date_sent.isoformat() if msg.date_sent else "",
                    })
            return replies
        except TwilioRestException as e:
            self.logger.error(f"Failed to fetch replies: {e.msg or str(e)}")
            return []
        except Exception as e:
            self.logger.error(f"Failed to fetch replies: {e}")
            return []

    def send_batch(
        self,
        recipients: List[Dict[str, Any]],
        content_sid: str,
        variable_mapping: Dict[str, str],
        messaging_service_sid: Optional[str] = None,
        delay: float = 0.5,
        progress_callback=None,
        cancel_event=None,
    ) -> List[Dict[str, Any]]:
        """Send messages to a batch of recipients.

        Returns list of result dicts with phone, success, sid, error.
        """
        results = []
        for idx, recipient in enumerate(recipients):
            if cancel_event and cancel_event.is_set():
                break

            phone = recipient.get("phone", "")
            content_vars = {}
            for var_key, col_name in variable_mapping.items():
                content_vars[var_key] = str(recipient.get(col_name, ""))

            success, sid, status = self.send_message(
                to=phone,
                content_sid=content_sid,
                content_variables=content_vars,
                messaging_service_sid=messaging_service_sid,
            )

            result = {
                "phone": phone,
                "success": success,
                "sid": sid,
                "status": status if success else "failed",
                "error": "" if success else sid,
            }
            results.append(result)

            if progress_callback:
                progress_callback(idx + 1, len(recipients), result)

            if delay > 0:
                time.sleep(delay)

        return results

    def build_content_variables(
        self, row: Dict[str, str], variable_order: List[str], column_mapping: Dict[str, str]
    ) -> Dict[str, str]:
        """Build content_variables dict from a row of data.

        variable_order: e.g. ["1", "2", "3"]
        column_mapping: e.g. {"1": "Customer", "2": "Order", "3": "Tracking"}
        Returns e.g. {"1": "John", "2": "Order 55", "3": "TRK-123"}
        """
        result = {}
        for var_key in variable_order:
            col_name = column_mapping.get(var_key, var_key)
            value = str(row.get(col_name, "")).strip()
            if value.lower() in ("nan", "none", "null", ""):
                value = ""
            result[var_key] = value
        return result
