"""Explicit additions; original M2/M3 HTTP and DDL goldens stay unchanged."""
OPS_TABLES = {"ops_warehouses", "ops_products", "ops_supplier_settings", "ops_purchase_orders", "ops_purchase_order_lines",
    "ops_stock_documents", "ops_stock_document_lines", "ops_stock_balances", "ops_audit_events"}
OPS_SCHEMAS = {"OpsWarehouseInput", "OpsWarehouseUpdate", "OpsProductInput", "OpsProductUpdate", "OpsSupplierSettingsInput",
    "OpsOrderLineInput", "OpsOrderInput", "OpsOrderUpdate", "OpsOrderTransition", "OpsReceiptLineInput", "OpsReceiptInput", "OpsMovementInput"}
OPS_ROUTES = {"/api/v1/operations/" + path: methods for path, methods in {
    "summary": ["get"], "warehouses": ["get", "post"], "warehouses/{key}": ["patch"],
    "products": ["get", "post"], "products/{key}": ["patch"], "suppliers": ["get"], "suppliers/{key}/settings": ["patch"],
    "orders": ["get", "post"], "orders/{key}": ["get", "patch"], "orders/{key}/confirm": ["post"],
    "orders/{key}/cancel": ["post"], "orders/{key}/receipts": ["post"], "stock": ["get"], "stock/{warehouse_id}/{item_id}": ["get"],
    "issues": ["post"], "counts": ["post"], "documents": ["get"], "documents/{key}": ["get"], "audit": ["get"],
}.items()}
OPS_ROUTES.update({"/api/v1/supplier/orders": ["get"], "/api/v1/supplier/orders/{key}": ["get"], "/api/v1/supplier/operational-products": ["get"]})
OPS_ROUTES['/api/v1/operations/recommendations'] = ['get']
OPS_SCHEMAS.add('OpsQrScanInput')
OPS_ROUTES.update({'/api/v1/operations/orders/{key}/receipt-qr':['post'], '/api/v1/operations/orders/{key}/receipt-qr/preview':['post']})
