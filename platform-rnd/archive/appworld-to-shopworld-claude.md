I'll start by finding the actual AppWorld repository, since I need to see what's really in it before recommending what to cut.Let me clone the actual repo and inspect its structure so my recommendation is grounded in what's really there, not a guess.Now let me look at the key files that define the world model, the environment/task/evaluator core, and how apps are structured — that's what determines what's reusable for a Shopify RLE.The `.bundle` files are LFS pointers (131 bytes — not pulled). They contain the actual app implementations, the DB models, the tasks, and the tests. That's the part you'd gut and replace. Let me confirm they're pointers and look at the environment/evaluator architecture, since that's the reusable RLE core.I have enough to map the architecture precisely. Let me look at how a task and the evaluator are structured, and check the apps lib (the framework that all 9 apps are built on — this is the reusable scaffold for building a Shopify app).I now have a complete enough picture of the architecture to give you the answer. Let me check one more thing — whether there's any RL/reward harness already, or whether the evaluator's pass/fail unit tests are the only reward signal — since that's the crux of repurposing this into an RLE.I have everything I need. The `grep` confirms there's no RL harness — `environment.py` mentions "reward" only incidentally. The reusable core is the sandbox primitives (`execute`, `save_state`/`load_state`, `evaluate`), and the reward signal is the evaluator's state-based unit tests. Everything app-specific lives in the encrypted bundles you'll replace.

**Problem.** AppWorld is a benchmark, not a trainer. It ships 9 fixed apps (Amazon, Spotify, etc.) across 457 APIs, plus 750 frozen tasks with held-out test sets. None of that is Shopify, and the test-set secrecy that makes it a good benchmark is dead weight for an RLE you control end to end. You want the sandbox engine and the grader, not the world.

**Why.** The repo cleanly separates two things: a plain-text execution/eval *engine* (`src/appworld/`, Apache-2.0) and encrypted `.bundle` payloads (app code, DB models, tasks, unit tests) that hold all the domain content. The bundles are LFS pointers — 131 bytes on a fresh clone, the real ~194KB apps blob lives behind `git lfs pull`. So "eliminate everything but the core" maps almost 1:1 onto "keep the engine, drop the bundles."

**Pattern.** The engine gives you exactly the four primitives an RLE needs, already built:

- `environment.execute(code)` — sandboxed Python REPL (IPython embed + `SafetyGuard`), the action interface. This is your agent's hands.
- `save_state` / `load_state` — snapshot and reset the world per episode. This is your `env.reset()`.
- `evaluate()` → `TestTracker` with `success: bool` and per-requirement pass/fail. This is your reward. AppWorld's "collateral damage" tests (did the agent break unrelated state?) are a gift — they're shaped reward for free.
- The `apps/lib/` framework (ORM, API callers, auth, pagination, datetime, factories) — the scaffold every app is built on. You rebuild Shopify *on this*, not from scratch.

Luna (andon labs) runs a real vending business; failure costs real money. AppWorld's value is letting you grind the same loop with zero real-world cost before you put a dollar of someone's revenue at risk.

**What to keep.**

- `src/appworld/` engine: `environment.py`, `task.py`, `evaluator.py`, `requester.py`, `api_docs.py`, all of `common/`, and `apps/lib/` (the app-building framework — load-bearing, keep intact).
- `serve/` including `_mcp.py` — the MCP server lets a tool-calling agent hit your APIs over a standard protocol. Keep it; it's how you'll wire any model in.
- `generate/code/` — the task/solution/docstring generators. This is the actual engine for *minting training tasks at scale*. Most valuable non-obvious asset in the repo.

**What to delete.**

- `src/appworld/.source/*.bundle` and `generate/.source/*.bundle` — the 9 apps, their DB models, the 750 tasks, the unit tests. All replaced by Shopify.
- `experiments/` except as reference — `simplified/react_code_agent.py` and `function_calling_agent.py` are worth reading as baseline agent loops, then discarding. `legacy/` goes entirely.
- `leaderboard.py`, `verify.py`, `download.py`, the test-set encryption/secrecy machinery (`common/crypto.py` if only used for bundle sealing). You own the data; sanctity is irrelevant.
- `notebooks/`, `guides/`, `images/`, leaderboard configs.

**What to build (the Shopify layer that slots into `apps/lib/`).** Two paths, and they differ in fidelity vs. effort:

- *Simulated Shopify app* — model Products, Orders, Customers, Inventory, Discounts, Fulfillment as ORM tables under `apps/lib/models/`, expose Shopify-shaped REST/GraphQL Admin API endpoints via the API caller framework. High effort, but gives you `save_state`/`load_state` and deterministic resets — which real Shopify will never give you.
- *Live Shopify dev store* via the real Admin API + a development store. Zero modeling, real fidelity, but no cheap reset and no free reward — you'd have to write evaluators against live state. Risky for high-volume RL.

The right answer is simulate first, then validate on a live dev store. The simulated app is what makes this an *RLE* rather than just an agent harness.

**The reward is the moat.** AppWorld's evaluator checks task success *and* unexpected side effects. For a store agent leased on % of revenue, your reward function is the product: it has to encode "fulfilled the order" AND "didn't refund the wrong customer, didn't tank margin, didn't oversell inventory." Port `evaluator.py`'s state-based + collateral-damage test structure directly; write Shopify requirement-tests in the same shape. Tasks become: restock, run a promo, handle a return, answer a customer, reprice for margin — each with setup state, a solution, and pass/fail asserts.

**TL;DR.** Keep `src/appworld/` (engine + `apps/lib/` + `serve/_mcp.py`) and `generate/code/`. Delete every `.bundle`, `experiments/legacy/`, and the leaderboard/test-secrecy machinery. Build a simulated Shopify app on `apps/lib/`, write Shopify tasks + state-based evaluators in the existing shape, and the engine's `execute`/`save_state`/`evaluate` loop *is* your RLE.

---

Want me to produce the concrete deletion+keep manifest as a script (a `git rm` + directory-prune list you can run against your fork), or scaffold the empty Shopify app module against `apps/lib/` so you can see where Products/Orders/Inventory models and API endpoints plug in?