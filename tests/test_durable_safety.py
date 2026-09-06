from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from app.domain.events import NormalizedInboundEvent, Platform
from app.domain.states import ProcessingState
from app.persistence.repositories import DurableRepository, IdempotencyConflict
from app.persistence.sqlite import SQLiteDatabase
from app.services.ingestion import IngestionService
from app.services.transitions import TransitionService


def _repository(tmp_path: Path) -> tuple[DurableRepository, IngestionService]:
    database = SQLiteDatabase(tmp_path / "router.db")
    database.initialize()
    repository = DurableRepository(database)
    return repository, IngestionService(repository)


def _ingest(service: IngestionService, key: str) -> str:
    result = service.ingest_event(
        NormalizedInboundEvent(platform=Platform.FACEBOOK, external_event_key=key)
    )
    return result.event.id


def test_outbound_idempotency_key_collision_fails_closed(tmp_path: Path) -> None:
    repository, service = _repository(tmp_path)
    first_event_id = _ingest(service, "event-1")
    second_event_id = _ingest(service, "event-2")

    repository.create_outbound_action(
        event_id=first_event_id,
        platform=Platform.FACEBOOK,
        action_type="reply",
        idempotency_key="reply:collision",
    )

    with pytest.raises(IdempotencyConflict, match="different outbound action"):
        repository.create_outbound_action(
            event_id=second_event_id,
            platform=Platform.FACEBOOK,
            action_type="reply",
            idempotency_key="reply:collision",
        )


def test_retry_schedule_rejects_naive_datetime(tmp_path: Path) -> None:
    repository, service = _repository(tmp_path)
    event_id = _ingest(service, "retry-event")
    TransitionService(repository).transition(event_id, ProcessingState.PROCESSING)

    with pytest.raises(ValueError, match="timezone-aware"):
        repository.mark_retryable_failure(
            event_id,
            next_retry_at=datetime(2026, 9, 6, 8, 0),
        )
