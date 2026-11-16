// Management pages read the real ledger only; forecast/scenario pages live under the Tools group.
export const NAV_GROUPS = [
  ["", [["dashboard", "grid", "Tổng quan"]]],
  ["KHO", [["stock", "box", "Tồn kho"], ["documents", "download", "Chứng từ"], ["warehouses", "warehouse", "Kho hàng"]]],
  ["NHẬP HÀNG", [["orders", "truck", "Đơn nhập"], ["recommendations", "check", "Đề xuất nhập"], ["suppliers", "settings", "Nhà cung cấp"]]],
  ["ĐẠI LÝ", [["dealer-requests", "check", "Yêu cầu lấy hàng"], ["dealers", "grid", "Danh sách đại lý"]]],
  ["DANH MỤC", [["catalog", "box", "Sản phẩm"]]],
  ["HỆ THỐNG", [["audit", "clock", "Lịch sử thao tác"]]],
  ["CÔNG CỤ", [["forecast", "chart", "Dự báo & kịch bản"]]],
] as const;

// Management page id -> tab key of the Operations page.
export const OPS_TAB: Record<string, string> = {
  stock: "stock", documents: "documents", warehouses: "warehouses", orders: "orders",
  recommendations: "recommendations", suppliers: "suppliers", catalog: "products", audit: "audit",
};
export const MANAGEMENT_PAGES = ["dashboard", "dealers", "dealer-requests", ...Object.keys(OPS_TAB)];

export const TOOL_PAGES = [
  ["forecast", "Dự báo"],
  ["scenarios", "Kịch bản"],
  ["overview", "Tổng quan mô phỏng"],
  ["inventory", "Tồn mô phỏng"],
  ["replenishment", "Nhập hàng mô phỏng"],
  ["alerts", "Cảnh báo"],
  ["products", "Chính sách sản phẩm"],
] as const;

export const isManagementPage = (page: string) => MANAGEMENT_PAGES.includes(page);

export function pageTitle(page: string) {
  if (page === "product") return ["Công cụ dự báo", "Cấu hình sản phẩm"];
  const tool = TOOL_PAGES.find(([id]) => id === page);
  if (tool) return ["Công cụ dự báo", tool[1]];
  for (const [group, pages] of NAV_GROUPS)
    for (const [id, , name] of pages) if (id === page) return [group ? group.charAt(0) + group.slice(1).toLowerCase() : "Quản lý", name];
  return ["Quản lý", "Tổng quan"];
}

export const inventoryKinds = ["stock_projection", "policy_replay", "alert_replay"];
