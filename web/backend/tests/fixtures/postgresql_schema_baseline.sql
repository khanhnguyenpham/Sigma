CREATE TABLE alerts (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	run_id UUID NOT NULL,
	window_origin DATE NOT NULL,
	item_id BIGINT NOT NULL,
	as_of_date DATE NOT NULL,
	alert_type TEXT NOT NULL,
	state TEXT NOT NULL,
	predicted_depletion_date DATE,
	actual_depletion_date DATE,
	lead_days SMALLINT,
	is_evaluable BOOLEAN NOT NULL,
	evaluation_class TEXT,
	exclusion_reason TEXT,
	explanation JSONB NOT NULL,
	is_simulated BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (run_id, window_origin, item_id, as_of_date, alert_type),
	CHECK (alert_type IN ('below_rop','depletion')),
	CHECK (state IN ('low_stock','pending_covers','urgent','early','already_depleted','not_within_horizon')),
	CHECK (evaluation_class IS NULL OR evaluation_class IN ('TP','FP','FN','TN')),
	FOREIGN KEY(run_id) REFERENCES runs (id) ON DELETE RESTRICT,
	FOREIGN KEY(item_id) REFERENCES items (id) ON DELETE RESTRICT
);

CREATE INDEX ix_alert_state ON alerts (run_id, state, as_of_date);

CREATE TABLE daily_sales (
	source_import_run_id UUID NOT NULL,
	item_id BIGINT NOT NULL,
	date DATE NOT NULL,
	sales_qty BIGINT,
	order_count BIGINT,
	actual_available BOOLEAN NOT NULL,
	PRIMARY KEY (source_import_run_id, item_id, date),
	CHECK ((actual_available AND sales_qty IS NOT NULL AND sales_qty>=0 AND order_count IS NOT NULL AND order_count>=0) OR (NOT actual_available AND sales_qty IS NULL AND order_count IS NULL)),
	FOREIGN KEY(source_import_run_id) REFERENCES runs (id) ON DELETE RESTRICT,
	FOREIGN KEY(item_id) REFERENCES items (id) ON DELETE RESTRICT
);

CREATE INDEX ix_sales_date ON daily_sales (source_import_run_id, date, item_id);

CREATE TABLE inventory_daily (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	run_id UUID NOT NULL,
	window_origin DATE NOT NULL,
	item_id BIGINT NOT NULL,
	date DATE NOT NULL,
	policy_id BIGINT,
	forecast_as_of_date DATE NOT NULL,
	opening_qty BIGINT NOT NULL,
	receipts_qty BIGINT NOT NULL,
	sales_qty BIGINT NOT NULL,
	fulfilled_qty BIGINT NOT NULL,
	shortage_qty BIGINT NOT NULL,
	closing_qty BIGINT NOT NULL,
	ss BIGINT,
	rop_forecast BIGINT,
	rop BIGINT,
	target_stock BIGINT,
	pending_qty BIGINT NOT NULL,
	inventory_position BIGINT NOT NULL,
	needs_replenishment BOOLEAN,
	recommended_qty BIGINT,
	config_status TEXT NOT NULL,
	is_simulated BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(policy_id, item_id) REFERENCES supplier_item_policies (id, item_id) ON DELETE RESTRICT,
	UNIQUE (run_id, window_origin, item_id, date),
	CHECK (opening_qty>=0 AND receipts_qty>=0 AND sales_qty>=0 AND fulfilled_qty>=0 AND shortage_qty>=0 AND closing_qty>=0 AND pending_qty>=0),
	CHECK (closing_qty=opening_qty+receipts_qty-fulfilled_qty AND sales_qty=fulfilled_qty+shortage_qty AND inventory_position=closing_qty+pending_qty),
	CHECK (ss>=0 AND rop_forecast>=0 AND rop>=0 AND target_stock>=0 AND recommended_qty>=0),
	FOREIGN KEY(run_id) REFERENCES runs (id) ON DELETE RESTRICT,
	FOREIGN KEY(item_id) REFERENCES items (id) ON DELETE RESTRICT
);

CREATE INDEX ix_inventory_date ON inventory_daily (run_id, date, item_id);

CREATE TABLE inventory_events (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	run_id UUID NOT NULL,
	window_origin DATE NOT NULL,
	item_id BIGINT NOT NULL,
	event_at TIMESTAMP WITH TIME ZONE NOT NULL,
	event_sequence BIGINT NOT NULL,
	event_kind TEXT NOT NULL,
	source_sequence BIGINT,
	replenishment_order_id BIGINT,
	quantity BIGINT NOT NULL,
	fulfilled_qty BIGINT NOT NULL,
	shortage_qty BIGINT NOT NULL,
	balance_after BIGINT NOT NULL,
	is_simulated BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (run_id, window_origin, item_id, event_sequence),
	CHECK (quantity>=0 AND fulfilled_qty>=0 AND shortage_qty>=0 AND balance_after>=0 AND event_sequence>=0),
	CHECK ((event_kind='sale' AND quantity=fulfilled_qty+shortage_qty AND source_sequence IS NOT NULL AND replenishment_order_id IS NULL) OR (event_kind='receipt' AND fulfilled_qty=0 AND shortage_qty=0 AND replenishment_order_id IS NOT NULL) OR (event_kind='initial_stock' AND fulfilled_qty=0 AND shortage_qty=0 AND replenishment_order_id IS NULL)),
	FOREIGN KEY(run_id) REFERENCES runs (id) ON DELETE RESTRICT,
	FOREIGN KEY(item_id) REFERENCES items (id) ON DELETE RESTRICT,
	FOREIGN KEY(replenishment_order_id) REFERENCES replenishment_orders (id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX uq_receipt_once ON inventory_events (replenishment_order_id) WHERE event_kind='receipt';

CREATE TABLE item_forecasts (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	run_id UUID NOT NULL,
	item_id BIGINT NOT NULL,
	as_of_date DATE NOT NULL,
	target_date DATE NOT NULL,
	horizon_day SMALLINT NOT NULL,
	forecast_qty DOUBLE PRECISION NOT NULL,
	actual_qty BIGINT,
	actual_available BOOLEAN NOT NULL,
	item_share DOUBLE PRECISION NOT NULL,
	weekday_weight DOUBLE PRECISION NOT NULL,
	share_window_days SMALLINT NOT NULL,
	allocation_basis TEXT NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (run_id, item_id, as_of_date, target_date),
	CHECK (horizon_day BETWEEN 1 AND 14 AND target_date=as_of_date+horizon_day),
	CHECK (forecast_qty>=0 AND forecast_qty<'Infinity'::float8 AND item_share BETWEEN 0 AND 1 AND weekday_weight BETWEEN 0 AND 1 AND share_window_days IN (30,90)),
	CHECK ((actual_available AND actual_qty IS NOT NULL AND actual_qty>=0) OR (NOT actual_available AND actual_qty IS NULL)),
	FOREIGN KEY(run_id) REFERENCES runs (id) ON DELETE RESTRICT,
	FOREIGN KEY(item_id) REFERENCES items (id) ON DELETE RESTRICT
);

CREATE INDEX ix_item_forecast_origin ON item_forecasts (run_id, as_of_date, item_id);

CREATE INDEX ix_item_forecast_target ON item_forecasts (run_id, target_date);

CREATE TABLE items (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	warehouse_id BIGINT NOT NULL,
	sku TEXT NOT NULL,
	product_type TEXT NOT NULL,
	first_seen_date DATE NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (warehouse_id, sku, product_type),
	CHECK (product_type IN ('eSIM','physical_SIM')),
	FOREIGN KEY(warehouse_id) REFERENCES warehouses (id) ON DELETE RESTRICT
);

CREATE INDEX ix_items_warehouse ON items (warehouse_id);

CREATE TABLE replenishment_orders (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	run_id UUID NOT NULL,
	window_origin DATE NOT NULL,
	item_id BIGINT NOT NULL,
	policy_id BIGINT NOT NULL,
	order_key TEXT NOT NULL,
	ordered_on DATE NOT NULL,
	eta DATE NOT NULL,
	ordered_qty BIGINT NOT NULL,
	received_qty BIGINT NOT NULL,
	status TEXT NOT NULL,
	is_initial BOOLEAN NOT NULL,
	is_simulated BOOLEAN NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(policy_id, item_id) REFERENCES supplier_item_policies (id, item_id) ON DELETE RESTRICT,
	UNIQUE (run_id, window_origin, order_key),
	CHECK (ordered_qty>0 AND eta=ordered_on+7 AND ((status='ordered' AND received_qty=0) OR (status='received' AND received_qty=ordered_qty))),
	FOREIGN KEY(run_id) REFERENCES runs (id) ON DELETE RESTRICT,
	FOREIGN KEY(item_id) REFERENCES items (id) ON DELETE RESTRICT
);

CREATE INDEX ix_orders_eta ON replenishment_orders (run_id, eta, status);

CREATE TABLE route_forecasts (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	run_id UUID NOT NULL,
	warehouse_id BIGINT NOT NULL,
	as_of_date DATE NOT NULL,
	block SMALLINT NOT NULL,
	window_start DATE NOT NULL,
	target_date DATE NOT NULL,
	forecast_qty DOUBLE PRECISION NOT NULL,
	actual_qty DOUBLE PRECISION,
	actual_available BOOLEAN NOT NULL,
	family TEXT NOT NULL,
	model_id TEXT NOT NULL,
	selection_basis TEXT NOT NULL,
	parent_bundle_sha256 TEXT,
	PRIMARY KEY (id),
	UNIQUE (run_id, warehouse_id, as_of_date, block),
	CHECK (block IN (1,2) AND window_start=as_of_date+1+7*(block-1) AND target_date=as_of_date+7*block),
	CHECK (forecast_qty>=0 AND forecast_qty<'Infinity'::float8),
	CHECK ((actual_available AND actual_qty IS NOT NULL AND actual_qty>=0 AND actual_qty<'Infinity'::float8) OR (NOT actual_available AND actual_qty IS NULL)),
	FOREIGN KEY(run_id) REFERENCES runs (id) ON DELETE RESTRICT,
	FOREIGN KEY(warehouse_id) REFERENCES warehouses (id) ON DELETE RESTRICT
);

CREATE INDEX ix_route_forecast_origin ON route_forecasts (run_id, as_of_date, warehouse_id);

CREATE TABLE runs (
	id UUID NOT NULL,
	kind TEXT NOT NULL,
	status TEXT NOT NULL,
	source_import_run_id UUID,
	forecast_run_id UUID,
	retry_of_run_id UUID,
	scenario_id BIGINT,
	as_of_date DATE NOT NULL,
	period_start DATE,
	period_end DATE,
	observation_end DATE NOT NULL,
	target_version TEXT NOT NULL,
	config_version TEXT NOT NULL,
	assumption_version TEXT NOT NULL,
	source_sha256 VARCHAR(64),
	code_revision TEXT NOT NULL,
	code_sha256 VARCHAR(64) NOT NULL,
	config_snapshot JSONB NOT NULL,
	config_sha256 VARCHAR(64) NOT NULL,
	request_key VARCHAR(128) NOT NULL,
	request_sha256 VARCHAR(64) NOT NULL,
	selection_sha256 VARCHAR(64),
	result_summary JSONB NOT NULL,
	artifact_manifest JSONB NOT NULL,
	error_code TEXT,
	started_at TIMESTAMP WITH TIME ZONE,
	finished_at TIMESTAMP WITH TIME ZONE,
	heartbeat_at TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CHECK (kind IN ('source_import','forecast','policy_replay','alert_replay','stock_projection')),
	CHECK (status IN ('queued','running','complete','failed','invalidated')),
	CHECK (source_import_run_id IS DISTINCT FROM id AND forecast_run_id IS DISTINCT FROM id AND retry_of_run_id IS DISTINCT FROM id),
	CHECK (period_end IS NULL OR (period_start IS NOT NULL AND period_end>=period_start)),
	FOREIGN KEY(source_import_run_id) REFERENCES runs (id) ON DELETE RESTRICT,
	FOREIGN KEY(forecast_run_id) REFERENCES runs (id) ON DELETE RESTRICT,
	FOREIGN KEY(retry_of_run_id) REFERENCES runs (id) ON DELETE RESTRICT,
	FOREIGN KEY(scenario_id) REFERENCES scenarios (id) ON DELETE RESTRICT,
	UNIQUE (request_key)
);

CREATE INDEX ix_runs_queue ON runs (status, created_at);

CREATE TABLE scenarios (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	code TEXT NOT NULL,
	version INTEGER NOT NULL,
	name TEXT NOT NULL,
	description TEXT NOT NULL,
	settings JSONB NOT NULL,
	assumption_version TEXT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (code, version),
	CHECK (version>=1)
);

CREATE TABLE supplier_item_policies (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	item_id BIGINT NOT NULL,
	supplier_id BIGINT NOT NULL,
	version INTEGER NOT NULL,
	effective_from DATE NOT NULL,
	effective_to DATE,
	configured_rop_floor BIGINT NOT NULL,
	moq BIGINT NOT NULL,
	safety_days NUMERIC(8, 3) NOT NULL,
	is_assumed BOOLEAN NOT NULL,
	assumption_source TEXT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (item_id, version),
	UNIQUE (item_id, effective_from),
	UNIQUE (id, item_id),
	CHECK (configured_rop_floor>=0 AND moq>=1 AND safety_days>=0 AND version>=1),
	CHECK (effective_to IS NULL OR effective_to>effective_from),
	FOREIGN KEY(item_id) REFERENCES items (id) ON DELETE RESTRICT,
	FOREIGN KEY(supplier_id) REFERENCES suppliers (id) ON DELETE RESTRICT
);

CREATE INDEX ix_policy_effective ON supplier_item_policies (item_id, effective_from, effective_to);

CREATE TABLE suppliers (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	code TEXT NOT NULL,
	display_name TEXT NOT NULL,
	is_assumed BOOLEAN NOT NULL,
	assumption_source TEXT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (code)
);

CREATE TABLE warehouses (
	id BIGINT GENERATED ALWAYS AS IDENTITY,
	code TEXT NOT NULL,
	destination_country TEXT NOT NULL,
	carrier TEXT NOT NULL,
	city TEXT NOT NULL,
	is_assumed BOOLEAN NOT NULL,
	assumption_source TEXT NOT NULL,
	version INTEGER NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (destination_country, carrier),
	CHECK (version >= 1),
	CHECK (length(city)>0),
	UNIQUE (code)
);
