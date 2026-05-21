"""
Outbound mail service — sends via Resend API and tracks in database.
"""

import os
import requests
from typing import Optional, List
from comm_platform.repositories.sent_message_repo import SentMessageRepository
from comm_platform.models.sent_message import SentMessage
from comm_platform.core.config import CommConfig


class MailSenderService:
    """
    Encapsulated outbound email service.
    Sends via Resend REST API and logs to SentMessage for tracking.
    """

    RESEND_API_URL = "https://api.resend.com/emails"

    def __init__(self):
        self._repo = SentMessageRepository()
        self._api_key = os.getenv("RESEND_API_KEY") or CommConfig.get("RESEND_API_KEY")

    def send(
        self,
        to: str | List[str],
        subject: str,
        from_email: str = "admin@atrivix.com",
        from_name: Optional[str] = None,
        body_html: Optional[str] = None,
        body_text: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> SentMessage:
        """
        Send an email via Resend API and track it.
        """
        to_list = [to] if isinstance(to, str) else to
        to_str = ", ".join(to_list)

        sent_msg = self._repo.create(
            to_email=to_str,
            from_email=from_email,
            from_name=from_name,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            category=category or "transactional",
            tags=tags or [],
            status="queued",
        )

        payload = {
            "from": f"{from_name} <{from_email}>" if from_name else from_email,
            "to": to_list,
            "subject": subject,
        }
        if body_html:
            payload["html"] = body_html
        if body_text:
            payload["text"] = body_text

        try:
            resp = requests.post(
                self.RESEND_API_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            sent_msg.mark_sent(data.get("id", ""))
        except requests.RequestException as e:
            sent_msg.mark_failed(str(e))
            raise RuntimeError(f"Failed to send email: {e}")

        return sent_msg

    def get_stats(self) -> dict:
        return self._repo.stats()

    def get_by_sender(self, from_email: str, limit: int = 50) -> List[SentMessage]:
        return self._repo.by_sender(from_email, limit)

    def get_grouped_by_sender(self) -> List[dict]:
        return self._repo.group_by_sender()

    def get_grouped_by_domain(self) -> List[dict]:
        return self._repo.group_by_domain()
        