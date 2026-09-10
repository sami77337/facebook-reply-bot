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

Facebook, Instagram, Telegram, and YouTube integrations implement provider-specific adapter modules while domain/services remain provider-neutral.

Phase 6 implements only pure normalization plus injected client protocols. It deliberately does not implement production OAuth, webhook verification, polling, token refresh, or network clients. Stable inbound identities are normalized as follows:

- Facebook: comment id.
- Instagram: comment id.
- Telegram: `chat_id:message_id`; update id remains delivery metadata.
- YouTube: comment id; thread id may be retained separately.

Adapters preserve Arabic/Unicode text verbatim and fail closed when required identifiers or text are missing. Reply publishers and the Telegram supervisor transport delegate only to injected client protocols. Raw provider payloads are not persisted.

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
- `fatwa_bridge_requests`: one durable supervised-fatwa request per FATWA event.
- `fatwa_bridge_results`: one normalized attributed external result per bridge request.

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

Human escalation is eligible only when classification is explicitly `SUPERVISOR`, or a `FAQ` classification has a durable `supervisor_required` FAQ resolution.

FATWA-routed events and successfully resolved FAQ events are not eligible for this workflow. Telegram is the intended V1 supervisor transport, but transport is not the source of truth; SQLite holds escalation and response state.

The escalation lifecycle is:

```text
pending_dispatch -> awaiting_response -> responded
       │                  │
       └──────────────> cancelled
```

One accepted human response is allowed per escalation. Duplicate identical provider updates are idempotent; conflicting response or transport evidence fails closed.

### Fatwa bot bridge

A `FATWA` classification is only a routing decision and never contains a religious answer. Gheras cannot generate, rewrite, summarize, infer, complete, or improve a fatwa.

Phase 7 adds a durable bridge boundary to an external supervised fatwa system. Eligibility requires an exact durable classification route of `FATWA`. The request lifecycle is:

```text
pending_dispatch -> awaiting_result -> approved_result
                              └──────> rejected
       │                  │
       └──────────────────┴────> cancelled
```

The bridge prepares only minimal normalized question/identity data and performs no live call in this phase. Failed dispatch attempts increment a counter without storing raw provider errors. Successful dispatch records only a stable bridge name and external case id.

A bridge result becomes publishable evidence only when the external result is `approved` and includes all of: non-empty answer text supplied by the supervised system, a non-empty `approved_by` value, a non-empty `source_ref`, and a stable unique external result key. A rejected result is structurally forbidden from carrying answer text or an approver.

`fatwa_bridge_results` preserves the exact approved external text; Gheras does not transform it. Duplicate identical results are idempotent, while reuse of a request/result key with different semantics fails closed. The existing `telegram-fatwa-bot-v2` runtime and repository remain untouched until a separate Live Integration human gate.

### Publishing dispatcher

Publishing is separated from classification, FAQ resolution, supervisor response handling, and fatwa handling. A later dispatcher selects the correct Facebook/Instagram/Telegram/YouTube adapter and uses durable outbound action records to prevent duplicate publishing.

## Reliability rules

- Persist first, process later.
- Inbound platform events are idempotent.
- Moderation, classification, FAQ resolution, supervisor escalation, and fatwa bridge state are durable.
- Duplicate/racing workers converge on one semantic durable result.
- Outbound replies/actions are idempotent.
- SQLite foreign keys are enabled.
- WAL mode and busy timeout are enabled where safe.
- External failure must not silently lose accepted work.
- Low-confidence or uncertain routing escalates rather than guesses.
- Possible religious content fails toward FATWA routing, never an AI-generated answer.
- Fatwa text is publishable only after explicit external approval/provenance evidence.
- Secrets come from environment variables and are never committed.
- Raw external provider payloads are not blindly persisted.

## Current implementation boundary

- Phase 0: application/configuration/CI bootstrap.
- Phase 1: durable event core, retries, state machine, inbound/outbound idempotency.
- Phase 2: mock-first fail-closed moderation and durable moderation results.
- Phase 3: mock-first routing-only classification with religious safety override.
- Phase 4: versioned approved FAQ store and exact-key durable resolution.
- Phase 5: durable human supervisor escalation/response workflow; no live Telegram calls.
- Phase 6: mock-first four-platform normalizers and injected publisher/transport clients; no live network clients.
- Phase 7: durable supervised fatwa bridge request/result lifecycle; no legacy-bot call or modification.
