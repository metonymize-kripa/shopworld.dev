"""Built-in task library for ShopWorld.

MVP scenario families (README §10):
  - WISMO
  - Cancellation
  - Address change
  - Refund
  - Return
"""

from shopworld.tasks.wismo import create_wismo_task
from shopworld.tasks.cancellation import create_cancellation_task
from shopworld.tasks.address_change import create_address_change_task
from shopworld.tasks.refund import create_refund_task
from shopworld.tasks.return_item import create_return_task

__all__ = [
    "create_wismo_task",
    "create_cancellation_task",
    "create_address_change_task",
    "create_refund_task",
    "create_return_task",
]
