from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import json
import mimetypes
import os
import sqlite3


ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "warehouse_app.db"
STATIC_DIR = ROOT / "static"


TABLE_QUERIES = {
    "suppliers": """
        SELECT supplier_id, supplier_name, contact_person, phone, email, address
        FROM suppliers
        ORDER BY supplier_name
    """,
    "products": """
        SELECT p.product_id, p.product_name, p.sku, p.category, p.unit_price,
               p.reorder_level, p.expiry_required, s.supplier_name
        FROM products p
        JOIN suppliers s ON s.supplier_id = p.supplier_id
        ORDER BY p.product_name
    """,
    "warehouses": """
        SELECT warehouse_id, warehouse_name, location, city, capacity, manager, status
        FROM warehouses
        ORDER BY warehouse_name
    """,
    "inventory": """
        SELECT i.stock_id, p.product_name, p.sku, w.warehouse_name, w.city,
               i.quantity, p.reorder_level, i.bin_location, i.bin_status,
               i.expiry_date, i.last_stock_check
        FROM inventory i
        JOIN products p ON p.product_id = i.product_id
        JOIN warehouses w ON w.warehouse_id = i.warehouse_id
        ORDER BY w.warehouse_name, p.product_name, i.bin_location
    """,
    "orders": """
        SELECT o.order_id, p.product_name, w.warehouse_name, o.customer_name,
               o.order_date, o.order_status, o.quantity_ordered, o.total_amount
        FROM orders o
        JOIN products p ON p.product_id = o.product_id
        JOIN warehouses w ON w.warehouse_id = o.warehouse_id
        ORDER BY o.order_date DESC, o.order_id DESC
        LIMIT 50
    """,
    "movements": """
        SELECT m.movement_id, p.product_name, m.movement_type, m.quantity,
               sw.warehouse_name AS source_warehouse,
               dw.warehouse_name AS destination_warehouse,
               m.movement_date, m.reference_note
        FROM stock_movements m
        JOIN products p ON p.product_id = m.product_id
        LEFT JOIN warehouses sw ON sw.warehouse_id = m.source_warehouse_id
        LEFT JOIN warehouses dw ON dw.warehouse_id = m.destination_warehouse_id
        ORDER BY m.movement_date DESC, m.movement_id DESC
        LIMIT 50
    """,
}

OPERATIONAL_TABLES = ("orders", "stock_movements", "expiry_alerts", "reorder_alerts", "inventory")
MASTER_TABLES = ("products", "warehouses", "suppliers")


class ManagedConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if exc_type is None:
                self.commit()
            else:
                self.rollback()
        finally:
            self.close()
        return False


def connect():
    conn = sqlite3.connect(DB_PATH, factory=ManagedConnection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = MEMORY")
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with connect() as conn:
        conn.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
        supplier_count = conn.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0]
        if supplier_count == 0:
            conn.executescript((ROOT / "seed.sql").read_text(encoding="utf-8"))


def reset_sequences(conn, tables):
    placeholders = ",".join("?" for _ in tables)
    conn.execute(f"DELETE FROM sqlite_sequence WHERE name IN ({placeholders})", tables)


def clear_operational_data(conn):
    for table in OPERATIONAL_TABLES:
        conn.execute(f"DELETE FROM {table}")
    reset_sequences(conn, OPERATIONAL_TABLES)


def clear_demo_data():
    with connect() as conn:
        clear_operational_data(conn)
        return {
            "message": "Demo inventory, orders, movements, and alerts cleared. Products and warehouses are ready for fresh transactions.",
            "dashboard": dashboard(conn),
        }


def restore_demo_data():
    with connect() as conn:
        clear_operational_data(conn)
        for table in MASTER_TABLES:
            conn.execute(f"DELETE FROM {table}")
        reset_sequences(conn, OPERATIONAL_TABLES + MASTER_TABLES)
        conn.executescript((ROOT / "seed.sql").read_text(encoding="utf-8"))
        return {
            "message": "Demo dataset restored with sample suppliers, products, warehouses, and stock.",
            "dashboard": dashboard(conn),
        }


def rows(conn, sql, params=()):
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def scalar(conn, sql, params=()):
    return conn.execute(sql, params).fetchone()[0]


def current_stock(conn, product_id, warehouse_id):
    return scalar(
        conn,
        """
        SELECT COALESCE(SUM(quantity), 0)
        FROM inventory
        WHERE product_id = ? AND warehouse_id = ?
        """,
        (product_id, warehouse_id),
    )


def decrement_stock(conn, product_id, warehouse_id, quantity):
    available = current_stock(conn, product_id, warehouse_id)
    if available < quantity:
        raise ValueError(f"Only {available} units are available in this warehouse.")

    remaining = quantity
    stock_rows = conn.execute(
        """
        SELECT stock_id, quantity
        FROM inventory
        WHERE product_id = ? AND warehouse_id = ? AND quantity > 0
        ORDER BY expiry_date IS NULL, expiry_date, stock_id
        """,
        (product_id, warehouse_id),
    ).fetchall()

    for stock in stock_rows:
        if remaining <= 0:
            break
        taken = min(stock["quantity"], remaining)
        new_quantity = stock["quantity"] - taken
        new_status = "EMPTY" if new_quantity == 0 else "OCCUPIED"
        conn.execute(
            """
            UPDATE inventory
               SET quantity = ?,
                   bin_status = ?,
                   last_stock_check = CURRENT_TIMESTAMP
             WHERE stock_id = ?
            """,
            (new_quantity, new_status, stock["stock_id"]),
        )
        remaining -= taken


def upsert_stock(conn, product_id, warehouse_id, quantity, bin_location, expiry_date=None):
    conn.execute(
        """
        INSERT INTO inventory (
            product_id, warehouse_id, quantity, bin_location, bin_status,
            expiry_date, last_stock_check
        )
        VALUES (?, ?, ?, ?, 'OCCUPIED', ?, CURRENT_TIMESTAMP)
        ON CONFLICT(product_id, warehouse_id, bin_location) DO UPDATE SET
            quantity = inventory.quantity + excluded.quantity,
            bin_status = 'OCCUPIED',
            expiry_date = COALESCE(excluded.expiry_date, inventory.expiry_date),
            last_stock_check = CURRENT_TIMESTAMP
        """,
        (product_id, warehouse_id, quantity, bin_location, expiry_date),
    )


def dashboard(conn):
    utilization = rows(
        conn,
        """
        SELECT w.warehouse_id, w.warehouse_name, w.capacity,
               COALESCE(SUM(i.quantity), 0) AS units,
               ROUND(COALESCE(SUM(i.quantity), 0) * 100.0 / w.capacity, 1) AS utilization
        FROM warehouses w
        LEFT JOIN inventory i ON i.warehouse_id = w.warehouse_id
        GROUP BY w.warehouse_id
        ORDER BY utilization DESC
        """,
    )

    return {
        "metrics": {
            "products": scalar(conn, "SELECT COUNT(*) FROM products"),
            "warehouses": scalar(conn, "SELECT COUNT(*) FROM warehouses WHERE status = 'ACTIVE'"),
            "total_units": scalar(conn, "SELECT COALESCE(SUM(quantity), 0) FROM inventory"),
            "low_stock": scalar(conn, "SELECT COUNT(*) FROM reorder_alerts WHERE alert_status = 'OPEN'"),
            "expiry_alerts": scalar(conn, "SELECT COUNT(*) FROM expiry_alerts WHERE alert_status = 'OPEN'"),
        },
        "utilization": utilization,
        "stock_watch": rows(
            conn,
            """
            SELECT p.product_name, p.sku, w.warehouse_name, i.quantity,
                   p.reorder_level, i.bin_location, i.expiry_date,
                   CASE
                       WHEN i.quantity <= p.reorder_level THEN 'LOW'
                       WHEN i.expiry_date IS NOT NULL AND date(i.expiry_date) <= date('now', '+30 day') THEN 'EXPIRING'
                       ELSE 'OK'
                   END AS stock_state
            FROM inventory i
            JOIN products p ON p.product_id = i.product_id
            JOIN warehouses w ON w.warehouse_id = i.warehouse_id
            ORDER BY
                CASE stock_state WHEN 'LOW' THEN 1 WHEN 'EXPIRING' THEN 2 ELSE 3 END,
                i.quantity ASC
            LIMIT 12
            """,
        ),
        "alerts": rows(
            conn,
            """
            SELECT 'LOW_STOCK' AS alert_type, p.product_name, w.warehouse_name,
                   r.current_quantity AS value, r.reorder_level AS threshold,
                   r.created_at AS created_at
            FROM reorder_alerts r
            JOIN products p ON p.product_id = r.product_id
            JOIN warehouses w ON w.warehouse_id = r.warehouse_id
            WHERE r.alert_status = 'OPEN'
            UNION ALL
            SELECT 'EXPIRY' AS alert_type, p.product_name, w.warehouse_name,
                   e.days_to_expiry AS value, NULL AS threshold,
                   e.created_at AS created_at
            FROM expiry_alerts e
            JOIN products p ON p.product_id = e.product_id
            JOIN warehouses w ON w.warehouse_id = e.warehouse_id
            WHERE e.alert_status = 'OPEN'
            ORDER BY created_at DESC
            LIMIT 10
            """,
        ),
        "recent_movements": rows(conn, TABLE_QUERIES["movements"].replace("LIMIT 50", "LIMIT 8")),
    }


def require_int(payload, key, minimum=1):
    try:
        value = int(payload.get(key))
    except (TypeError, ValueError):
        raise ValueError(f"{key} must be a number.")
    if value < minimum:
        raise ValueError(f"{key} must be at least {minimum}.")
    return value


def receive_stock(payload):
    product_id = require_int(payload, "product_id")
    warehouse_id = require_int(payload, "warehouse_id")
    quantity = require_int(payload, "quantity")
    bin_location = (payload.get("bin_location") or "").strip().upper()
    expiry_date = (payload.get("expiry_date") or "").strip() or None
    if not bin_location:
        raise ValueError("bin_location is required.")

    with connect() as conn:
        upsert_stock(conn, product_id, warehouse_id, quantity, bin_location, expiry_date)
        conn.execute(
            """
            INSERT INTO stock_movements (
                product_id, source_warehouse_id, destination_warehouse_id,
                movement_type, quantity, reference_note
            )
            VALUES (?, NULL, ?, 'RECEIVING', ?, ?)
            """,
            (product_id, warehouse_id, quantity, payload.get("reference_note") or "Supplier receipt"),
        )
        return {"message": "Stock received and inventory updated.", "dashboard": dashboard(conn)}


def ship_order(payload):
    product_id = require_int(payload, "product_id")
    warehouse_id = require_int(payload, "warehouse_id")
    quantity = require_int(payload, "quantity")
    customer_name = (payload.get("customer_name") or "").strip()
    if not customer_name:
        raise ValueError("customer_name is required.")

    with connect() as conn:
        product = conn.execute(
            "SELECT product_name, unit_price FROM products WHERE product_id = ?",
            (product_id,),
        ).fetchone()
        if not product:
            raise ValueError("Product not found.")
        decrement_stock(conn, product_id, warehouse_id, quantity)
        total = round(product["unit_price"] * quantity, 2)
        cursor = conn.execute(
            """
            INSERT INTO orders (
                product_id, warehouse_id, customer_name, order_status,
                quantity_ordered, total_amount
            )
            VALUES (?, ?, ?, 'SHIPPED', ?, ?)
            """,
            (product_id, warehouse_id, customer_name, quantity, total),
        )
        order_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO stock_movements (
                product_id, source_warehouse_id, destination_warehouse_id,
                movement_type, quantity, reference_note
            )
            VALUES (?, ?, NULL, 'SHIPPING', ?, ?)
            """,
            (product_id, warehouse_id, quantity, f"Order #{order_id} for {customer_name}"),
        )
        return {"message": "Order shipped and stock deducted.", "order_id": order_id, "dashboard": dashboard(conn)}


def transfer_stock(payload):
    product_id = require_int(payload, "product_id")
    source_id = require_int(payload, "source_warehouse_id")
    destination_id = require_int(payload, "destination_warehouse_id")
    quantity = require_int(payload, "quantity")
    bin_location = (payload.get("bin_location") or "").strip().upper()
    if source_id == destination_id:
        raise ValueError("Source and destination warehouses must be different.")
    if not bin_location:
        raise ValueError("bin_location is required for the destination.")

    with connect() as conn:
        decrement_stock(conn, product_id, source_id, quantity)
        upsert_stock(conn, product_id, destination_id, quantity, bin_location)
        conn.execute(
            """
            INSERT INTO stock_movements (
                product_id, source_warehouse_id, destination_warehouse_id,
                movement_type, quantity, reference_note
            )
            VALUES (?, ?, ?, 'TRANSFER', ?, ?)
            """,
            (product_id, source_id, destination_id, quantity, payload.get("reference_note") or "Inter-warehouse transfer"),
        )
        return {"message": "Transfer completed across warehouse locations.", "dashboard": dashboard(conn)}


def remove_order(order_id):
    with connect() as conn:
        order = conn.execute(
            """
            SELECT o.order_id, o.product_id, o.warehouse_id, o.customer_name,
                   o.quantity_ordered, o.order_status, p.product_name
            FROM orders o
            JOIN products p ON p.product_id = o.product_id
            WHERE o.order_id = ?
            """,
            (order_id,),
        ).fetchone()
        if not order:
            raise ValueError("Order not found.")

        upsert_stock(
            conn,
            order["product_id"],
            order["warehouse_id"],
            order["quantity_ordered"],
            "RETURNS",
        )
        conn.execute(
            """
            INSERT INTO stock_movements (
                product_id, source_warehouse_id, destination_warehouse_id,
                movement_type, quantity, reference_note
            )
            VALUES (?, NULL, ?, 'ADJUSTMENT', ?, ?)
            """,
            (
                order["product_id"],
                order["warehouse_id"],
                order["quantity_ordered"],
                f"Removed order #{order_id}; stock restored from {order['customer_name']}",
            ),
        )
        conn.execute("DELETE FROM orders WHERE order_id = ?", (order_id,))
        return {
            "message": f"Order #{order_id} removed and stock restored.",
            "dashboard": dashboard(conn),
        }


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("%s - - %s" % (self.client_address[0], fmt % args))

    def send_json(self, payload, status=200):
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/dashboard":
            with connect() as conn:
                self.send_json(dashboard(conn))
            return
        if path.startswith("/api/table/"):
            table = path.rsplit("/", 1)[-1]
            sql = TABLE_QUERIES.get(table)
            if not sql:
                self.send_json({"error": "Unknown table."}, 404)
                return
            with connect() as conn:
                self.send_json({"rows": rows(conn, sql)})
            return
        if path == "/api/options":
            with connect() as conn:
                self.send_json(
                    {
                        "products": rows(
                            conn,
                            "SELECT product_id, product_name, sku FROM products ORDER BY product_name",
                        ),
                        "warehouses": rows(
                            conn,
                            "SELECT warehouse_id, warehouse_name, city FROM warehouses ORDER BY warehouse_name",
                        ),
                    }
                )
            return
        if path == "/":
            self.serve_file(STATIC_DIR / "index.html")
            return
        self.serve_file(ROOT / path.lstrip("/"))

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            payload = self.read_json()
            if parsed.path == "/api/receive":
                self.send_json(receive_stock(payload))
            elif parsed.path == "/api/ship":
                self.send_json(ship_order(payload))
            elif parsed.path == "/api/transfer":
                self.send_json(transfer_stock(payload))
            elif parsed.path == "/api/demo/clear":
                self.send_json(clear_demo_data())
            elif parsed.path == "/api/demo/restore":
                self.send_json(restore_demo_data())
            else:
                self.send_json({"error": "Unknown endpoint."}, 404)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, 400)
        except sqlite3.IntegrityError as exc:
            self.send_json({"error": f"Database constraint failed: {exc}"}, 400)
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON body."}, 400)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        try:
            if parsed.path.startswith("/api/order/"):
                order_id = int(parsed.path.rsplit("/", 1)[-1])
                self.send_json(remove_order(order_id))
            else:
                self.send_json({"error": "Unknown endpoint."}, 404)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, 400)
        except sqlite3.IntegrityError as exc:
            self.send_json({"error": f"Database constraint failed: {exc}"}, 400)

    def serve_file(self, path):
        path = path.resolve()
        if ROOT not in path.parents and path != ROOT:
            self.send_error(403)
            return
        if not path.exists() or not path.is_file():
            self.send_error(404)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    init_db()
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Smart Warehouse Logistics running at http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
