SET TIME ZONE 'Asia/Kolkata';

DROP table if exists  url_shortener;   

CREATE TABLE url_shortener (
    id SERIAL PRIMARY KEY,
    long_url VARCHAR(2048) NOT NULL,
    short_code VARCHAR(255) unique,
    short_url VARCHAR(255) unique,
    created_at timestamp default CURRENT_TIMESTAMP,
    expiry timestamp
);

TRUNCATE TABLE url_shortener RESTART IDENTITY;

SELECT * FROM url_shortener;