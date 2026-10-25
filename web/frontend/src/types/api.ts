export type Row = Record<string, unknown>;

export interface Run {
  id: string;
  kind: string;
  status: string;
  as_of_date: string;
  observation_end: string;
  source_import_run_id: string | null;
  forecast_run_id: string | null;
  scenario_id: number | null;
  config_version: string;
  assumption_version: string;
  target_version: string;
  error_code: string | null;
  result_summary: Row;
  period_start: string | null;
  period_end: string | null;
  created_at: string;
}

export interface Page<T = Row> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  context?: Row;
}

export interface WorkspaceData {
  context: Row;
  summary: Row;
  attention: Row[];
  incoming: Row[];
  route_stock: Row[];
}
