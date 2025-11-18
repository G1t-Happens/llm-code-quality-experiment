-- Insert sample users into the "users" table with hashed passwords and timestamps - pw: Root2131
INSERT INTO users (username, password_hash, email, is_admin, created, updated)
VALUES ('Daniel', '$2a$10$lzr8dkyEhJjASvHeKoBo5e5hUiyLPJNXbGLZTcX0JZ35VDfDbWurW', 'daniel@test.de', true,
        '2023-07-17 15:38:58+00', '2023-07-17 15:38:58+00'),
       ('Johannes', '$2a$10$lzr8dkyEhJjASvHeKoBo5e5hUiyLPJNXbGLZTcX0JZ35VDfDbWurW', 'johannes@test.de', false,
        '2023-07-17 15:38:58+00', '2023-07-17 15:38:58+00'),
       ('User3', '$2a$12$KK5nmVyXDRFatZHIS5UWbOVrTMeg4ZYljIbjxsGxcMuaLYN6ilh02', 'user3@test.de', false,
        '2023-07-17 15:38:58+00', '2023-07-17 15:38:58+00'),
       ('User4', '$2a$12$KK5nmVyXDRFatZHIS5UWbOVrTMeg4ZYljIbjxsGxcMuaLYN6ilh02', 'user4@test.de', false,
        '2023-07-17 15:38:58+00', '2023-07-17 15:38:58+00'),
       ('User5', '$2a$12$KK5nmVyXDRFatZHIS5UWbOVrTMeg4ZYljIbjxsGxcMuaLYN6ilh02', 'user5@test.de', false,
        '2023-07-17 15:38:58+00', '2023-07-17 15:38:58+00'),
       ('User6', '$2a$12$KK5nmVyXDRFatZHIS5UWbOVrTMeg4ZYljIbjxsGxcMuaLYN6ilh02', 'user6@test.de', false,
        '2023-07-17 15:38:58+00', '2023-07-17 15:38:58+00'),
       ('User7', '$2a$12$KK5nmVyXDRFatZHIS5UWbOVrTMeg4ZYljIbjxsGxcMuaLYN6ilh02', 'user7@test.de', false,
        '2023-07-17 15:38:58+00', '2023-07-17 15:38:58+00'),
       ('User8', '$2a$12$KK5nmVyXDRFatZHIS5UWbOVrTMeg4ZYljIbjxsGxcMuaLYN6ilh02', 'user8@test.de', false,
        '2023-07-17 15:38:58+00', '2023-07-17 15:38:58+00'),
       ('User9', '$2a$12$KK5nmVyXDRFatZHIS5UWbOVrTMeg4ZYljIbjxsGxcMuaLYN6ilh02', 'user9@test.de', false,
        '2023-07-17 15:38:58+00', '2023-07-17 15:38:58+00'),
       ('User10', '$2a$12$KK5nmVyXDRFatZHIS5UWbOVrTMeg4ZYljIbjxsGxcMuaLYN6ilh02', 'user10@test.de', false,
        '2023-07-17 15:38:58+00', '2023-07-17 15:38:58+00');

-- Insert sample products into the "products" table with descriptions, prices, stock, and timestamps
INSERT INTO products (title, description, price, stock, created, updated)
VALUES ('MacBook Pro 14" M3', 'Apple MacBook Pro mit M3 Chip', 2199.0000, 12, now(), now()),
       ('iPhone 16 Pro', 'Apple iPhone 16 Pro 256GB', 1299.0000, 25, now(), now()),
       ('AirPods Pro 2', 'Noise Cancelling In-Ear', 279.0000, 50, now(), now()),
       ('Logitech MX Master 3S', 'Ergonomische Maus', 119.9900, 80, now(), now()),
       ('Samsung 34" Ultrawide', 'Curved Gaming Monitor', 649.0000, 15, now(), now()),
       ('Anker Powerbank 24k', '140W Power Delivery', 149.9900, 100, now(), now());

-- Insert sample orders into the "orders" table, linking users and including order status and totals
INSERT INTO orders (user_id, order_number, order_status, total_amount, created, updated)
VALUES (1, 'ORD-2025-000001', 'COMPLETED', 3817.9900, '2025-03-15 14:22:10+01', '2025-03-20 09:15:33+01'),
       (1, 'ORD-2025-000008', 'SHIPPED', 918.9800, '2025-10-28 09:11:45+01', '2025-11-15 12:30:22+01'),
       (2, 'ORD-2025-000003', 'PAID', 279.0000, '2025-08-20 18:45:12+02', '2025-08-20 19:10:05+02'),
       (2, 'ORD-2025-000012', 'PROCESSING', 768.9900, '2025-11-12 11:07:33+01', '2025-11-17 10:22:18+01');

-- Insert items into the "order_items" table linking products to orders with quantity, unit price, and subtotal
INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal)
VALUES (1, 1, 1, 2199.0000, 2199.0000),
       (1, 2, 1, 1299.0000, 1299.0000),
       (1, 3, 2, 279.0000, 558.0000),
       (2, 4, 1, 119.9900, 119.9900),
       (2, 5, 1, 649.0000, 649.0000),
       (2, 6, 2, 149.9900, 299.9800),
       (3, 3, 1, 279.0000, 279.0000),
       (4, 4, 1, 119.9900, 119.9900),
       (4, 5, 1, 649.0000, 649.0000);