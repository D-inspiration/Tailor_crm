"""
Unit tests: MessageRepository CRUD and queries.
"""

import pytest
from datetime import datetime
from comm_platform.repositories.message_repo import MessageRepository
from comm_platform.models.message import Message
from comm_platform.core.constants import MessageStatus


class TestMessageRepository:
    def test_create_message(self, db_session):
        repo = MessageRepository()
        msg = repo.create(
            sender="a@example.com",
            recipient="b@example.com",
            subject="Hello",
            body="World",
            status=MessageStatus.UNREAD.value,
            received_at=datetime.utcnow(),
            provider="resend",
        )
        assert msg.id is not None
        assert msg.preview == "World"

    def test_search_finds_match(self, db_session):
        repo = MessageRepository()
        repo.create(sender="findme@example.com", recipient="to@example.com", subject="Target", body="Content", received_at=datetime.utcnow(), provider="resend")
        results = repo.search("findme")
        assert len(results) == 1
        assert results[0].sender == "findme@example.com"

    def test_unread_count(self, db_session):
        repo = MessageRepository()
        repo.create(sender="a@example.com", recipient="b@example.com", subject="S", body="B", status=MessageStatus.UNREAD.value, received_at=datetime.utcnow(), provider="resend")
        repo.create(sender="a@example.com", recipient="b@example.com", subject="S2", body="B2", status=MessageStatus.READ.value, received_at=datetime.utcnow(), provider="resend")
        assert repo.unread_count() == 1
