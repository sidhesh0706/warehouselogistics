# Smart Warehouse & Inventory Logistics DBMS

This project implements the DBMS Review-1 PPT brief as a working warehouse inventory system. It keeps the PPT entities (`Suppliers`, `Products`, `Warehouses`, `Inventory`, and `Orders`) and adds operational tables for stock movement, reorder alerts, and expiry alerts.

## Requirements Covered

- Track product movement from receiving to shipping across warehouse locations.
- Monitor real-time stock levels from the dashboard.
- Use low-stock reorder triggers in SQLite.
- Generate expiry alerts for perishable goods within 30 days.
- Manage shelf-space through warehouse capacity, bin locations, and bin status.
- Maintain normalized relational tables with primary keys, foreign keys, checks, and indexes.

## Tech Stack

- Front end: HTML, CSS, JavaScript
- Back end: Python standard library HTTP server
- Database: SQLite

## Run

```powershell
python app.py
```

Then open:

```text
http://127.0.0.1:8000
```

If Python is not on PATH, use the bundled runtime from Codex:

```powershell
& 'C:\Users\Sidhesh\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' .\app.py
```

The database file `warehouse_app.db` is created automatically from `schema.sql` and `seed.sql`. The app uses SQLite's in-memory journal mode so it runs cleanly from a OneDrive-backed folder.

## Run From PyCharm

Open this folder in PyCharm:

```text
C:\Users\Sidhesh\OneDrive\Documents\New project 3
```

Then choose the saved run configuration:

```text
Run Smart Warehouse DBMS
```

Start it and open `http://127.0.0.1:8000`.

## Main Tables

- `suppliers`: Supplier contact and address details.
- `products`: SKU, category, price, supplier, reorder level, expiry flag.
- `warehouses`: Location, capacity, manager, and warehouse status.
- `inventory`: Stock quantity by product, warehouse, bin, and expiry date.
- `orders`: Customer shipments with quantity and total amount.
- `stock_movements`: Receiving, shipping, transfer, and adjustment history.
- `reorder_alerts`: Trigger-created low-stock alerts.
- `expiry_alerts`: Trigger-created expiry risk alerts.

## Trigger Logic

- When inventory is inserted or updated, SQLite checks total product quantity in that warehouse against `products.reorder_level`.
- If stock is low, an open `reorder_alerts` row is created or refreshed.
- If stock rises above the reorder level, the open alert is resolved.
- If an inventory row has an expiry date within 30 days, an `expiry_alerts` row is created.
