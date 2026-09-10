# Phase 14 — End-to-End Sandbox Assembly & Replay Validation

Objective: compose the completed V1 boundaries into a side-effect-free end-to-end sandbox runtime and prove replay behavior across all four platforms before any real provider credential or registration step.

Required gates:
- no production credential or provider registration;
- no live network call; injected fake/MockTransport boundaries only;
- inbound event must persist before moderation/classification;
- moderation remains authoritative before classification;
- FAQ answers come only from active approved entries;
- supervisor path requires accepted human response evidence;
- FATWA path never generates/rephrases a religious answer and remains origin-blocked by default policy;
- shadow evaluation must create no outbound action;
- publishing plan may be evaluated, but external provider invocation is replaced by recording fakes;
- duplicate replay must converge without duplicate durable events/actions;
- restart replay must preserve idempotency;
- four-platform matrix required;
- final output is a redaction-safe replay report with counts/outcomes only.

Exit: Ruff/Mypy/Pytest PASS, adversarial review PASS, and no external side effect observed.
