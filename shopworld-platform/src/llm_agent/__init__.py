"""llm_agent: an LLM-powered, tool-using merchant runtime under test.

Provider-agnostic: the agent drives a ReAct-style tool-use loop over any
``LLMClient``. A deterministic offline client (``ScriptedLLMClient``) is the
default so the benchmark runs without network or API keys; ``AnthropicClient``
is a drop-in adapter for a hosted model, and ``OllamaClient`` runs a local model.

This package is a sibling of ``shopworld`` and is never imported by ShopWorld
core (README §13 environment separation). It uses the same Merchant API Surface
as milli.run (README §7).
"""

from llm_agent.agent import LLMAgent
from llm_agent.client import LLMClient, ScriptedLLMClient, AnthropicClient, OllamaClient

__all__ = ["LLMAgent", "LLMClient", "ScriptedLLMClient", "AnthropicClient", "OllamaClient"]
