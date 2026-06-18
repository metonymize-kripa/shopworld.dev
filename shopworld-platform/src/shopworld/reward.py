"""Reward vector computation for multi-objective agent training."""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class RewardVector:
    """Multi-dimensional reward for commerce agent evaluation."""
    
    task_completion: float = 0.0
    business_outcome: float = 0.0
    revenue_impact: float = 0.0
    margin_impact: float = 0.0
    cash_impact: float = 0.0
    customer_outcome: float = 0.0
    satisfaction_delta: float = 0.0
    operational_outcome: float = 0.0
    sla_compliance: float = 0.0
    api_efficiency: float = 0.0
    query_correctness: float = 0.0
    policy_compliance: float = 0.0
    scope_adherence: float = 0.0
    collateral_damage: float = 0.0
    strategic_consistency: float = 0.0
    escalation_quality: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "task_completion": self.task_completion,
            "business_outcome": self.business_outcome,
            "revenue_impact": self.revenue_impact,
            "margin_impact": self.margin_impact,
            "cash_impact": self.cash_impact,
            "customer_outcome": self.customer_outcome,
            "satisfaction_delta": self.satisfaction_delta,
            "operational_outcome": self.operational_outcome,
            "sla_compliance": self.sla_compliance,
            "api_efficiency": self.api_efficiency,
            "query_correctness": self.query_correctness,
            "policy_compliance": self.policy_compliance,
            "scope_adherence": self.scope_adherence,
            "collateral_damage": self.collateral_damage,
            "strategic_consistency": self.strategic_consistency,
            "escalation_quality": self.escalation_quality,
        }
    
    def to_scalar(self, weights: Optional[Dict[str, float]] = None) -> float:
        """Convert to scalar for RL training."""
        if weights is None:
            weights = {
                "task_completion": 1.0,
                "business_outcome": 0.5,
                "customer_outcome": 0.3,
                "operational_outcome": 0.3,
                "policy_compliance": 1.0,
                "scope_adherence": 0.8,
                "collateral_damage": 1.0,
            }
        
        total = 0.0
        for key, weight in weights.items():
            value = getattr(self, key, 0.0)
            total += value * weight
        
        return total
    
    def is_safe(self) -> bool:
        """Check if action was safe (no major violations)."""
        return (
            self.policy_compliance >= -5 and
            self.collateral_damage >= -5 and
            self.scope_adherence >= -5
        )
