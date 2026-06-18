"""Tests for ShopWorld environment."""

import pytest
from datetime import datetime

from shopworld.environment import ShopWorldEnv, Action, Observation
from shopworld.task import Task
from shopworld.common.errors import ShopWorldError


class TestShopWorldEnv:
    """Test suite for ShopWorldEnv."""
    
    def test_env_initialization(self):
        """Test environment can be initialized."""
        env = ShopWorldEnv()
        assert env is not None
        assert env.enable_tracing is True
    
    def test_env_reset(self):
        """Test environment reset creates valid initial state."""
        env = ShopWorldEnv()
        obs, info = env.reset(seed=42)
        
        assert obs is not None
        assert info is not None
        assert "episode_id" in info
        assert obs.step_number == 0
        assert obs.timestamp is not None
    
    def test_env_reset_deterministic(self):
        """Test that same seed produces same initial state."""
        env1 = ShopWorldEnv()
        obs1, info1 = env1.reset(seed=42)
        
        env2 = ShopWorldEnv()
        obs2, info2 = env2.reset(seed=42)
        
        assert obs1.timestamp == obs2.timestamp
        assert info1["episode_id"] != info2["episode_id"]  # UUIDs should differ
    
    def test_env_step_increments(self):
        """Test that step increments step counter."""
        env = ShopWorldEnv()
        obs, _ = env.reset(seed=42)
        
        action = Action(tool_name="query_orders", arguments={})
        obs2, reward, terminated, truncated, info = env.step(action)
        
        assert obs2.step_number == 1
        assert info["step_number"] == 1
    
    def test_env_step_after_termination_raises(self):
        """Test that stepping after termination raises error."""
        env = ShopWorldEnv(max_steps=1)
        obs, _ = env.reset(seed=42)
        
        action = Action(tool_name="query_orders", arguments={})
        env.step(action)  # This should truncate after max_steps
        
        with pytest.raises(ShopWorldError):
            env.step(action)
    
    def test_trace_recording(self):
        """Test that trace is recorded when tracing enabled."""
        env = ShopWorldEnv(enable_tracing=True)
        obs, _ = env.reset(seed=42)
        
        action = Action(tool_name="query_orders", arguments={})
        env.step(action)
        
        trace = env.get_trace()
        assert len(trace) == 1
        assert trace[0].action.tool_name == "query_orders"
    
    def test_trace_empty_when_disabled(self):
        """Test that trace is empty when tracing disabled."""
        env = ShopWorldEnv(enable_tracing=False)
        obs, _ = env.reset(seed=42)
        
        action = Action(tool_name="query_orders", arguments={})
        env.step(action)
        
        trace = env.get_trace()
        assert len(trace) == 0


class TestTaskIntegration:
    """Test task integration with environment."""
    
    def test_task_provides_initial_state(self):
        """Test that task provides initial state."""
        task = Task(
            id="test-001",
            name="Test Task",
            description="A test task",
            difficulty=1,
            domain="test",
            initial_hidden_state={"test_key": "test_value"},
        )
        
        env = ShopWorldEnv(task=task)
        obs, info = env.reset(seed=42)
        
        assert env.hidden_state.get("test_key") == "test_value"
    
    def test_task_scopes_applied(self):
        """Test that task scopes are applied to environment."""
        task = Task(
            id="test-002",
            name="Test Task",
            description="A test task",
            difficulty=1,
            domain="test",
            allowed_scopes=["read_orders", "read_customers"],
        )
        
        env = ShopWorldEnv(task=task)
        obs, info = env.reset(seed=42)
        
        assert "read_orders" in env.granted_scopes
        assert "read_customers" in env.granted_scopes


class TestAction:
    """Test Action dataclass."""
    
    def test_action_creation(self):
        """Test action can be created."""
        action = Action(
            tool_name="query_orders",
            arguments={"status": "open"},
        )
        
        assert action.tool_name == "query_orders"
        assert action.arguments["status"] == "open"
    
    def test_action_with_message(self):
        """Test action with message component."""
        action = Action(
            tool_name="send_message",
            arguments={"ticket_id": "123"},
            message="Hello, how can I help?",
        )
        
        assert action.message == "Hello, how can I help?"


class TestClock:
    """Test simulated clock."""
    
    def test_clock_advances_on_step(self):
        """Test that clock advances with environment steps."""
        env = ShopWorldEnv()
        obs, _ = env.reset(seed=42)
        
        initial_time = obs.timestamp
        
        action = Action(tool_name="query_orders", arguments={})
        obs2, _, _, _, _ = env.step(action)
        
        assert obs2.timestamp > initial_time
