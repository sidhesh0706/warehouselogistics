INSERT INTO suppliers (supplier_name, contact_person, phone, email, address) VALUES
('MedFresh Supply Co.', 'Anita Rao', '+91-98765-10001', 'orders@medfresh.example', 'Peenya Industrial Area, Bengaluru'),
('UrbanPack Distributors', 'Karan Mehta', '+91-98765-10002', 'sales@urbanpack.example', 'Bhiwandi Logistics Park, Mumbai'),
('ColdChain Foods', 'Nisha Iyer', '+91-98765-10003', 'support@coldchain.example', 'Kochi Food Terminal, Kerala'),
('RetailTech Components', 'Arjun Kapoor', '+91-98765-10004', 'dispatch@retailtech.example', 'Okhla Industrial Estate, Delhi'),
('GreenCare Essentials', 'Fatima Khan', '+91-98765-10005', 'supply@greencare.example', 'GIDC Industrial Estate, Ahmedabad');

INSERT INTO products (
    supplier_id, product_name, sku, category, unit_price, reorder_level, expiry_required
) VALUES
(1, 'Paracetamol 500mg Carton', 'MED-PARA-500', 'Medicine', 760.00, 40, 1),
(1, 'Antiseptic Solution Case', 'MED-ANTI-CASE', 'Medicine', 1180.00, 25, 1),
(2, 'Corrugated Shipping Box', 'PKG-BOX-12X10', 'Packaging', 24.00, 200, 0),
(2, 'Thermal Label Roll', 'PKG-LABEL-THERM', 'Packaging', 310.00, 60, 0),
(3, 'Insulated Dairy Crate', 'FOOD-DAIRY-CRATE', 'Food', 1450.00, 30, 1),
(3, 'Frozen Vegetable Pack', 'FOOD-FROZ-VEG', 'Food', 95.00, 120, 1),
(4, 'Barcode Scanner Handheld', 'TECH-SCAN-HH', 'Equipment', 4200.00, 50, 0),
(5, 'Sanitizer Refill Drum', 'CARE-SAN-DRUM', 'Hygiene', 1320.00, 80, 1);

INSERT INTO warehouses (warehouse_name, location, city, capacity, manager, status) VALUES
('North Fulfilment Hub', 'Yelahanka', 'Bengaluru', 1600, 'Meera Nair', 'ACTIVE'),
('West Cross-Dock', 'Bhiwandi', 'Mumbai', 2200, 'Rohit Sharma', 'ACTIVE'),
('South Cold Store', 'Edappally', 'Kochi', 1200, 'Divya Menon', 'ACTIVE'),
('Capital Distribution Node', 'Dwarka', 'Delhi', 1800, 'Sanjay Batra', 'ACTIVE'),
('Gujarat Reserve Depot', 'Naroda', 'Ahmedabad', 1500, 'Priya Desai', 'ACTIVE');

INSERT INTO inventory (
    product_id, warehouse_id, quantity, bin_location, bin_status, expiry_date
) VALUES
(1, 1, 38, 'A1-R1-B02', 'OCCUPIED', date('now', '+22 day')),
(1, 2, 90, 'M1-R3-B04', 'OCCUPIED', date('now', '+75 day')),
(2, 1, 20, 'A2-R4-B01', 'OCCUPIED', date('now', '+18 day')),
(3, 1, 430, 'P1-R1-B09', 'OCCUPIED', NULL),
(3, 2, 160, 'M2-R5-B03', 'OCCUPIED', NULL),
(4, 2, 58, 'M3-R2-B06', 'OCCUPIED', NULL),
(5, 3, 24, 'C1-R2-B01', 'OCCUPIED', date('now', '+12 day')),
(6, 3, 100, 'C2-R1-B07', 'OCCUPIED', date('now', '+26 day')),
(7, 4, 15, 'D1-R2-B04', 'OCCUPIED', date('now', '+20 day')),
(8, 5, 45, 'G1-R1-B05', 'OCCUPIED', date('now', '+15 day'));

INSERT INTO orders (
    product_id, warehouse_id, customer_name, order_status, quantity_ordered, total_amount
) VALUES
(1, 1, 'CityCare Pharmacy', 'SHIPPED', 12, 9120.00),
(3, 2, 'QuickShip Packaging', 'SHIPPED', 40, 960.00),
(5, 3, 'FreshMart Kochi', 'PACKED', 6, 8700.00),
(7, 4, 'North Retail Systems', 'PENDING', 3, 12600.00),
(8, 5, 'CleanPlus Stores', 'SHIPPED', 10, 13200.00);

INSERT INTO stock_movements (
    product_id, source_warehouse_id, destination_warehouse_id, movement_type, quantity, reference_note
) VALUES
(1, NULL, 1, 'RECEIVING', 50, 'Initial supplier receipt'),
(3, NULL, 1, 'RECEIVING', 470, 'Initial supplier receipt'),
(5, NULL, 3, 'RECEIVING', 30, 'Cold storage batch'),
(4, NULL, 2, 'RECEIVING', 58, 'Label restock'),
(7, NULL, 4, 'RECEIVING', 18, 'Scanner inbound lot'),
(1, 1, NULL, 'SHIPPING', 12, 'Order #1 for CityCare Pharmacy'),
(3, 2, NULL, 'SHIPPING', 40, 'Order #2 for QuickShip Packaging'),
(5, 3, NULL, 'SHIPPING', 6, 'Order #3 for FreshMart Kochi'),
(7, 4, NULL, 'SHIPPING', 3, 'Order #4 for North Retail Systems'),
(8, 5, NULL, 'SHIPPING', 10, 'Order #5 for CleanPlus Stores');

INSERT INTO action_logs (
    related_product_id, action_type, entity_name, entity_id, summary, details
) VALUES
(1, 'INSERT', 'inventory', 1, 'Seeded receiving stock for Paracetamol 500mg Carton.', '{"quantity": 50, "warehouse_id": 1}'),
(3, 'INSERT', 'orders', 2, 'Seeded shipment for Corrugated Shipping Box.', '{"quantity": 40, "warehouse_id": 2}'),
(5, 'UPDATE', 'inventory', 5, 'Seeded cold-chain stock movement for Insulated Dairy Crate.', '{"quantity": 30, "warehouse_id": 3}'),
(7, 'INSERT', 'products', 7, 'Seeded equipment SKU Barcode Scanner Handheld.', '{"category": "Equipment", "reorder_level": 50}'),
(8, 'INSERT', 'orders', 5, 'Seeded shipment for Sanitizer Refill Drum.', '{"quantity": 10, "warehouse_id": 5}');
