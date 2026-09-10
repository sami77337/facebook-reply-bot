# Gheras Social Router — Human Gates Before Live Activation

This document lists actions that require explicit repository-owner approval. None of these actions is performed by Phase 10.

## HG-01 — Legacy Facebook bot cutover

**Status:** REQUIRED BEFORE LIVE

The repository still contains `.github/workflows/bot.yml`, which defines `Auto Reply Workflow` with a 30-minute schedule and manual dispatch. That workflow runs the legacy root `main.py` with Facebook credentials and therefore represents a real outbound side-effect path.

Available repository workflow history shows no `Auto Reply Workflow` in the newest 100 runs. An older available run exists from 2025-12-06 and failed. This evidence is not sufficient to assert that the workflow definition is disabled.

Before Gheras V1 is allowed to publish live, the owner must explicitly choose and approve a cutover plan that prevents the legacy bot and the new router from replying concurrently.

Possible owner-approved actions include disabling/removing the legacy workflow at cutover time, or proving that it is already disabled and cannot execute. Phase 10 does not change it.

## HG-02 — Public tracked runtime-data cleanup

**Status:** REQUIRED

The public repository still tracks:

- `log.txt`, containing historical Facebook comment identifiers, timestamps, and reply text;
- `seen_comments.json`, a legacy runtime-state file, currently empty;
- `bot_activity.log`, currently empty.

`.gitignore` now excludes these runtime artifacts, but ignore rules do not remove files already tracked.

The owner must explicitly approve removal of tracked runtime artifacts from the active code line. Any Git history rewrite is a separate, higher-impact decision and must not be performed implicitly.

## HG-03 — Legacy religious-response retirement

**Status:** REQUIRED BEFORE NEW ROUTER BECOMES AUTHORITATIVE

The legacy `responses.json` contains keyword rules such as `(الله|يارب|جزاك)` that can produce a generic religious reply without passing through the new moderation/classification/FATWA safety boundary.

The new V1 architecture does not import this legacy logic. Nevertheless, the legacy runtime must not remain an authoritative public-reply path after V1 cutover.

## HG-04 — Live platform credentials and scopes

**Status:** NOT PROVISIONED / NOT VERIFIED

No production credentials are committed. `.env.example` contains empty placeholders only.

Before live integration, the owner must explicitly provision and validate the minimum required credentials/scopes for:

- Facebook / Instagram;
- Telegram;
- YouTube;
- the selected moderation/classification provider, if used;
- the supervised FATWA bridge.

Credential values must remain outside Git.

## HG-05 — Live platform adapter implementation

**Status:** NOT IMPLEMENTED BY DESIGN

Current Facebook, Instagram, Telegram, and YouTube adapters are mock-first normalization/client boundaries. Production OAuth, webhook verification, polling, token refresh, rate-limit behavior, and network clients are intentionally absent.

Each live adapter requires separate implementation, provider-specific contract tests, sandbox/staging validation, and explicit approval before enabling external side effects.

## HG-06 — Supervised FATWA-system integration

**Status:** NOT CONNECTED BY DESIGN

The Phase 7 bridge is a durable contract only. The existing FATWA system/runtime was not modified or called.

The owner must approve the exact integration contract, authentication mechanism, approved-result provenance format, operational ownership, and failure/reconciliation procedure before connection.

## HG-07 — FATWA publication policy

**Status:** SAFE DEFAULT ACTIVE IN CODE

The code default is `telegram_only`; therefore an approved FATWA result is not automatically posted to the origin comment.

Changing production policy to `origin_only` or `both` requires explicit owner approval after the supervised FATWA integration has been validated.

## HG-08 — Dependency/security assessment

**Status:** REQUIRED BEFORE LIVE

Functional CI installs dependencies from version ranges in `pyproject.toml`. Phase 10 does not claim that those resolved packages, or the legacy `requirements.txt`, are free of known vulnerabilities.

Before live activation, run and record an approved software-composition/dependency vulnerability assessment and decide the production pin/lock strategy.

## HG-09 — Staging Shadow Mode evaluation

**Status:** REQUIRED BEFORE LIVE PUBLISHING

Run the finished router against representative staging or safely replayed data in Shadow Mode. Review route/outcome aggregates and investigate unexpected `blocked`, `not_ready`, `would_wait_human`, and `would_route_fatwa` cases before permitting live publication.

No production reply publishing should be enabled during this gate.

## HG-10 — Production configuration and operations

**Status:** REQUIRED

Before production, explicitly approve:

- deployment environment and database location/backup policy;
- log retention and redaction policy;
- operational ownership for `dispatching`/`uncertain` publication reconciliation;
- monitoring/alerting;
- webhook/network ingress controls where applicable;
- rollback/cutover procedure.

## HG-11 — Merge/promotion to `main`

**Status:** OWNER APPROVAL REQUIRED

The implementation is maintained as stacked phase branches/PRs. Phase 10 does not merge them to `main`.

Promotion must occur only after prerequisite PR reviews are complete and the owner explicitly approves the merge/cutover sequence.
