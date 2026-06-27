import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime

from database.database import DatabaseManager
from services.twilio_service import TwilioService
from services.campaign_service import CampaignService
from utils.logger import AppLogger
from config.config import ConfigManager


class SenderWorker:
    """Background worker that orchestrates multi-threaded message sending.

    Manages the full lifecycle of sending a campaign: queuing, throttling,
    progress reporting, pause/resume/cancel, and retry logic. All UI
    interaction happens through callbacks to keep the interface responsive.
    """

    def __init__(self) -> None:
        self.config = ConfigManager()
        self.db = DatabaseManager()
        self.twilio_service = TwilioService()
        self.campaign_service = CampaignService()
        self.logger = AppLogger()

        self._pause_event = threading.Event()
        self._pause_event.set()
        self._cancel_event = threading.Event()
        self._is_running = False

        self._progress_callbacks: List[Callable] = []
        self._log_callbacks: List[Callable] = []
        self._complete_callbacks: List[Callable] = []

        self._stats = {
            "total": 0,
            "sent": 0,
            "failed": 0,
            "delivered": 0,
            "sending": 0,
            "queued": 0,
            "start_time": 0.0,
            "elapsed": 0.0,
            "estimated_remaining": 0.0,
        }

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def is_paused(self) -> bool:
        return not self._pause_event.is_set()

    @property
    def stats(self) -> Dict[str, Any]:
        return dict(self._stats)

    def register_progress_callback(self, callback: Callable) -> None:
        self._progress_callbacks.append(callback)

    def register_log_callback(self, callback: Callable) -> None:
        self._log_callbacks.append(callback)

    def register_complete_callback(self, callback: Callable) -> None:
        self._complete_callbacks.append(callback)

    def unregister_progress_callback(self, callback: Callable) -> None:
        if callback in self._progress_callbacks:
            self._progress_callbacks.remove(callback)

    def _notify_progress(self) -> None:
        for cb in self._progress_callbacks:
            try:
                cb(self._stats)
            except Exception:
                pass

    def _notify_log(self, level: str, message: str, **kwargs) -> None:
        self.logger.info(message, **kwargs)
        for cb in self._log_callbacks:
            try:
                cb(level, message, **kwargs)
            except Exception:
                pass

    def _notify_complete(self) -> None:
        for cb in self._complete_callbacks:
            try:
                cb(self._stats)
            except Exception:
                pass

    def pause(self) -> None:
        self._pause_event.clear()
        self._notify_log("INFO", "Sending paused")

    def resume(self) -> None:
        self._pause_event.set()
        self._notify_log("INFO", "Sending resumed")

    def cancel(self) -> None:
        self._cancel_event.set()
        self._pause_event.set()
        self._notify_log("INFO", "Sending cancelled by user")

    def reset(self) -> None:
        self._cancel_event.clear()
        self._pause_event.set()
        self._is_running = False
        self._stats = {k: 0 if isinstance(v, int) else "" if isinstance(v, str) else 0.0 for k, v in self._stats.items()}

    def start_sending(
        self, campaign_id: int, results: List[Dict[str, Any]],
        content_sid: str, variable_order: List[str],
        column_mapping: Dict[str, str],
        max_workers: Optional[int] = None,
        delay: Optional[float] = None,
    ) -> None:
        """Start sending messages for a campaign using worker threads."""
        self.reset()
        self._is_running = True

        if max_workers is None:
            max_workers = int(self.config.get("MAX_PARALLEL_WORKERS", 5))
        if delay is None:
            delay = float(self.config.get("DELAY_BETWEEN_MSGS", 0.5))

        messaging_service_sid = self.config.get("TWILIO_MESSAGING_SERVICE_SID", "")
        default_sender = self.config.get("DEFAULT_SENDER", "")
        if not messaging_service_sid and not default_sender:
            self._notify_log("ERROR", "Configure either a Messaging Service SID or a Default Sender in Settings")
            self._is_running = False
            self._notify_complete()
            return

        self._stats["total"] = len(results)
        self._stats["queued"] = len(results)
        self._stats["start_time"] = time.time()

        self.campaign_service.update_campaign_status(campaign_id, "sending")

        thread = threading.Thread(
            target=self._send_loop,
            args=(campaign_id, results, content_sid, variable_order, column_mapping,
                  messaging_service_sid, default_sender, max_workers, delay),
            daemon=True,
        )
        thread.start()

    def _send_loop(
        self, campaign_id: int, results: List[Dict[str, Any]],
        content_sid: str, variable_order: List[str],
        column_mapping: Dict[str, str],
        messaging_service_sid: str, default_sender: str, max_workers: int, delay: float,
    ) -> None:
        try:
            self._process_results(results, content_sid, variable_order, column_mapping,
                                  messaging_service_sid, default_sender, max_workers, delay, campaign_id)

            self.campaign_service.mark_campaign_completed(campaign_id)
            self._stats["elapsed"] = time.time() - self._stats["start_time"]
            self._is_running = False
            self._notify_progress()
            self._notify_complete()
            self._notify_log("SUCCESS", f"Campaign {campaign_id} completed in {self._stats['elapsed']:.1f}s")

        except Exception as e:
            self._notify_log("ERROR", f"Campaign failed: {e}")
            self._is_running = False
            self._notify_complete()

    def _process_results(
        self, results: List[Dict[str, Any]],
        content_sid: str, variable_order: List[str],
        column_mapping: Dict[str, str],
        messaging_service_sid: str, default_sender: str, max_workers: int, delay: float,
        campaign_id: int,
    ) -> None:
        """Process results using a thread pool."""
        self._stats["queued"] = len(results)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for result in results:
                if self._cancel_event.is_set():
                    self._db_bulk_update_status(
                        [r["id"] for r in results if r.get("id")],
                        "cancelled",
                    )
                    return

                self._pause_event.wait()

                future = executor.submit(
                    self._send_single_message,
                    result, content_sid, variable_order, column_mapping,
                    messaging_service_sid, default_sender, campaign_id,
                )
                futures[future] = result
                time.sleep(delay)

            for future in as_completed(futures):
                if self._cancel_event.is_set():
                    break
                try:
                    future.result()
                except Exception as e:
                    self._notify_log("ERROR", f"Worker error: {e}")

    def _send_single_message(
        self, result: Dict[str, Any],
        content_sid: str, variable_order: List[str],
        column_mapping: Dict[str, str],
        messaging_service_sid: str, default_sender: str, campaign_id: int,
    ) -> None:
        """Send a single message and update the database."""
        result_id = result.get("id")
        phone = result.get("phone", "")

        if not phone:
            self._update_result(result_id, "failed", "Empty phone")
            self._stats["failed"] += 1
            self._stats["queued"] = max(0, self._stats["queued"] - 1)
            self._notify_progress()
            return

        variables_raw = result.get("variables_used", "{}")
        if isinstance(variables_raw, str):
            try:
                variables = json.loads(variables_raw)
            except json.JSONDecodeError:
                variables = {}
        else:
            variables = variables_raw

        try:
            self.db.update_campaign_result(result_id, "sending")
            self._stats["sending"] += 1
            self._stats["queued"] = max(0, self._stats["queued"] - 1)
            self._notify_progress()

            target = phone if phone.startswith("whatsapp:") else f"whatsapp:{phone}"
            sender = default_sender if default_sender.startswith("whatsapp:") else f"whatsapp:{default_sender}" if default_sender else ""

            success, sid, status = self.twilio_service.send_message(
                to=target,
                content_sid=content_sid,
                content_variables=variables,
                messaging_service_sid=messaging_service_sid,
                from_number=sender,
            )

            if success:
                self.db.update_campaign_result(result_id, "sent", twilio_sid=sid)
                self._stats["sent"] += 1
                self._stats["sending"] = max(0, self._stats["sending"] - 1)
                self._notify_log("SUCCESS", f"Sent to {phone}", phone=phone, twilio_sid=sid)
            else:
                error_msg = status or sid or "Unknown error"
                self.db.update_campaign_result(result_id, "failed", error_message=error_msg)
                self._stats["failed"] += 1
                self._stats["sending"] = max(0, self._stats["sending"] - 1)
                self._notify_log("ERROR", f"Failed {phone}: {error_msg}", phone=phone)

        except Exception as e:
            self.db.update_campaign_result(result_id, "failed", error_message=str(e))
            self._stats["failed"] += 1
            self._stats["sending"] = max(0, self._stats["sending"] - 1)
            self._notify_log("ERROR", f"Exception for {phone}: {e}", phone=phone)

        self._notify_progress()

    def _update_result(self, result_id: int, status: str, error: str = "") -> None:
        if result_id:
            self.db.update_campaign_result(result_id, status, error_message=error)

    def _db_bulk_update_status(self, result_ids: List[int], status: str) -> None:
        for rid in result_ids:
            if rid:
                self.db.update_result_status(rid, status)

    def retry_failed(self, campaign_id: int) -> None:
        """Retry all failed messages for a campaign."""
        failed_results = self.campaign_service.get_retry_failed_results(campaign_id)
        if not failed_results:
            self._notify_log("INFO", "No failed messages to retry")
            return

        campaign = self.campaign_service.get_campaign(campaign_id)
        if not campaign:
            return

        template = self.campaign_service.template_service.get_template(campaign.template_id)
        if not template:
            self._notify_log("ERROR", "Template not found for retry")
            return

        self._notify_log("INFO", f"Retrying {len(failed_results)} failed messages")
        results_data = []
        for r in failed_results:
            self.db.update_campaign_result(r.id, "queued")
            results_data.append({
                "id": r.id,
                "phone": r.phone,
                "variables_used": r.variables_used,
            })

        self.start_sending(
            campaign_id=campaign_id,
            results=results_data,
            content_sid=template.content_sid,
            variable_order=template.variables,
            column_mapping={},
        )
