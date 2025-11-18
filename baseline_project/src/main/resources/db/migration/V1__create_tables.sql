-- Create the 'users' table to store user-related information
CREATE TABLE users
(
    id       BIGSERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    userpw   VARCHAR(255) NOT NULL,
    email    VARCHAR(255) NOT NULL,
    isadmin  BOOLEAN      NOT NULL
);

-- Create the 'addresses' table to store address-related information linked to users
CREATE TABLE addresses
(
    id           BIGSERIAL PRIMARY KEY,
    user_id      BIGINT       NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    street       VARCHAR(255) NOT NULL,
    house_number VARCHAR(20)  NOT NULL,
    postal_code  VARCHAR(20)  NOT NULL,
    city         VARCHAR(255) NOT NULL,
    country      VARCHAR(255) NOT NULL,
    address_type VARCHAR(20)  NOT NULL DEFAULT 'PRIVATE'
);

-- Create an index on the 'user_id' column in the 'addresses' table for faster lookups
CREATE INDEX idx_addresses_user_id ON addresses (user_id);
