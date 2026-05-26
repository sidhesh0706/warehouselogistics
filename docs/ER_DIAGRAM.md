# Smart Warehouse Logistics - ER Diagram

This ER diagram is generated from the project schema in `schema.sql`.

```mermaid
erDiagram
    SUPPLIERS ||--o{ PRODUCTS : supplies
    PRODUCTS ||--o{ INVENTORY : stocked_as
    WAREHOUSES ||--o{ INVENTORY : stores
    PRODUCTS ||--o{ ORDERS : ordered_in
    WAREHOUSES ||--o{ ORDERS : fulfilled_from
    PRODUCTS ||--o{ STOCK_MOVEMENTS : tracked_in
    WAREHOUSES ||--o{ STOCK_MOVEMENTS : source_location
    WAREHOUSES ||--o{ STOCK_MOVEMENTS : destination_location
    PRODUCTS ||--o{ REORDER_ALERTS : raises
    WAREHOUSES ||--o{ REORDER_ALERTS : monitored_at
    INVENTORY ||--o{ EXPIRY_ALERTS : triggers
    PRODUCTS ||--o{ EXPIRY_ALERTS : belongs_to
    WAREHOUSES ||--o{ EXPIRY_ALERTS : monitored_at
    PRODUCTS ||--o{ ACTION_LOGS : optionally_audited

    SUPPLIERS {
        INTEGER supplier_id PK
        TEXT supplier_name
        TEXT contact_person
        TEXT phone
        TEXT email UK
        TEXT address
    }

    PRODUCTS {
        INTEGER product_id PK
        INTEGER supplier_id FK
        TEXT product_name
        TEXT sku UK
        TEXT category
        REAL unit_price
        INTEGER reorder_level
        INTEGER expiry_required
    }

    WAREHOUSES {
        INTEGER warehouse_id PK
        TEXT warehouse_name
        TEXT location
        TEXT city
        INTEGER capacity
        TEXT manager
        TEXT status
    }

    INVENTORY {
        INTEGER stock_id PK
        INTEGER product_id FK
        INTEGER warehouse_id FK
        INTEGER quantity
        TEXT bin_location
        TEXT bin_status
        TEXT expiry_date
        TEXT last_stock_check
    }

    ORDERS {
        INTEGER order_id PK
        INTEGER product_id FK
        INTEGER warehouse_id FK
        TEXT customer_name
        TEXT order_date
        TEXT order_status
        INTEGER quantity_ordered
        REAL total_amount
    }

    STOCK_MOVEMENTS {
        INTEGER movement_id PK
        INTEGER product_id FK
        INTEGER source_warehouse_id FK
        INTEGER destination_warehouse_id FK
        TEXT movement_type
        INTEGER quantity
        TEXT movement_date
        TEXT reference_note
    }

    REORDER_ALERTS {
        INTEGER alert_id PK
        INTEGER product_id FK
        INTEGER warehouse_id FK
        INTEGER current_quantity
        INTEGER reorder_level
        TEXT alert_status
        TEXT created_at
        TEXT resolved_at
    }

    EXPIRY_ALERTS {
        INTEGER alert_id PK
        INTEGER stock_id FK
        INTEGER product_id FK
        INTEGER warehouse_id FK
        TEXT expiry_date
        INTEGER days_to_expiry
        TEXT alert_status
        TEXT created_at
        TEXT resolved_at
    }

    ACTION_LOGS {
        INTEGER log_id PK
        INTEGER related_product_id FK
        TEXT action_type
        TEXT entity_name
        INTEGER entity_id
        TEXT summary
        TEXT details
        TEXT created_at
    }
```

## Relationship Summary

- One supplier supplies many products.
- One product can appear in many inventory rows, orders, stock movements, reorder alerts, expiry alerts, and audit logs.
- One warehouse can store many inventory rows, fulfil many orders, appear in stock movements, and generate alerts.
- One inventory row can generate many expiry alert records over time.
- Action logs optionally reference products through `related_product_id`; some actions, such as demo reset, are system-level actions and keep this field empty.
