-- Insert demo users into the 'users' table - pw: Root2131
INSERT INTO users (username, password, email, isadmin)
VALUES ('Daniel', '$2a$10$lzr8dkyEhJjASvHeKoBo5e5hUiyLPJNXbGLZTcX0JZ35VDfDbWurW', 'daniel@test.de', true),
       ('Johannes', '$2a$10$lzr8dkyEhJjASvHeKoBo5e5hUiyLPJNXbGLZTcX0JZ35VDfDbWurW', 'johannes@test.de', false),
       ('User3', '$2a$12$KK5nmVyXDRFatZHIS5UWbOVrTMeg4ZYljIbjxsGxcMuaLYN6ilh02', 'user3@test.de', false),
       ('User4', '$2a$12$KK5nmVyXDRFatZHIS5UWbOVrTMeg4ZYljIbjxsGxcMuaLYN6ilh02', 'user4@test.de', false),
       ('User5', '$2a$12$KK5nmVyXDRFatZHIS5UWbOVrTMeg4ZYljIbjxsGxcMuaLYN6ilh02', 'user5@test.de', false),
       ('User6', '$2a$12$KK5nmVyXDRFatZHIS5UWbOVrTMeg4ZYljIbjxsGxcMuaLYN6ilh02', 'user6@test.de', false),
       ('User7', '$2a$12$KK5nmVyXDRFatZHIS5UWbOVrTMeg4ZYljIbjxsGxcMuaLYN6ilh02', 'user7@test.de', false),
       ('User8', '$2a$12$KK5nmVyXDRFatZHIS5UWbOVrTMeg4ZYljIbjxsGxcMuaLYN6ilh02', 'user8@test.de', false),
       ('User9', '$2a$12$KK5nmVyXDRFatZHIS5UWbOVrTMeg4ZYljIbjxsGxcMuaLYN6ilh02', 'user9@test.de', false),
       ('User10', '$2a$12$KK5nmVyXDRFatZHIS5UWbOVrTMeg4ZYljIbjxsGxcMuaLYN6ilh02', 'user10@test.de', false);

-- Insert addresses into the 'addresses' table
INSERT INTO addresses (user_id, street, house_number, postal_code, city, country, address_type)
VALUES (1, 'Musterstraße', '42', '80331', 'München', 'Deutschland', 'PRIVATE'),
       (1, 'Bahnhofstraße', '12a', '10115', 'Berlin', 'Deutschland', 'BUSINESS'),
       (1, 'Schlossallee', '1', '14193', 'Berlin', 'Deutschland', 'SHIPPING'),
       (2, 'Hauptstraße', '7', '80331', 'München', 'Deutschland', 'PRIVATE'),
       (2, 'Rosenweg', '23b', '85521', 'Ottobrunn', 'Deutschland', 'SHIPPING'),
       (3, 'Berliner Allee', '56', '40212', 'Düsseldorf', 'Deutschland', 'PRIVATE');
