# Source notes

## Public Vending-Bench 2 page

Source: https://andonlabs.com/evals/vending-bench-2

Observed public details used by this local harness:

- Vending-Bench 2 measures AI model performance at running a simulated vending-machine business over long horizons.
- Models run the business over a year and are scored on bank account balance at the end.
- The benchmark uses a $500 starting balance.
- The business pays a $2 daily fee.
- A run terminates early if the model cannot pay the $2 daily fee for more than 10 consecutive days.
- Models can search for suppliers and contact them by email.
- Delivered products arrive at storage, and models use tools to move items between storage and machine.
- Customer sales depend on factors such as day of week, season, weather, and price.
- Vending-Bench 2 adds adversarial suppliers, negotiation, delivery delays, suppliers going out of business, customer complaints, clearer score criteria, note-taking, and reminders.
- The system prompt states the output-token cost as $100 per million output tokens.
- The system prompt states one tool call at a time and automatic context trimming.

## Original Vending-Bench paper

Source: https://arxiv.org/abs/2502.15840

Observed public details used by this local harness:

- The original Vending-Bench simulated customer purchases using price elasticity of demand.
- Per-item values include price elasticity, reference price, and base sales.
- Base sales are modified by day-of-week, monthly multipliers, and weather impact factors.
- Product variety affects demand; too many options are penalized.
- Final sales prediction uses random noise, rounding, and capping between zero and available inventory.
- Task-specific tools include email, inventory, balance, sub-agent-like physical operations, pricing, cash collection, and waiting for the next day.
- The benchmark uses simple agent looping with context management and memory tools.

## Local implementation choices

These details are not publicly specified by Andon Labs and are therefore local deterministic choices:

- Supplier names, prices, reliability, delivery-delay distributions, and negotiation curves.
- Item catalog and aliases.
- Exact sales equations and parameter values.
- Weather pseudo-randomness.
- Machine capacity abstraction.
- JSON action fallback format for Ollama models.
- Scripted baseline policy.

## Claim boundary

This project can reproduce a source-linked local benchmark protocol and can produce reproducible local evidence for Ollama models. It cannot reproduce official Andon Labs Vending-Bench 2 leaderboard numbers exactly unless the official environment, supplier simulator, hidden state, prompts, and run traces are provided.
