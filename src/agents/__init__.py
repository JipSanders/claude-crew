from .coder import CoderAgent
from .marketer import MarketerAgent
from .designer import DesignerAgent
from .analyst import AnalystAgent
from .sales import SalesAgent

REGISTRY: dict[str, type] = {
    "coder": CoderAgent,
    "marketer": MarketerAgent,
    "designer": DesignerAgent,
    "analyst": AnalystAgent,
    "sales": SalesAgent,
}
