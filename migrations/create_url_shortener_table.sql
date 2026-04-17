SET TIME ZONE 'Asia/Kolkata';

DROP table if exists  url_shortener;   


CREATE TABLE url_shortener (
    id BIGSERIAL PRIMARY KEY,
    short_code VARCHAR(10) UNIQUE NOT NULL,
    short_url TEXT NOT NULL,
    long_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    last_accessed TIMESTAMP NULL,
    is_deleted BOOLEAN DEFAULT FALSE,
    click_count BIGINT DEFAULT 0
);

TRUNCATE TABLE url_shortener RESTART IDENTITY;

SELECT * FROM url_shortener;