# Gheras Social Router — Human Gates Before Live Activation

This document tracks only actions that still require external credentials, live provider validation, irreversible repository operations, or production activation decisions. Routine non-live engineering proceeds without waiting for additional approval.

## HG-01 — Legacy Facebook bot cutover

**Status:** OWNER-CONFIRMED STOPPED / ACTIVE-CODE-LINE RETIREMENT COMPLETE IN PHASE 11

On 2026-09-10 the repository owner explicitly confirmed that the legacy bot is already stopped and authorized proceeding without further routine approval waits.

Phase 11 therefore makes the future active code line fail-closed:

- `.github/workflows/bot.yml` is removed from the Phase 11 branch;
- root `main.py` is replaced by a retired fail-closed stub;
- the historical implementation remains recoverable from Git history.

No claim is made that Phase 11 changed the already-existing production runtime state. The owner supplied that runtime-state assertion; the code-line changes prevent accidental reactivation after promotion.

## HG-02 — Public tracked runtime-data cleanup

**Status:** ACTIVE-CODE-LINE CLEANUP COMPLETE / HISTORY REWRITE NOT PERFORMED

Phase 11 removes the following tracked runtime artifacts from the active branch:

- `log.txt`;
- `seen_comments.json`;
- `bot_activity.log`.

`.gitignore` continues to exclude these files.

Historical Git objects are intentionally not rewritten. Rewriting public repository history is a separate high-impact/irreversible operation and is not required to continue engineering or sandbox validation.

## HG-03 — Legacy religious-response retirement

**Status:** AUTHORITATIVE RUNTIME PATH RETIRED IN PHASE 11

The historical `responses.json` remains repository evidence, but the old entry point is fail-closed and its scheduled workflow is removed on the Phase 11 branch. The new application does not import the legacy regex response logic.

After promotion, the legacy rules must remain non-authoritative; religious routing continues exclusively through the governed moderation/classification/FATWA path.

## HG-04 — Live platform credentials and scopes

**Status:** NOT PROVISIONED / NOT VERIFIED

No production credentials are committed. `.env.example` contains empty placeholders only.

Before sandbox/live provider validation, provision the minimum required credentials/scopes outside Git for:

- Facebook / Instagram;
- Telegram;
- YouTube;
- the selected moderation/classification provider, if used;
- the supervised FATWA bridge.

Credential values must never be posted in chat or committed to the repository.

## HG-05 — Live platform adapter implementation

**Status:** PREPARATION IMPLEMENTED / NETWORK CLIENTS STILL DISABLED BY DESIGN

Phase 11 adds provider-specific security/readiness contracts, including Meta webhook verification, Telegram webhook-secret validation, YouTube polling/quota metadata, environment configuration placeholders, and redaction-safe readiness evaluation.

Real OAuth/token exchange, webhook registration, polling/network transport, token refresh, and provider HTTP clients remain outside the core and require sandbox validation before activation.

## HG-06 — Supervised FATWA-system integration

**Status:** NOT CONNECTED BY DESIGN

The Phase 7 bridge remains a durable contract. No external FATWA runtime is called by Phase 11.

The real connection requires authentication material, approved-result provenance verification, and failure/reconciliation validation in sandbox/staging before activation.

## HG-07 — FATWA publication policy

**Status:** SAFE DEFAULT ACTIVE IN CODE

The default remains `telegram_only`. An approved FATWA result is therefore not automatically posted back to the origin comment.

Any later move to `origin_only` or `both` remains a production policy decision after supervised FATWA integration validation.

## HG-08 — Dependency/security assessment

**Status:** REQUIRED BEFORE LIVE

Functional CI validates installation and tests but does not constitute a software-composition vulnerability assessment. Run and record SCA/dependency review and choose a production lock/pinning strategy before live activation.

## HG-09 — Staging Shadow Mode evaluation

**Status:** REQUIRED BEFORE LIVE PUBLISHING

Run the router against representative sandbox/staging or safely replayed data in Shadow Mode. Review route/outcome aggregates and investigate unexpected `blocked`, `not_ready`, `would_wait_human`, and `would_route_fatwa` cases before permitting live publication.

No production reply publishing is authorized during this gate.

## HG-10 — Production configuration and operations

**Status:** REQUIRED

Before production activation, finalize:

- deployment environment and database location/backup policy;
- log retention and redaction policy;
- operational ownership for `dispatching`/`uncertain` reconciliation;
- monitoring and alerting;
- webhook/network ingress controls;
- rollback/cutover procedure.

## HG-11 — Merge/promotion to `main`

**Status:** REVIEW/CI GATE REQUIRED

Implementation remains on stacked phase branches/PRs. Routine engineering does not wait for additional owner messages, but promotion to `main` must still preserve the project rule: relevant CI and independent review gates must pass before merge.
