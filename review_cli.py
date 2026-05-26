import sqlite3
import sys
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "warehouse_app.db"


TABLE_COMMANDS = {
    "suppliers": (
        "Suppliers Table",
        """
        SELECT supplier_id, supplier_name, contact_person, phone, email, address
        FROM suppliers
        ORDER BY supplier_id
        """,
    ),
    "products": (
        "Products Table",
        """
        SELECT p.product_id, p.product_name, p.sku, p.category, p.unit_price,
               p.reorder_level, p.expiry_required, s.supplier_name
        FROM products p
        JOIN suppliers s ON s.supplier_id = p.supplier_id
        ORDER BY p.product_id
        """,
    ),
    "warehouses": (
        "Warehouses Table",
        """
        SELECT warehouse_id, warehouse_name, location, city, capacity, manager, status
        FROM warehouses
        ORDER BY warehouse_id
        """,
    ),
    "inventory": (
        "Inventory Table",
        """
        SELECT i.stock_id, p.product_name, p.sku, w.warehouse_name,
               i.quantity, i.bin_location, i.bin_status, i.expiry_date
        FROM inventory i
        JOIN products p ON p.product_id = i.product_id
        JOIN warehouses w ON w.warehouse_id = i.warehouse_id
        ORDER BY i.stock_id
        """,
    ),
    "orders": (
        "Orders Table",
        """
        SELECT o.order_id, p.product_name, w.warehouse_name, o.customer_name,
               o.order_status, o.quantity_ordered, o.total_amount
        FROM orders o
        JOIN products p ON p.product_id = o.product_id
        JOIN warehouses w ON w.warehouse_id = o.warehouse_id
        ORDER BY o.order_id
        """,
    ),
    "movements": (
        "Stock Movements Table",
        """
        SELECT m.movement_id, p.product_name, m.movement_type, m.quantity,
               sw.warehouse_name AS source_warehouse,
               dw.warehouse_name AS destination_warehouse,
               m.reference_note
        FROM stock_movements m
        JOIN products p ON p.product_id = m.product_id
        LEFT JOIN warehouses sw ON sw.warehouse_id = m.source_warehouse_id
        LEFT JOIN warehouses dw ON dw.warehouse_id = m.destination_warehouse_id
        ORDER BY m.movement_id
        """,
    ),
    "reorder-alerts": (
        "Reorder Alerts Table",
        """
        SELECT r.alert_id, p.product_name, w.warehouse_name,
               r.current_quantity, r.reorder_level, r.alert_status
        FROM reorder_alerts r
        JOIN products p ON p.product_id = r.product_id
        JOIN warehouses w ON w.warehouse_id = r.warehouse_id
        ORDER BY r.alert_id
        """,
    ),
    "expiry-alerts": (
        "Expiry Alerts Table",
        """
        SELECT e.alert_id, p.product_name, w.warehouse_name,
               e.expiry_date, e.days_to_expiry, e.alert_status
        FROM expiry_alerts e
        JOIN products p ON p.product_id = e.product_id
        JOIN warehouses w ON w.warehouse_id = e.warehouse_id
        ORDER BY e.alert_id
        """,
    ),
}


def rows(sql, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def print_table(title, data):
    print(f"\n{title}")
    print("=" * len(title))
    if not data:
        print("No rows found.")
        return

    headers = list(data[0].keys())
    widths = {
        header: max(len(header), *(len(str(row.get(header, ""))) for row in data))
        for header in headers
    }
    line = "+-" + "-+-".join("-" * widths[header] for header in headers) + "-+"
    header_line = "| " + " | ".join(header.ljust(widths[header]) for header in headers) + " |"

    print(line)
    print(header_line)
    print(line)
    for row in data:
        print("| " + " | ".join(str(row.get(header, "")).ljust(widths[header]) for header in headers) + " |")
    print(line)


def show_triggers():
    print_table(
        "Database Row Triggers",
        rows(
            """
            SELECT name AS trigger_name,
                   tbl_name AS table_name,
                   CASE
                       WHEN sql LIKE '%AFTER INSERT%' THEN 'AFTER INSERT'
                       WHEN sql LIKE '%AFTER UPDATE%' THEN 'AFTER UPDATE'
                       ELSE 'TRIGGER'
                   END AS trigger_event
            FROM sqlite_master
            WHERE type = 'trigger'
            ORDER BY name
            """
        ),
    )


def show_alerts():
    print_table(
        "Trigger Output: Reorder Alerts",
        rows(
            """
            SELECT r.alert_id,
                   p.product_name,
                   w.warehouse_name,
                   r.current_quantity,
                   r.reorder_level,
                   r.alert_status
            FROM reorder_alerts r
            JOIN products p ON p.product_id = r.product_id
            JOIN warehouses w ON w.warehouse_id = r.warehouse_id
            ORDER BY r.alert_id DESC
            LIMIT 10
            """
        ),
    )
    print_table(
        "Trigger Output: Expiry Alerts",
        rows(
            """
            SELECT e.alert_id,
                   p.product_name,
                   w.warehouse_name,
                   e.expiry_date,
                   e.days_to_expiry,
                   e.alert_status
            FROM expiry_alerts e
            JOIN products p ON p.product_id = e.product_id
            JOIN warehouses w ON w.warehouse_id = e.warehouse_id
            ORDER BY e.alert_id DESC
            LIMIT 10
            """
        ),
    )


def run_trigger_demo():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO inventory (
                product_id, warehouse_id, quantity, bin_location, bin_status, expiry_date
            )
            VALUES (1, 1, 5, 'TRIGGER-DEMO-BIN', 'OCCUPIED', date('now', '+10 day'))
            ON CONFLICT(product_id, warehouse_id, bin_location) DO UPDATE SET
                quantity = 5,
                expiry_date = date('now', '+10 day'),
                bin_status = 'OCCUPIED',
                last_stock_check = CURRENT_TIMESTAMP
            """
        )
    print("Inserted/updated one inventory row. Alerts below are generated by row triggers.")
    show_alerts()


def show_actions():
    print_table(
        "Procedure-Style Actions / Audit Log",
        rows(
            """
            SELECT log_id,
                   action_type,
                   entity_name,
                   entity_id,
                   summary,
                   created_at
            FROM action_logs
            ORDER BY log_id DESC
            LIMIT 12
            """
        ),
    )


def show_named_table(command):
    title, sql = TABLE_COMMANDS[command]
    print_table(title, rows(sql))


def search_products(term):
    like = f"%{term}%"
    print_table(
        f"Find Products Matching: {term}",
        rows(
            """
            SELECT p.product_id, p.product_name, p.sku, p.category,
                   s.supplier_name, COALESCE(SUM(i.quantity), 0) AS total_quantity
            FROM products p
            JOIN suppliers s ON s.supplier_id = p.supplier_id
            LEFT JOIN inventory i ON i.product_id = p.product_id
            WHERE p.product_name LIKE ?
               OR p.sku LIKE ?
               OR p.category LIKE ?
               OR s.supplier_name LIKE ?
            GROUP BY p.product_id, p.product_name, p.sku, p.category, s.supplier_name
            ORDER BY p.product_name
            """,
            (like, like, like, like),
        ),
    )


def filter_products_by_quantity(min_quantity, max_quantity):
    print_table(
        f"Products With Quantity Between {min_quantity} And {max_quantity}",
        rows(
            """
            SELECT p.product_id, p.product_name, p.sku,
                   COALESCE(SUM(i.quantity), 0) AS total_quantity
            FROM products p
            LEFT JOIN inventory i ON i.product_id = p.product_id
            GROUP BY p.product_id, p.product_name, p.sku
            HAVING total_quantity BETWEEN ? AND ?
            ORDER BY total_quantity
            """,
            (min_quantity, max_quantity),
        ),
    )


def show_help():
    print(
        """
Usage:
  py -3.12 review_cli.py suppliers
  py -3.12 review_cli.py products
  py -3.12 review_cli.py warehouses
  py -3.12 review_cli.py inventory
  py -3.12 review_cli.py orders
  py -3.12 review_cli.py movements
  py -3.12 review_cli.py reorder-alerts
  py -3.12 review_cli.py expiry-alerts
  py -3.12 review_cli.py search <name-or-sku>
  py -3.12 review_cli.py quantity <min> <max>
  py -3.12 review_cli.py triggers
  py -3.12 review_cli.py demo-trigger
  py -3.12 review_cli.py alerts
  py -3.12 review_cli.py actions
"""
    )


def main():
    command = sys.argv[1].lower() if len(sys.argv) > 1 else "help"
    if command == "triggers":
        show_triggers()
    elif command == "demo-trigger":
        run_trigger_demo()
    elif command == "alerts":
        show_alerts()
    elif command == "actions":
        show_actions()
    elif command in TABLE_COMMANDS:
        show_named_table(command)
    elif command == "search" and len(sys.argv) > 2:
        search_products(" ".join(sys.argv[2:]))
    elif command == "quantity" and len(sys.argv) == 4:
        try:
            filter_products_by_quantity(int(sys.argv[2]), int(sys.argv[3]))
        except ValueError:
            print("Quantity filters must be numbers.")
    else:
        show_help()


if __name__ == "__main__":
    main()
