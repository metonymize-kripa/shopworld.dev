"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from shopper_sim.persona.library import all_personas, persona_by_id
from shopper_sim.taxonomy.scenario_compiler import (
    compile_family_scenario,
    compile_full_battery,
    default_context,
)


@pytest.fixture(scope="session")
def full_battery():
    return compile_full_battery()


@pytest.fixture(scope="session")
def personas():
    return all_personas()


@pytest.fixture
def loyal_regular():
    return persona_by_id("loyal_regular")


@pytest.fixture
def order_editing_scenario():
    return compile_family_scenario("order_editing", default_context())


@pytest.fixture
def return_flow_scenario():
    return compile_family_scenario("return_initiation", default_context())
