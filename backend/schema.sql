CREATE TABLE IF NOT EXISTS stores (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT NOT NULL DEFAULT '',
    district TEXT NOT NULL DEFAULT '',
    address TEXT NOT NULL,
    phone TEXT NOT NULL DEFAULT '',
    hours TEXT NOT NULL DEFAULT '',
    services TEXT NOT NULL DEFAULT '',
    maps_url TEXT NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    keywords TEXT NOT NULL DEFAULT '',
    aisle TEXT NOT NULL DEFAULT '',
    price_twd INTEGER NOT NULL CHECK (price_twd >= 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS inventory (
    store_id TEXT NOT NULL REFERENCES stores(id),
    product_id TEXT NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (store_id, product_id)
);

CREATE TABLE IF NOT EXISTS members (
    google_sub TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    shopping_credit_twd INTEGER NOT NULL DEFAULT 0 CHECK (shopping_credit_twd >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS member_coupons (
    id BIGSERIAL PRIMARY KEY,
    google_sub TEXT NOT NULL REFERENCES members(google_sub),
    coupon_code TEXT NOT NULL,
    title TEXT NOT NULL,
    discount_twd INTEGER NOT NULL CHECK (discount_twd >= 0),
    min_spend_twd INTEGER NOT NULL DEFAULT 0 CHECK (min_spend_twd >= 0),
    is_used BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMPTZ,
    UNIQUE (google_sub, coupon_code)
);

CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY,
    order_code TEXT NOT NULL UNIQUE,
    google_sub TEXT NOT NULL REFERENCES members(google_sub),
    store_id TEXT NOT NULL REFERENCES stores(id),
    payment_method TEXT NOT NULL,
    payment_status TEXT NOT NULL,
    fulfillment_status TEXT NOT NULL DEFAULT 'pending_pickup',
    contact_name TEXT NOT NULL DEFAULT '',
    contact_phone TEXT NOT NULL,
    subtotal_twd INTEGER NOT NULL,
    discount_twd INTEGER NOT NULL DEFAULT 0,
    credit_used_twd INTEGER NOT NULL DEFAULT 0,
    total_twd INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS order_items (
    id BIGSERIAL PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id TEXT NOT NULL REFERENCES products(id),
    product_name TEXT NOT NULL,
    unit_price_twd INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0)
);

CREATE INDEX IF NOT EXISTS idx_orders_member_created ON orders(google_sub, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_inventory_product ON inventory(product_id);
