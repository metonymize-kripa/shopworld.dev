"""Example: run and display a complete multi-step dialogue session.

This shows the details of the shopper simulator's dialogue policy and turn-by-turn
execution against a mock merchant.
"""

from __future__ import annotations

from shopper_sim.adapters.dialogue_policy import DialoguePolicy
from shopper_sim.adapters.mock_merchant import GoodMerchant
from shopper_sim.persona.library import persona_by_id
from shopper_sim.taxonomy.scenario_compiler import compile_family_scenario


def main() -> None:
    # 1. Compile a hard-core multistep scenario: 'order_editing' (editing/cancelling an order)
    scenario = compile_family_scenario("order_editing")
    print(f"Scenario: {scenario.title} ({scenario.scenario_id})")
    print(f"Goal Stack: {[g.description for g in scenario.goals]}")
    print(f"Factsheet: {scenario.factsheet.known_slots}")
    print("-" * 60)

    # 2. Select a persona
    persona = persona_by_id("anxious_gifter")
    seed = 42

    # 3. Connect to a mock merchant (GoodMerchant) and run the dialogue policy
    merchant = GoodMerchant(scenario)
    policy = DialoguePolicy(scenario, persona, merchant, seed)
    transcript = policy.run()

    # 4. Print the back-and-forth dialogue
    for i, turn in enumerate(transcript.turns):
        print(f"Turn {i+1}:")
        print(f"  🛒 Shopper (Persona: {persona.name}):")
        print(f"     \"{turn.shopper_utterance}\"")
        print(f"  🏪 Merchant (GoodMerchant):")
        print(f"     \"{turn.merchant_text}\"")
        print(f"  🔧 [Engine Info: Goal={turn.goal_id}, Outcome={turn.outcome.value}, Move={turn.classification.value}]")
        print()

    print(f"Dialogue Completed: {transcript.completed}")
    print(f"Total Turns: {transcript.total_turns}")
    print(f"Journey State established: {transcript.journey_state}")


if __name__ == "__main__":
    main()
