# Gheras Social Router — Architecture

## Scope

V1 is a single Python service that coordinates comment/message handling for Facebook, Instagram, Telegram, and YouTube. External integrations stay behind adapters, and the existing fatwa bot remains behind a narrow integration boundary.

## High-level flow

```text
Facebook  ─┐
Instagram ─┤
Telegram  ─┼─> Collector ─> Persist First ─> Moderation ─> Classification ─┬─> FAQ
YouTube   ─┘                                                                ├─> Supervisor
                                                                            └─> Fatwa Bridge
                                                                                     │
                                                                                     ▼
                                                                            Publishing Dispatcher
                                                                                     │
                                                            ┌────────────┬────────────┼───────────┐
                                                            ▼            ▼            ▼           ▼
                                                         Facebook     Instagram    Telegram    YouTube
```

## Boundaries

### HTTP application

FastAPI owns health endpoints and, in later phases, inbound webhook endpoints. Importing or starting the application must not require production credentials.

### Platform adapters

Facebook, Instagram, Telegram, and YouTube integrations implement adapter contracts. Domain and routing logic must not call vendor SDKs or raw HTTP endpoints directly.

Each adapter normalizes platform-specific identifiers and payloads into the shared inbound event model. Platform-specific details may be preserved only where needed for correct routing/publishing and must not leak into core state-machine semantics.

### Durable event boundary

Every accepted inbound event is persisted before moderation, classification, FAQ resolution, supervisor handling, fatwa routing, or publishing work begins.

The SQLite durable layer contains persistent concerns including:

- `inbound_events`: normalized accepted events and processing state.
- `processing_attempts`: sanitized attempt history and retry metadata.
- `outbound_actions`: durable publish intents/results with unique idempotency keys.
- `moderation_results`: one normalized moderation decision per event.
- `classification_results`: one normalized semantic route per eligible event.
- `faq_entries`: immutable versioned approved operational answers.
- `faq_resolutions`: one exact-key FAQ resolution per classified event.
- `supervisor_escalations`: one durable human escalation per eligible event.
- `supervisor_responses`: one accepted human response per escalation.

Inbound uniqueness is `(platform, external_event_key)`. Outbound uniqueness is `idempotency_key`. Duplicate work must resolve to the existing durable record instead of creating a second semantic action.

### Processing state machine

Core event state changes are explicit domain transitions. V1 includes:

- `received`
- `processing`
- `waiting_human`
- `completed`
- `failed_retryable`
- `failed_terminal`

Terminal states do not transition unless a future explicit recovery mechanism is introduced.

### Moderation boundary

Moderation occurs after persist-first ingestion and before semantic classification.

A provider-neutral async `ModerationAdapter` returns normalized evidence only. A deterministic local policy maps the evidence to one routing-only disposition:

- `allow_routing`
- `human_review`
- `block_routing`

`block_routing` does not authorize hide/delete/report actions. Missing coverage, low confidence, malformed evidence, contradictory evidence, and adapter failure fail closed toward human review rather than automatic routing.

### Classification boundary

Classification runs only after durable `allow_routing` moderation. The async adapter produces routing evidence only; the deterministic local policy is authoritative.

The only V1 routes are:

- `FAQ`
- `SUPERVISOR`
- `FATWA`

Safety rules include:

- `religious_possible=true` always forces `FATWA`.
- an explicit FATWA proposal remains `FATWA`.
- low-confidence FAQ becomes `SUPERVISOR`.
- FAQ without a valid compact key becomes `SUPERVISOR`.
- adapter failure/malformed output becomes `SUPERVISOR`.
- the classifier never generates user-facing answer text or a fatwa.

`classification_results` deliberately stores no prompt, chain-of-thought, raw provider response, or answer payload.

### Approved FAQ boundary

FAQ resolution is eligible only for a durable `FAQ` classification containing an exact key.

The model never supplies the answer. Answers come only from `faq_entries`, which are versioned and preserve approval provenance (`approved_by`, `approved_at`, `source_ref`). Historical versions are not rewritten in place, and SQLite permits at most one active version for a key.

Resolution is exact-key only; no fuzzy key substitution and no generated fallback are allowed. Missing, disabled, or invalid keys create `supervisor_required` resolution instead of answer text.

Each `faq_resolution` links the event and classification to the exact approved entry used. Duplicate/racing workers converge on one resolution. If an entry is later disabled, the historical resolution remains auditable but its answer text is no longer eligible for future publishing.

### Human supervisor boundary

Human escalation is eligible only when:

1. classification is explicitly `SUPERVISOR`; or
2. a `FAQ` classification has a durable `supervisor_required` FAQ resolution.

FATWA-routed events and successfully resolved FAQ events are not eligible for this workflow.

Telegram is the intended V1 supervisor transport, but transport is not the source of truth. `supervisor_escalations` and `supervisor_responses` persist workflow state independently of Telegram.

The escalation lifecycle is:

```text
pending_dispatch -> awaiting_response -> responded
       │                  │
       └──────────────> cancelled
```

The service prepares a minimal normalized dispatch request but does not perform a live Telegram call in Phase 5. Successful external dispatch is recorded only after a transport returns a stable external thread identifier. Failed attempts increment durable attempt metadata without storing raw exception text.

One accepted human response is allowed per escalation. Duplicate identical provider updates are idempotent; reuse of an external response key or escalation with different response semantics fails closed as a conflict. Supervisor responses are human-provided content and are not automatically published by this phase.

### Fatwa bot bridge

The existing fatwa bot remains a separate system boundary. Gheras exchanges only the information required to route a question and consume an approved supervised result. Gheras AI must never fabricate or infer a fatwa.

### Publishing dispatcher

Publishing is separated from classification, FAQ resolution, supervisor response handling, and fatwa handling. A later dispatcher selects the correct Facebook/Instagram/Telegram/YouTube adapter and uses durable outbound action records to prevent duplicate publishing.

## Reliability rules

- Persist first, process later.
- Inbound platform events are idempotent.
- Moderation, classification, FAQ resolution, and supervisor escalation are durable.
- Duplicate/racing workers converge on one semantic durable result.
- Outbound replies/actions are idempotent.
- SQLite foreign keys are enabled.
- WAL mode and busy timeout are enabled where safe.
- External failure must not silently lose accepted work.
- Low-confidence or uncertain routing escalates rather than guesses.
- Possible religious content fails toward FATWA routing, never an AI-generated answer.
- Secrets come from environment variables and are never committed.
- Raw external provider payloads are not blindly persisted.

## Current implementation boundary

- Phase 0: application/configuration/CI bootstrap.
- Phase 1: durable event core, retries, state machine, inbound/outbound idempotency.
- Phase 2: mock-first fail-closed moderation and durable moderation results.
- Phase 3: mock-first routing-only classification with religious safety override.
- Phase 4: versioned approved FAQ store and exact-key durable resolution.
- Phase 5: durable human supervisor escalation/response workflow and transport contract, with no live Telegram calls.
