CREATE TABLE Rule (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patterns VARCHAR(500) NOT NULL,
    response TEXT,
    priority INT NOT NULL DEFAULT 5, -- 1-10
    tag VARCHAR(50) DEFAULT NULL,
    post_id BIGINT DEFAULT NULL,  -- null means global
    auto_reply TINYINT(1) DEFAULT 1,
    reply_once TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_patterns ON Rule(patterns);
CREATE INDEX idx_post_id ON Rule(post_id);
CREATE INDEX idx_tag ON Rule(tag);
