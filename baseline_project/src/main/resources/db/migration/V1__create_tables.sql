-- Users table: stores application users, their credentials, and account metadata
CREATE TABLE users
(
    id            BIGSERIAL PRIMARY KEY,
    username      VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    email         VARCHAR(255) NOT NULL UNIQUE CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    is_admin      BOOLEAN      NOT NULL DEFAULT false,
    deleted       TIMESTAMPTZ,
    created       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated       TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Products table: stores products available for sale, including stock and pricing
CREATE TABLE products
(
    product_id  BIGSERIAL PRIMARY KEY,
    title       VARCHAR(255)   NOT NULL,
    description TEXT,
    price       NUMERIC(12, 4) NOT NULL CHECK (price >= 0),
    stock       INTEGER        NOT NULL DEFAULT 0 CHECK (stock >= 0),
    created     TIMESTAMPTZ    NOT NULL DEFAULT now(),
    updated     TIMESTAMPTZ    NOT NULL DEFAULT now()
);

-- Orders table: stores customer orders, their status, and total amounts
CREATE TABLE orders
(
    order_id     BIGSERIAL PRIMARY KEY,
    user_id      BIGINT         NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
    order_number VARCHAR(50)    NOT NULL UNIQUE,
    order_status VARCHAR(20)    NOT NULL DEFAULT 'PENDING'
        CHECK (order_status IN (
                                'PENDING', 'CONFIRMED', 'PAID', 'PROCESSING',
                                'SHIPPED', 'COMPLETED', 'CANCELLED', 'REFUNDED'
            )),
    total_amount NUMERIC(14, 4) NOT NULL CHECK (total_amount >= 0),
    created      TIMESTAMPTZ    NOT NULL DEFAULT now(),
    updated      TIMESTAMPTZ    NOT NULL DEFAULT now()
);

-- Order_items table: stores individual items within an order, their quantity, and pricing
CREATE TABLE order_items
(
    order_item_id BIGSERIAL PRIMARY KEY,
    order_id      BIGINT         NOT NULL REFERENCES orders (order_id) ON DELETE CASCADE,
    product_id    BIGINT         NOT NULL REFERENCES products (product_id) ON DELETE RESTRICT,
    quantity      INTEGER        NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit_price    NUMERIC(12, 4) NOT NULL CHECK (unit_price >= 0),
    subtotal      NUMERIC(14, 4) NOT NULL,

    CONSTRAINT unique_order_product UNIQUE (order_id, product_id)
);

-- Function to automatically update the "updated" timestamp on row updates
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
    RETURNS TRIGGER AS
$$
BEGIN
    NEW.updated = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers to automatically set updated timestamp for each table
CREATE TRIGGER trg_users_updated
    BEFORE UPDATE
    ON users
    FOR EACH ROW
EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER trg_products_updated
    BEFORE UPDATE
    ON products
    FOR EACH ROW
EXECUTE FUNCTION trigger_set_updated_at();

CREATE TRIGGER trg_orders_updated
    BEFORE UPDATE
    ON orders
    FOR EACH ROW
EXECUTE FUNCTION trigger_set_updated_at();

-- Indexes to improve query performance on orders and order_items
CREATE INDEX idx_orders_user_id ON orders (user_id);
CREATE INDEX idx_orders_status ON orders (order_status);
CREATE INDEX idx_orders_created_at ON orders (created DESC);
CREATE INDEX idx_orders_number ON orders (order_number);
CREATE INDEX idx_order_items_order_id ON order_items (order_id);
CREATE INDEX idx_order_items_product_id ON order_items (product_id);