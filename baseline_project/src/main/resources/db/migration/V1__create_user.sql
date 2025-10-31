CREATE TABLE users
(
    id       BIGSERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    userpw   VARCHAR(255) NOT NULL,
    email    VARCHAR(255) NOT NULL,
    isadmin  BOOLEAN      NOT NULL
);