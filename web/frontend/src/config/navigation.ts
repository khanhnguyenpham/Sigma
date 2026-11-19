export const TOOL_PAGES = [
  ["forecast", "Dự báo"],
  ["scenarios", "Kịch bản"],
  ["overview", "Tổng quan mô phỏng"],
  ["inventory", "Tồn mô phỏng"],
  ["replenishment", "Nhập hàng mô phỏng"],
  ["alerts", "Cảnh báo"],
  ["products", "Chính sách sản phẩm"],
] as const;

// Sidebar: [label, icon, children]. Children fold under their parent; the unlabeled group renders flat.
// Management pages read the real ledger only; forecast/scenario pages live under the Tools group.
export const NAV_GROUPS = [
  ["", "grid", [["dashboard", "Tổng quan"]]],
  ["Kho", "warehouse", [["stock", "Tồn kho"], ["documents", "Chứng từ"], ["warehouses", "Kho hàng"]]],
  ["Nhập hàng", "truck", [["orders", "Đơn nhập"], ["recommendations", "Đề xuất nhập"], ["suppliers", "Nhà cung cấp"]]],
  ["Đại lý", "check", [["dealer-requests", "Yêu cầu lấy hàng"], ["dealers", "Danh sách đại lý"]]],
  ["Danh mục", "box", [["catalog", "Sản phẩm"]]],
  ["Hệ thống", "clock", [["audit", "Lịch sử thao tác"]]],
  ["Công cụ dự báo", "chart", TOOL_PAGES],
] as const;

// Management page id -> tab key of the Operations page.
export const OPS_TAB: Record<string, string> = {
  stock: "stock", documents: "documents", warehouses: "warehouses", orders: "orders",
  recommendations: "recommendations", suppliers: "suppliers", catalog: "products", audit: "audit",
};
export const MANAGEMENT_PAGES = ["dashboard", "dealers", "dealer-requests", ...Object.keys(OPS_TAB)];

export const isManagementPage = (page: string) => MANAGEMENT_PAGES.includes(page);

// The product configuration page sits under its "Chính sách sản phẩm" menu entry.
export const menuPage = (page: string) => (page === "product" ? "products" : page);

export function pageTitle(page: string) {
  if (page === "product") return ["Công cụ dự báo", "Cấu hình sản phẩm"];
  for (const [group, , pages] of NAV_GROUPS)
    for (const [id, name] of pages) if (id === page) return [group || "Quản lý", name];
  return ["Quản lý", "Tổng quan"];
}

export const inventoryKinds = ["stock_projection", "policy_replay", "alert_replay"];
