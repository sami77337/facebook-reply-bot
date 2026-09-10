"""Async semantic routing orchestration after durable moderation."""

from __future__ import annotations

from app.adapters.contracts import ClassificationAdapter
from app.domain.classification import (
    ClassificationAssessment,
    ClassificationRequest,
    ClassificationResult,
)
from app.domain.moderation import ModerationDisposition
from app.persistence.classification_repository import ClassificationRepository
from app.persistence.moderation_repository import ModerationRepository
from app.persistence.repositories import DurableRepository
from app.services.classification_policy import ClassificationPolicy

_UNKNOWN_ADAPTER = "unknown-classifier"
_UNKNOWN_VERSION = "unknown-version"


class ClassificationNotEligible(RuntimeError):
    """Raised when semantic classification is attempted before moderation allows it."""


def _safe_adapter_identity(adapter: ClassificationAdapter) -> tuple[str, str]:
    try:
        name = adapter.name
        version = adapter.version
    except Exception:
        return _UNKNOWN_ADAPTER, _UNKNOWN_VERSION
    if not isinstance(name, str) or not isinstance(version, str):
        return _UNKNOWN_ADAPTER, _UNKNOWN_VERSION
    if not name.strip() or not version.strip():
        return _UNKNOWN_ADAPTER, _UNKNOWN_VERSION
    return name, version


class ClassificationService:
    """Produce one durable routing-only classification for an eligible event."""

    def __init__(
        self,
        *,
        events: DurableRepository,
        moderation: ModerationRepository,
        results: ClassificationRepository,
        adapter: ClassificationAdapter,
        policy: ClassificationPolicy,
    ) -> None:
        self.events = events
        self.moderation = moderation
        self.results = results
        self.adapter = adapter
        self.policy = policy

    async def classify(self, event_id: str) -> ClassificationResult:
        """Classify only events whose durable moderation result explicitly allows routing."""

        moderation_result = self.moderation.get_for_event(event_id)
        if (
            moderation_result is None
            or moderation_result.disposition is not ModerationDisposition.ALLOW_ROUTING
        ):
            raise ClassificationNotEligible(
                "classification requires durable moderation disposition allow_routing"
            )

        existing = self.results.get_for_event(event_id)
        if existing is not None:
            return existing

        event = self.events.get_event(event_id)
        request = ClassificationRequest(
            event_id=event.id,
            platform=event.platform,
            text=event.text,
            media=event.media,
        )
        adapter_name, adapter_version = _safe_adapter_identity(self.adapter)
        religious_possible: bool | None = None
        confidence: float | None = None

        try:
            candidate = await self.adapter.classify(request)
        except Exception:
            decision = self.policy.adapter_failure()
        else:
            if not isinstance(candidate, ClassificationAssessment):
                decision = self.policy.invalid_assessment()
            else:
                religious_possible = candidate.religious_possible
                confidence = candidate.confidence
                decision = self.policy.decide(request, candidate)

        return self.results.create_for_event(
            event_id=event.id,
            decision=decision,
            religious_possible=religious_possible,
            confidence=confidence,
            adapter_name=adapter_name,
            adapter_version=adapter_version,
        )
