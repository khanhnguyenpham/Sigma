"""Register all thirteen domain tables on the single shared metadata for Alembic."""
from core.db import Base as Base
from modules.catalog.models import Warehouse as Warehouse, Item as Item, Supplier as Supplier
from modules.configuration.models import Policy as Policy, Scenario as Scenario
from modules.runs.models import Run as Run
from modules.forecasting.models import DailySales as DailySales, RouteForecast as RouteForecast, ItemForecast as ItemForecast
from modules.inventory.models import InventoryEvent as InventoryEvent, InventoryDaily as InventoryDaily
from modules.purchasing.models import Replenishment as Replenishment
from modules.alerts.models import Alert as Alert
