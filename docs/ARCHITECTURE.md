# Gheras Social Router — Architecture

## Scope

V1 is a single Python service that coordinates comment/message handling for Facebook, Instagram, Telegram, and YouTube. External integrations stay behind adapters, and the existing fatwa bot remains behind a narrow integration boundary.

## High-level flow

```text
Facebook  ─┐
Instagram ─┤
Telegram  ─┼─> Collector ─> Persist-First Core ─> Moderation ─> Classification ─┬─> Approved FAQ reply
YouTube   ─┘                                                                     ├─> Human supervisor
                                                                                 └─> Fatwa bot bridge
                                                                                           │
                                                                                           ▼
                                                                                 Publishing Dispatcher
                                                                                           │
                                                                 ┌─────────────┬───────────┼───────────┐
                                                                 ▼             ▼           ▼           ▼
                                                              Facebook      Instagram   Telegram    YouTube
```

## Boundaries

### HTTP application

FastAPI owns health endpoints and, in later phases, inbound webhook endpoints. Importing or starting the application must not require production credentials.

### Platform adapters

Facebook, Instagram, Telegram, and YouTube integrations implement adapter contracts. Domain and routing logic must not call vendor SDKs or raw HTTP endpoints directly.

Each adapter normalizes platform-specific identifiers and payloads into the shared inbound event model. Platform-specific details may be preserved only where needed for correct routing/publishing and must not leak into core state-machine semantics.

### Durable event boundary

Every accepted inbound event is persisted before moderation, classification, or publishing work begins.

The V1 durable core uses SQLite behind repository/service abstractions and contains persistent concerns including:

- `inbound_events`: normalized accepted events and their processing state.
- `processing_attempts`: sanitized attempt history and retry metadata.
- `outbound_actions`: durable publish intents/results with unique idempotency keys.
- `moderation_results`: one normalized, auditable moderation routing decision per inbound event.

The uniqueness boundary for inbound work is `(platform, external_event_key)`. The uniqueness boundary for outbound work is `idempotency_key`.

A duplicate inbound delivery must resolve to the original internal event instead of creating a second record. A duplicate outbound intent must not create a second action.

### Processing state machine

Core processing state changes are explicit domain transitions rather than arbitrary database updates. V1 includes at least:

- `received`
- `processing`
- `waiting_human`
- `completed`
- `failed_retryable`
- `failed_terminal`

Terminal states do not transition unless a future explicit recovery mechanism is introduced.

### Moderation boundary

Moderation happens after persist-first ingestion and before semantic classification.

The moderation design is split into three responsibilities:

1. A provider-neutral async `ModerationAdapter` returns normalized moderation evidence only.
2. A deterministic local policy maps that evidence to one routing-only disposition.
3. A durable moderation repository stores one auditable result for the inbound event.

The V1 routing-only dispositions are:

- `allow_routing`: moderation evidence is explicitly safe and sufficiently confident for semantic routing to continue.
- `human_review`: evidence is missing, uncertain, low-confidence, unsupported, malformed, or the moderation adapter failed.
- `block_routing`: sufficiently confident unsafe evidence prevents automated semantic routing.

`block_routing` is not an authorization to hide, delete, report, or otherwise mutate external content. External moderation enforcement is outside this phase and requires an explicit later policy and adapter action.

Text/media coverage is fail-closed. If normalized media exists but the adapter did not actually assess it, the event cannot receive `allow_routing`. Likewise, an event with no assessable text or media goes to human review rather than being guessed safe.

Moderation adapter exceptions are converted to a normalized human-review result. Raw exception traces, credentials, authorization headers, provider payloads, and secret-bearing diagnostics are not persisted in `moderation_results`.

The moderation result is idempotent per `event_id`. Duplicate or racing workers resolve to the same persisted result instead of creating multiple moderation rows.

### AI adapters

Moderation and classification are separate adapters. Classification is routing-only; religious questions must never receive an AI-generated religious answer.

### Approved FAQ store

Operational answers such as schedules, registration information, and links come from an approved store. The classifier may select an intent/key but may not invent the answer.

### Human supervisor workflow

Unknown or low-confidence non-religious content is routed to supervisors. Telegram is the V1 supervisor interface, but supervisor transport remains separate from core routing logic.

### Fatwa bot bridge

The existing fatwa bot remains a separate system boundary. This service exchanges only the information required to route a question and publish an approved response. Public documentation should not expose unnecessary internal workflow details.

### Publishing dispatcher

Publishing is separated from classification and response composition. A dispatcher selects the correct adapter for Facebook, Instagram, Telegram, or YouTube and uses durable outbound action records to prevent duplicate publishing.

## Reliability rules

- Persist first, process later.
- Inbound platform events are idempotent.
- Moderation decisions are durable and idempotent per inbound event.
- Outbound replies/actions are idempotent.
- Accepted work and processing state survive process restarts.
- SQLite foreign keys are enabled.
- WAL mode and a sensible busy timeout are preferred where safe for V1.
- External API failures must not silently lose accepted work.
- Low-confidence routing escalates to a human rather than guessing.
- Secrets are supplied through process environment variables and are never committed.
- Raw external payloads are not blindly persisted; store normalized fields required by the router.

## Current implementation boundary

Phase 0 established configuration, the HTTP application, adapter interfaces, tests, and CI.

Phase 1 implements the durable core and intentionally contains no real Meta, Telegram, YouTube/Google, OpenAI, or fatwa-bot calls.

Phase 2 adds the mock-first moderation domain, async adapter contract, deterministic fail-closed policy, durable moderation-result repository, and idempotent moderation service. It still performs no live external moderation call and no external hide/delete/report action.
