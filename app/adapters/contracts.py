"""Protocol boundaries for future external integrations."""

from __future__ import annotations

from typing import Protocol

from app.domain.classification import ClassificationAssessment, ClassificationRequest
from app.domain.moderation import ModerationAssessment, ModerationRequest


class InboundCollector(Protocol):
    """Contract for a platform that can collect or receive inbound comments."""

    async def start(self) -> None:
        """Start receiving inbound events."""
        ...


class ReplyPublisher(Protocol):
    """Contract for publishing a reply to an originating platform."""

    async def publish_reply(self, *, external_comment_id: str, text: str) -> str:
        """Publish a reply and return the platform reply identifier."""
        ...


class ModerationAdapter(Protocol):
    """Provider-neutral async boundary for text/media moderation evidence."""

    @property
    def name(self) -> str:
        """Stable adapter identifier suitable for audit persistence."""
        ...

    @property
    def version(self) -> str:
        """Stable adapter/policy version suitable for audit persistence."""
        ...

    async def assess(self, request: ModerationRequest) -> ModerationAssessment:
        """Return normalized moderation evidence without taking external action."""
        ...


class ClassificationAdapter(Protocol):
    """Structured routing-only semantic classifier boundary."""

    @property
    def name(self) -> str:
        """Stable adapter identifier suitable for audit persistence."""
        ...

    @property
    def version(self) -> str:
        """Stable adapter/model version suitable for audit persistence."""
        ...

    async def classify(self, request: ClassificationRequest) -> ClassificationAssessment:
        """Return structured routing evidence; never answer the user."""
        ...
