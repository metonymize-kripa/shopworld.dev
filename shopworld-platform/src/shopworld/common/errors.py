"""ShopWorld exception hierarchy."""


class ShopWorldError(Exception):
    """Base exception for ShopWorld."""
    pass


class TaskError(ShopWorldError):
    """Error loading or executing a task."""
    pass


class EvaluationError(ShopWorldError):
    """Error during evaluation."""
    pass


class SimulationError(ShopWorldError):
    """Error in world simulation."""
    pass


class PolicyViolationError(ShopWorldError):
    """Agent action violated merchant policy."""
    pass


class ScopeError(ShopWorldError):
    """Agent attempted action outside granted API scopes."""
    pass


class APICostExceededError(ShopWorldError):
    """Agent exceeded simulated API cost budget."""
    pass
