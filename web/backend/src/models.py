"""Register domain tables on the single shared metadata for Alembic."""
from core.db import Base as Base
from modules.catalog.models import Warehouse as Warehouse, Item as Item, Supplier as Supplier
from modules.catalog.models import ItemSupplyChange as ItemSupplyChange
from modules.catalog.models import ProviderProductNotice as ProviderProductNotice
from modules.catalog.models import ProviderProductNoticeItem as ProviderProductNoticeItem
from modules.catalog.models import ProviderProductNoticeEvent as ProviderProductNoticeEvent
from modules.configuration.models import Policy as Policy, Scenario as Scenario
from modules.runs.models import Run as Run
from modules.forecasting.models import DailySales as DailySales, RouteForecast as RouteForecast, ItemForecast as ItemForecast
from modules.inventory.models import InventoryEvent as InventoryEvent, InventoryDaily as InventoryDaily
from modules.purchasing.models import Replenishment as Replenishment
from modules.alerts.models import Alert as Alert
from modules.auth.models import User as User, LoginSession as LoginSession
from modules.operations.models import SupplierSettings as SupplierSettings, OperationalOrder as OperationalOrder
from modules.operations.models import OperationalOrderLine as OperationalOrderLine, StockDocument as StockDocument
from modules.operations.models import StockDocumentLine as StockDocumentLine, StockBalance as StockBalance, OperationAudit as OperationAudit
from modules.operations.models import OperationalWarehouse as OperationalWarehouse, OperationalProduct as OperationalProduct
from modules.dealers.models import Dealer as Dealer, DealerRequest as DealerRequest, DealerRequestLine as DealerRequestLine
