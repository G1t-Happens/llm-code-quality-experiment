CREATE TABLE users
(
    id       BIGSERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    userpw   VARCHAR(255) NOT NULL,
    email    VARCHAR(255) NOT NULL,
    isadmin  BOOLEAN      NOT NULL
);

CREATE TABLE addresses
(
    id            BIGSERIAL PRIMARY KEY,
    user_id       BIGINT       NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    street        VARCHAR(255) NOT NULL,
    house_number  VARCHAR(20)  NOT NULL,
    postal_code   VARCHAR(20)  NOT NULL,
    city          VARCHAR(255) NOT NULL,
    country       VARCHAR(255) NOT NULL,
    address_type  VARCHAR(20)  NOT NULL DEFAULT 'PRIVATE'
);

CREATE INDEX idx_addresses_user_id ON addresses(user_id);