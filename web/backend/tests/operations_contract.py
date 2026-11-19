"""Explicit additions; original M2/M3 HTTP and DDL goldens stay unchanged."""
OPS_TABLES = {"ops_warehouses", "ops_products", "supplier_settings", "ops_purchase_orders", "ops_purchase_order_lines",
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
# 0012: dealer management replaces the retired supplier portal.
OPS_TABLES |= {"dealers", "dealer_requests", "dealer_request_lines"}
OPS_SCHEMAS |= {"OpsEtaChange", "DealerInput", "DealerUpdate", "RequestLineInput", "DealerRequestInput", "Transition", "Rejection", "IssueInput"}
OPS_ROUTES.update({"/api/v1/dealers": ["get", "post"], "/api/v1/dealers/{key}": ["patch"], "/api/v1/dealers/requests": ["get"],
    "/api/v1/dealers/requests/{key}": ["get"], "/api/v1/dealers/requests/{key}/approve": ["post"],
    "/api/v1/dealers/requests/{key}/reject": ["post"], "/api/v1/dealers/requests/{key}/issue": ["post"],
    "/api/v1/dealer/products": ["get"], "/api/v1/dealer/requests": ["get", "post"], "/api/v1/dealer/requests/{key}": ["get"],
    "/api/v1/dealer/requests/{key}/cancel": ["post"], "/api/v1/operations/orders/{key}/eta": ["post"], "/api/v1/dealer/requests/{key}/receive": ["post"], "/api/v1/dealer/stock": ["get"]})
OPS_ROUTES['/api/v1/operations/recommendations'] = ['get']
OPS_ROUTES['/api/v1/operations/queue-status'] = ['get']
OPS_SCHEMAS.add('OpsQrScanInput')
OPS_ROUTES.update({'/api/v1/operations/orders/{key}/receipt-qr':['post'], '/api/v1/operations/orders/{key}/receipt-qr/preview':['post']})
# Catalog filter options (countries and suppliers with registered products).
OPS_ROUTES['/api/v1/operations/product-filters'] = ['get']
