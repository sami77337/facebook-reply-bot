"""SQLite schema for Gheras Social Router Phase 1."""

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS inbound_events (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL CHECK (platform IN ('facebook', 'instagram', 'telegram', 'youtube')),
    external_event_key TEXT NOT NULL,
    external_event_id TEXT,
    external_comment_id TEXT,
    external_post_id TEXT,
    author_id TEXT,
    text TEXT,
    media_json TEXT,
    correlation_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN (
            'received',
            'processing',
            'waiting_human',
            'completed',
            'failed_retryable',
            'failed_terminal'
        )
    ),
    retry_count INTEGER NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
    next_retry_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (platform, external_event_key)
);

CREATE INDEX IF NOT EXISTS idx_inbound_events_status_retry
ON inbound_events (status, next_retry_at);

CREATE TABLE IF NOT EXISTS processing_attempts (
    id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL CHECK (attempt_number > 0),
    started_at TEXT NOT NULL,
    finished_at TEXT,
    outcome TEXT,
    error_code TEXT,
    error_message TEXT,
    FOREIGN KEY (event_id) REFERENCES inbound_events(id) ON DELETE CASCADE,
    UNIQUE (event_id, attempt_number)
);

CREATE INDEX IF NOT EXISTS idx_processing_attempts_event
ON processing_attempts (event_id, attempt_number);

CREATE TABLE IF NOT EXISTS outbound_actions (
    id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    platform TEXT NOT NULL CHECK (platform IN ('facebook', 'instagram', 'telegram', 'youtube')),
    action_type TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    external_result_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (event_id) REFERENCES inbound_events(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_outbound_actions_event
ON outbound_actions (event_id, created_at);
"""
