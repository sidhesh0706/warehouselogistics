INSERT INTO suppliers (supplier_name, contact_person, phone, email, address) VALUES
('MedFresh Supply Co.', 'Anita Rao', '+91-98765-10001', 'orders@medfresh.example', 'Peenya Industrial Area, Bengaluru'),
('UrbanPack Distributors', 'Karan Mehta', '+91-98765-10002', 'sales@urbanpack.example', 'Bhiwandi Logistics Park, Mumbai'),
('ColdChain Foods', 'Nisha Iyer', '+91-98765-10003', 'support@coldchain.example', 'Kochi Food Terminal, Kerala');

INSERT INTO products (
    supplier_id, product_name, sku, category, unit_price, reorder_level, expiry_required
) VALUES
(1, 'Paracetamol 500mg Carton', 'MED-PARA-500', 'Medicine', 760.00, 40, 1),
(1, 'Antiseptic Solution Case', 'MED-ANTI-CASE', 'Medicine', 1180.00, 25, 1),
(2, 'Corrugated Shipping Box', 'PKG-BOX-12X10', 'Packaging', 24.00, 200, 0),
(2, 'Thermal Label Roll', 'PKG-LABEL-THERM', 'Packaging', 310.00, 60, 0),
(3, 'Insulated Dairy Crate', 'FOOD-DAIRY-CRATE', 'Food', 1450.00, 30, 1),
(3, 'Frozen Vegetable Pack', 'FOOD-FROZ-VEG', 'Food', 95.00, 120, 1);

INSERT INTO warehouses (warehouse_name, location, city, capacity, manager, status) VALUES
('North Fulfilment Hub', 'Yelahanka', 'Bengaluru', 1600, 'Meera Nair', 'ACTIVE'),
('West Cross-Dock', 'Bhiwandi', 'Mumbai', 2200, 'Rohit Sharma', 'ACTIVE'),
('South Cold Store', 'Edappally', 'Kochi', 1200, 'Divya Menon', 'ACTIVE');

INSERT INTO inventory (
    product_id, warehouse_id, quantity, bin_location, bin_status, expiry_date
) VALUES
(1, 1, 38, 'A1-R1-B02', 'OCCUPIED', date('now', '+22 day')),
(1, 2, 90, 'M1-R3-B04', 'OCCUPIED', date('now', '+75 day')),
(2, 1, 32, 'A2-R4-B01', 'OCCUPIED', date('now', '+18 day')),
(3, 1, 430, 'P1-R1-B09', 'OCCUPIED', NULL),
(3, 2, 160, 'M2-R5-B03', 'OCCUPIED', NULL),
(4, 2, 58, 'M3-R2-B06', 'OCCUPIED', NULL),
(5, 3, 24, 'C1-R2-B01', 'OCCUPIED', date('now', '+12 day')),
(6, 3, 140, 'C2-R1-B07', 'OCCUPIED', date('now', '+40 day'));

INSERT INTO stock_movements (
    product_id, source_warehouse_id, destination_warehouse_id, movement_type, quantity, reference_note
) VALUES
(1, NULL, 1, 'RECEIVING', 38, 'Initial supplier receipt'),
(3, NULL, 1, 'RECEIVING', 430, 'Initial supplier receipt'),
(5, NULL, 3, 'RECEIVING', 24, 'Cold storage batch'),
(4, NULL, 2, 'RECEIVING', 58, 'Label restock');
