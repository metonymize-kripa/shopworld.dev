"""ShopWorld: A deterministic RL environment for Shopify merchant AI agents."""

from shopworld.environment import ShopWorldEnv
from shopworld.task import Task, TaskLoader
from shopworld.evaluator import Evaluator, EvaluationResult
from shopworld.reward import RewardVector

__version__ = "0.1.0"
__all__ = [
    "ShopWorldEnv",
    "Task",
    "TaskLoader", 
    "Evaluator",
    "EvaluationResult",
    "RewardVector",
]
