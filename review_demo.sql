-- DBMS Review-2 SQL demonstration script
-- Run after schema.sql and seed.sql are loaded.
-- SQLite syntax is used because the project backend is SQLite.

-- SELECT: verify seeded table counts.
SELECT 'suppliers' AS table_name, COUNT(*) AS total_rows FROM suppliers
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'warehouses', COUNT(*) FROM warehouses
UNION ALL SELECT 'inventory', COUNT(*) FROM inventory
UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'stock_movements', COUNT(*) FROM stock_movements
UNION ALL SELECT 'reorder_alerts', COUNT(*) FROM reorder_alerts
UNION ALL SELECT 'expiry_alerts', COUNT(*) FROM expiry_alerts;

-- VIEW: frontend exposes this as "Inventory View" in Database Tables.
SELECT product_name, supplier_name, warehouse_name, quantity, stock_state
FROM inventory_overview
ORDER BY stock_state, product_name;

-- INSERT: add a new stock batch. The inventory insert triggers alert checks.
BEGIN TRANSACTION;

INSERT INTO inventory (
    product_id, warehouse_id, quantity, bin_location, bin_status, expiry_date
) VALUES (
    2, 4, 12, 'D2-R4-B08', 'OCCUPIED', date('now', '+10 day')
);

-- UPDATE: adjust stock quantity and show trigger-updated reorder alert behavior.
UPDATE inventory
   SET quantity = 8,
       last_stock_check = CURRENT_TIMESTAMP
 WHERE product_id = 2
   AND warehouse_id = 4
   AND bin_location = 'D2-R4-B08';

SELECT p.product_name, w.warehouse_name, r.current_quantity, r.reorder_level, r.alert_status
FROM reorder_alerts r
JOIN products p ON p.product_id = r.product_id
JOIN warehouses w ON w.warehouse_id = r.warehouse_id
WHERE p.product_id = 2 AND w.warehouse_id = 4;

-- DELETE: remove the demo batch after review.
DELETE FROM inventory
WHERE product_id = 2
  AND warehouse_id = 4
  AND bin_location = 'D2-R4-B08';

-- ALTER: demonstration command for schema modification.
-- Keep this commented during normal app runs to avoid changing the reviewed schema repeatedly.
-- ALTER TABLE warehouses ADD COLUMN audit_note TEXT;

-- TRIGGER: these tables are populated automatically by inventory insert/update triggers.
SELECT * FROM reorder_alerts ORDER BY created_at DESC LIMIT 5;
SELECT * FROM expiry_alerts ORDER BY created_at DESC LIMIT 5;

-- Keep the review database unchanged after this demonstration block.
ROLLBACK;
