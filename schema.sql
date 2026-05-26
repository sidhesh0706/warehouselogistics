PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_name TEXT NOT NULL,
    contact_person TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    address TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    sku TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    unit_price REAL NOT NULL CHECK (unit_price >= 0),
    reorder_level INTEGER NOT NULL DEFAULT 25 CHECK (reorder_level >= 0),
    expiry_required INTEGER NOT NULL DEFAULT 0 CHECK (expiry_required IN (0, 1)),
    FOREIGN KEY (supplier_id) REFERENCES suppliers (supplier_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS warehouses (
    warehouse_id INTEGER PRIMARY KEY AUTOINCREMENT,
    warehouse_name TEXT NOT NULL,
    location TEXT NOT NULL,
    city TEXT NOT NULL,
    capacity INTEGER NOT NULL CHECK (capacity > 0),
    manager TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE', 'MAINTENANCE', 'INACTIVE'))
);

CREATE TABLE IF NOT EXISTS inventory (
    stock_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    warehouse_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity >= 0),
    bin_location TEXT NOT NULL,
    bin_status TEXT NOT NULL DEFAULT 'OCCUPIED'
        CHECK (bin_status IN ('EMPTY', 'OCCUPIED', 'RESERVED', 'DAMAGED')),
    expiry_date TEXT,
    last_stock_check TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (product_id, warehouse_id, bin_location),
    FOREIGN KEY (product_id) REFERENCES products (product_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (warehouse_id) REFERENCES warehouses (warehouse_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    warehouse_id INTEGER NOT NULL,
    customer_name TEXT NOT NULL,
    order_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    order_status TEXT NOT NULL DEFAULT 'SHIPPED'
        CHECK (order_status IN ('PENDING', 'PACKED', 'SHIPPED', 'CANCELLED')),
    quantity_ordered INTEGER NOT NULL CHECK (quantity_ordered > 0),
    total_amount REAL NOT NULL CHECK (total_amount >= 0),
    FOREIGN KEY (product_id) REFERENCES products (product_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (warehouse_id) REFERENCES warehouses (warehouse_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS stock_movements (
    movement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    source_warehouse_id INTEGER,
    destination_warehouse_id INTEGER,
    movement_type TEXT NOT NULL
        CHECK (movement_type IN ('RECEIVING', 'SHIPPING', 'TRANSFER', 'ADJUSTMENT')),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    movement_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reference_note TEXT,
    FOREIGN KEY (product_id) REFERENCES products (product_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (source_warehouse_id) REFERENCES warehouses (warehouse_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (destination_warehouse_id) REFERENCES warehouses (warehouse_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS reorder_alerts (
    alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    warehouse_id INTEGER NOT NULL,
    current_quantity INTEGER NOT NULL,
    reorder_level INTEGER NOT NULL,
    alert_status TEXT NOT NULL DEFAULT 'OPEN'
        CHECK (alert_status IN ('OPEN', 'RESOLVED')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TEXT,
    FOREIGN KEY (product_id) REFERENCES products (product_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (warehouse_id) REFERENCES warehouses (warehouse_id)
        ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS expiry_alerts (
    alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    warehouse_id INTEGER NOT NULL,
    expiry_date TEXT NOT NULL,
    days_to_expiry INTEGER NOT NULL,
    alert_status TEXT NOT NULL DEFAULT 'OPEN'
        CHECK (alert_status IN ('OPEN', 'RESOLVED')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TEXT,
    FOREIGN KEY (stock_id) REFERENCES inventory (stock_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products (product_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    FOREIGN KEY (warehouse_id) REFERENCES warehouses (warehouse_id)
        ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS action_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    related_product_id INTEGER,
    action_type TEXT NOT NULL,
    entity_name TEXT NOT NULL,
    entity_id INTEGER,
    summary TEXT NOT NULL,
    details TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (related_product_id) REFERENCES products (product_id)
        ON UPDATE CASCADE ON DELETE SET NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_open_reorder_alert
ON reorder_alerts (product_id, warehouse_id)
WHERE alert_status = 'OPEN';

CREATE UNIQUE INDEX IF NOT EXISTS idx_open_expiry_alert
ON expiry_alerts (stock_id)
WHERE alert_status = 'OPEN';

CREATE INDEX IF NOT EXISTS idx_inventory_product_warehouse
ON inventory (product_id, warehouse_id);

CREATE INDEX IF NOT EXISTS idx_movements_product_date
ON stock_movements (product_id, movement_date);

CREATE VIEW IF NOT EXISTS inventory_overview AS
SELECT
    i.stock_id,
    p.product_name,
    p.sku,
    p.category,
    s.supplier_name,
    w.warehouse_name,
    w.city,
    i.quantity,
    p.reorder_level,
    i.bin_location,
    i.expiry_date,
    CASE
        WHEN i.quantity <= p.reorder_level THEN 'LOW'
        WHEN i.expiry_date IS NOT NULL AND date(i.expiry_date) <= date('now', '+30 day') THEN 'EXPIRING'
        ELSE 'OK'
    END AS stock_state
FROM inventory i
JOIN products p ON p.product_id = i.product_id
JOIN suppliers s ON s.supplier_id = p.supplier_id
JOIN warehouses w ON w.warehouse_id = i.warehouse_id;

CREATE TRIGGER IF NOT EXISTS trg_inventory_low_stock_insert
AFTER INSERT ON inventory
BEGIN
    UPDATE reorder_alerts
       SET current_quantity = (
               SELECT COALESCE(SUM(quantity), 0)
               FROM inventory
               WHERE product_id = NEW.product_id AND warehouse_id = NEW.warehouse_id
           ),
           reorder_level = (SELECT reorder_level FROM products WHERE product_id = NEW.product_id)
     WHERE product_id = NEW.product_id
       AND warehouse_id = NEW.warehouse_id
       AND alert_status = 'OPEN';

    INSERT OR IGNORE INTO reorder_alerts (product_id, warehouse_id, current_quantity, reorder_level)
    SELECT NEW.product_id,
           NEW.warehouse_id,
           COALESCE(SUM(quantity), 0),
           (SELECT reorder_level FROM products WHERE product_id = NEW.product_id)
      FROM inventory
     WHERE product_id = NEW.product_id
       AND warehouse_id = NEW.warehouse_id
    HAVING COALESCE(SUM(quantity), 0) <= (SELECT reorder_level FROM products WHERE product_id = NEW.product_id);

    UPDATE reorder_alerts
       SET alert_status = 'RESOLVED',
           resolved_at = CURRENT_TIMESTAMP
     WHERE product_id = NEW.product_id
       AND warehouse_id = NEW.warehouse_id
       AND alert_status = 'OPEN'
       AND (
           SELECT COALESCE(SUM(quantity), 0)
           FROM inventory
           WHERE product_id = NEW.product_id AND warehouse_id = NEW.warehouse_id
       ) > (SELECT reorder_level FROM products WHERE product_id = NEW.product_id);
END;

CREATE TRIGGER IF NOT EXISTS trg_inventory_low_stock_update
AFTER UPDATE OF quantity ON inventory
BEGIN
    UPDATE reorder_alerts
       SET current_quantity = (
               SELECT COALESCE(SUM(quantity), 0)
               FROM inventory
               WHERE product_id = NEW.product_id AND warehouse_id = NEW.warehouse_id
           ),
           reorder_level = (SELECT reorder_level FROM products WHERE product_id = NEW.product_id)
     WHERE product_id = NEW.product_id
       AND warehouse_id = NEW.warehouse_id
       AND alert_status = 'OPEN';

    INSERT OR IGNORE INTO reorder_alerts (product_id, warehouse_id, current_quantity, reorder_level)
    SELECT NEW.product_id,
           NEW.warehouse_id,
           COALESCE(SUM(quantity), 0),
           (SELECT reorder_level FROM products WHERE product_id = NEW.product_id)
      FROM inventory
     WHERE product_id = NEW.product_id
       AND warehouse_id = NEW.warehouse_id
    HAVING COALESCE(SUM(quantity), 0) <= (SELECT reorder_level FROM products WHERE product_id = NEW.product_id);

    UPDATE reorder_alerts
       SET alert_status = 'RESOLVED',
           resolved_at = CURRENT_TIMESTAMP
     WHERE product_id = NEW.product_id
       AND warehouse_id = NEW.warehouse_id
       AND alert_status = 'OPEN'
       AND (
           SELECT COALESCE(SUM(quantity), 0)
           FROM inventory
           WHERE product_id = NEW.product_id AND warehouse_id = NEW.warehouse_id
       ) > (SELECT reorder_level FROM products WHERE product_id = NEW.product_id);
END;

CREATE TRIGGER IF NOT EXISTS trg_inventory_expiry_insert
AFTER INSERT ON inventory
WHEN NEW.expiry_date IS NOT NULL
 AND NEW.quantity > 0
 AND date(NEW.expiry_date) <= date('now', '+30 day')
BEGIN
    INSERT OR IGNORE INTO expiry_alerts (
        stock_id, product_id, warehouse_id, expiry_date, days_to_expiry
    )
    VALUES (
        NEW.stock_id,
        NEW.product_id,
        NEW.warehouse_id,
        NEW.expiry_date,
        CAST(julianday(NEW.expiry_date) - julianday(date('now')) AS INTEGER)
    );
END;

CREATE TRIGGER IF NOT EXISTS trg_inventory_expiry_update
AFTER UPDATE OF expiry_date, quantity ON inventory
BEGIN
    UPDATE expiry_alerts
       SET alert_status = 'RESOLVED',
           resolved_at = CURRENT_TIMESTAMP
     WHERE stock_id = NEW.stock_id
       AND alert_status = 'OPEN'
       AND (
           NEW.expiry_date IS NULL
           OR NEW.quantity <= 0
           OR date(NEW.expiry_date) > date('now', '+30 day')
       );

    INSERT OR IGNORE INTO expiry_alerts (
        stock_id, product_id, warehouse_id, expiry_date, days_to_expiry
    )
    SELECT NEW.stock_id,
           NEW.product_id,
           NEW.warehouse_id,
           NEW.expiry_date,
           CAST(julianday(NEW.expiry_date) - julianday(date('now')) AS INTEGER)
     WHERE NEW.expiry_date IS NOT NULL
       AND NEW.quantity > 0
       AND date(NEW.expiry_date) <= date('now', '+30 day');
END;
