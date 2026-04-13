SET TIME ZONE 'Asia/Kolkata';

DROP table if exists  url_shortener;    

CREATE TABLE url_shortener (
    id SERIAL PRIMARY KEY,
    long_url VARCHAR(2048) NOT NULL,
    short_url VARCHAR(255) NOT null,
    created_at timestamp default CURRENT_TIMESTAMP
);