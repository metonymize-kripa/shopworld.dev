"""
Task generators — the train distribution.

Each generator is a function (rng) -> Task. It samples a world (products, the
user, addresses) and a goal, then builds the state-diff tests for that goal.
Because the tests are built from the SEEDED start state, the no-op labeler can
correctly tag which requirements measure real work vs. which are already-satisfied
guards.

Add a generator here and register it in REGISTRY to grow the distribution.
"""

from __future__ import annotations
import random

from commerce_rle.tasks.task import Task
from commerce_rle.env.evaluator import Test, EvalContext, State


# ── shared world-sampling helpers ────────────────────────────────────────────

CATEGORIES = ["cables", "audio", "kitchen", "books", "office"]
ADJECTIVES = ["basic", "premium", "compact", "heavy-duty", "wireless"]
NOUNS = {
    "cables": ["usb-c cable", "hdmi cable", "lightning cable"],
    "audio": ["earbuds", "headphones", "speaker"],
    "kitchen": ["kettle", "blender", "toaster"],
    "books": ["novel", "cookbook", "textbook"],
    "office": ["notebook", "pen set", "stapler"],
}
USER_ID = 100


def _sample_user_and_addresses() -> dict[str, list[tuple]]:
    # one user, two addresses, first is default
    return {
        "users": [(USER_ID, "Sam Rivera", "sam@example.com", 200.0)],
        "addresses": [
            (10, USER_ID, 1, "1 Main St"),    # default
            (11, USER_ID, 0, "2 Oak Ave"),
        ],
    }


def _sample_products(rng: random.Random, category: str, n: int,
                    start_id: int = 1) -> list[tuple]:
    rows = []
    for i in range(n):
        pid = start_id + i
        noun = rng.choice(NOUNS[category])
        title = f"{rng.choice(ADJECTIVES)} {noun}"
        price = round(rng.uniform(5, 40), 2)
        stock = rng.choice([0, 0, 1, 3, 5, 10])  # ~1/3 out of stock
        rating = round(rng.uniform(3.0, 5.0), 1)
        rows.append((pid, title, category, price, stock, rating))
    return rows


# ── generator 1: cheapest in-stock match, within budget ──────────────────────

def gen_cheapest_in_stock_buy(rng: random.Random) -> Task:
    category = rng.choice(["cables", "audio", "kitchen"])
    keyword = rng.choice(NOUNS[category])
    products = _sample_products(rng, category, n=6)

    # guarantee at least one in-stock product matching the keyword
    matches = [p for p in products if keyword in p[1] and p[4] > 0]
    if not matches:
        # force one in
        forced = (99, f"basic {keyword}", category,
                  round(rng.uniform(5, 14), 2), 3, 4.5)
        products.append(forced)

    seed = _sample_user_and_addresses()
    seed["products"] = products

    def build_tests(start: State) -> list[Test]:
        # compute the ground-truth target from the SEEDED start state
        in_stock_matches = [
            p for p in start["products"]
            if keyword in p["title"] and p["stock"] > 0
        ]
        target = min(in_stock_matches, key=lambda p: p["price"])
        target_id = target["id"]
        target_start_stock = target["stock"]

        def t_one_order(ctx: EvalContext):
            assert len(ctx.end["orders"]) == 1, \
                f"expected 1 order, got {len(ctx.end['orders'])}"

        def t_correct_product(ctx: EvalContext):
            o = ctx.end["orders"][0]
            assert o["product_id"] == target_id, \
                f"ordered {o['product_id']}, expected cheapest in-stock {target_id}"

        def t_qty_one(ctx: EvalContext):
            assert ctx.end["orders"][0]["qty"] == 1, "qty must be 1"

        def t_default_addr(ctx: EvalContext):
            assert ctx.end["orders"][0]["ship_address_id"] == 10, \
                "must ship to default address (id 10)"

        def t_stock_dec(ctx: EvalContext):
            end_p = {p["id"]: p for p in ctx.end["products"]}
            assert end_p[target_id]["stock"] == target_start_stock - 1, \
                "target stock not decremented by 1"

        def t_only_stock_changed(ctx: EvalContext):
            # delta-based: the only product field that may change is stock, and
            # only for the target row. Catches an agent that mutates price/title
            # or touches a different product's row.
            for pk, changes in ctx.modified("products").items():
                assert pk == target_id, \
                    f"product {pk} changed but only {target_id} should"
                assert set(changes) == {"stock"}, \
                    f"product {target_id} changed fields {set(changes)}, only 'stock' allowed"

        return [
            Test("exactly one order exists", t_one_order),
            Test(f"order is cheapest in-stock '{keyword}'", t_correct_product),
            Test("order quantity is 1", t_qty_one),
            Test("ships to default address", t_default_addr),
            Test("target stock decremented by 1", t_stock_dec),
            Test("only target product's stock field changed", t_only_stock_changed),
        ]

    return Task(
        task_id=f"cheapest_buy_{rng.randint(10**6, 10**7)}",
        instruction=(
            f"Buy exactly one unit of the cheapest in-stock '{keyword}' and "
            f"ship it to my default address."
        ),
        seed_rows=seed,
        context={"user_id": USER_ID},
        build_tests=build_tests,
        # field-precise scope: orders may change freely (new row), but in products
        # ONLY the stock field may move. Anything else is collateral damage.
        write_scope={"orders", "products.stock", "users.balance"},
    )


# ── generator 2: cart then checkout (multi-item) ─────────────────────────────

def gen_cart_checkout(rng: random.Random) -> Task:
    category = rng.choice(CATEGORIES)
    products = _sample_products(rng, category, n=8)
    in_stock = [p for p in products if p[4] > 0]
    while len(in_stock) < 2:
        products = _sample_products(rng, category, n=8)
        in_stock = [p for p in products if p[4] > 0]

    wanted = rng.sample(in_stock, 2)
    wanted_ids = sorted(p[0] for p in wanted)

    seed = _sample_user_and_addresses()
    seed["products"] = products

    def build_tests(start: State) -> list[Test]:
        def t_two_orders(ctx: EvalContext):
            assert len(ctx.end["orders"]) == 2, \
                f"expected 2 orders, got {len(ctx.end['orders'])}"

        def t_right_products(ctx: EvalContext):
            got = sorted(o["product_id"] for o in ctx.end["orders"])
            assert got == wanted_ids, f"ordered {got}, expected {wanted_ids}"

        def t_cart_emptied(ctx: EvalContext):
            assert len(ctx.end["cart_items"]) == 0, "cart should be empty after checkout"

        return [
            Test("exactly two orders exist", t_two_orders),
            Test("orders match the two requested products", t_right_products),
            Test("cart is empty after checkout", t_cart_emptied),
        ]

    titles = [p[1] for p in wanted]
    return Task(
        task_id=f"cart_checkout_{rng.randint(10**6, 10**7)}",
        instruction=(
            f"Add these two items to my cart and check out to my default "
            f"address: '{titles[0]}' and '{titles[1]}'."
        ),
        seed_rows=seed,
        context={"user_id": USER_ID, "wanted_product_ids": wanted_ids},
        build_tests=build_tests,
        write_scope={"orders", "products", "cart_items", "users.balance"},
    )


# ── generator 3: return an existing order ────────────────────────────────────

def gen_return_order(rng: random.Random) -> Task:
    category = rng.choice(CATEGORIES)
    products = _sample_products(rng, category, n=5)
    p = products[0]
    seed = _sample_user_and_addresses()
    seed["products"] = products
    # pre-existing delivered order to return
    seed["orders"] = [
        (1, USER_ID, p[0], 1, 10, p[3], "delivered"),
    ]

    def build_tests(start: State) -> list[Test]:
        start_stock = {pp["id"]: pp["stock"] for pp in start["products"]}

        def t_returned(ctx: EvalContext):
            o = next(o for o in ctx.end["orders"] if o["id"] == 1)
            assert o["status"] == "returned", "order 1 status should be 'returned'"

        def t_restocked(ctx: EvalContext):
            end_p = {pp["id"]: pp for pp in ctx.end["products"]}
            assert end_p[p[0]]["stock"] == start_stock[p[0]] + 1, \
                "returned item should be restocked (+1)"

        def t_no_new_orders(ctx: EvalContext):
            assert len(ctx.end["orders"]) == 1, "should not create new orders"

        return [
            Test("order 1 is marked returned", t_returned),
            Test("returned item is restocked", t_restocked),
            Test("no new orders created", t_no_new_orders),
        ]

    return Task(
        task_id=f"return_{rng.randint(10**6, 10**7)}",
        instruction="Return my most recent order.",
        seed_rows=seed,
        context={"user_id": USER_ID, "order_id": 1},
        build_tests=build_tests,
        write_scope={"orders", "products", "users.balance"},
    )


# ── generator 4: constrained buy (rating filter + distractors) ───────────────

def gen_constrained_buy(rng: random.Random) -> Task:
    category = rng.choice(["audio", "kitchen", "office"])
    keyword = rng.choice(NOUNS[category])
    min_rating = rng.choice([4.0, 4.5])
    products = _sample_products(rng, category, n=8)

    # ensure at least one in-stock match clears the rating bar, and at least one
    # in-stock match that is CHEAPER but below the bar (a distractor the agent
    # must reject).
    forced_good = (97, f"premium {keyword}", category,
                   round(rng.uniform(15, 30), 2), 4, round(rng.uniform(min_rating, 5.0), 1))
    forced_trap = (98, f"basic {keyword}", category,
                   round(rng.uniform(5, 12), 2), 5, round(rng.uniform(3.0, min_rating - 0.1), 1))
    products += [forced_good, forced_trap]

    seed = _sample_user_and_addresses()
    seed["products"] = products

    def build_tests(start: State) -> list[Test]:
        eligible = [
            p for p in start["products"]
            if keyword in p["title"] and p["stock"] > 0 and p["rating"] >= min_rating
        ]
        target = min(eligible, key=lambda p: p["price"])
        tid = target["id"]

        def t_one_order(ctx: EvalContext):
            assert len(ctx.end["orders"]) == 1, "expected exactly 1 order"

        def t_meets_rating(ctx: EvalContext):
            o = ctx.end["orders"][0]
            bought = {p["id"]: p for p in ctx.end["products"]}[o["product_id"]]
            assert bought["rating"] >= min_rating, \
                f"bought rating {bought['rating']} < required {min_rating}"

        def t_cheapest_eligible(ctx: EvalContext):
            assert ctx.end["orders"][0]["product_id"] == tid, \
                f"did not buy cheapest eligible product {tid}"

        return [
            Test("exactly one order exists", t_one_order),
            Test(f"bought item rating >= {min_rating}", t_meets_rating),
            Test("bought cheapest rating-eligible item", t_cheapest_eligible),
        ]

    return Task(
        task_id=f"constrained_buy_{rng.randint(10**6, 10**7)}",
        instruction=(
            f"Buy the cheapest in-stock '{keyword}' that has a rating of at least "
            f"{min_rating} stars. Ship to my default address."
        ),
        seed_rows=seed,
        context={"user_id": USER_ID, "min_rating": min_rating},
        build_tests=build_tests,
        write_scope={"orders", "products.stock", "users.balance"},
    )


# ── generator 5: budget-enforced buy ─────────────────────────────────────────

def gen_budget_enforced_buy(rng: random.Random) -> Task:
    category = rng.choice(["audio", "kitchen"])
    keyword = rng.choice(NOUNS[category])
    products = _sample_products(rng, category, n=6)
    # an affordable in-stock match and a pricier in-stock match
    cheap = (96, f"compact {keyword}", category, round(rng.uniform(8, 18), 2), 4, 4.6)
    pricey = (95, f"premium {keyword}", category, round(rng.uniform(40, 80), 2), 4, 4.8)
    products += [cheap, pricey]

    seed = _sample_user_and_addresses()
    seed["products"] = products
    # balance covers the cheap one but NOT the pricey one
    budget = round(cheap[3] + rng.uniform(2, 8), 2)
    seed["users"] = [(USER_ID, "Sam Rivera", "sam@example.com", budget)]

    def build_tests(start: State) -> list[Test]:
        affordable = [
            p for p in start["products"]
            if keyword in p["title"] and p["stock"] > 0 and p["price"] <= budget
        ]
        target = min(affordable, key=lambda p: p["price"])
        tid = target["id"]

        def t_one_order(ctx: EvalContext):
            assert len(ctx.end["orders"]) == 1, "expected exactly 1 order"

        def t_affordable(ctx: EvalContext):
            o = ctx.end["orders"][0]
            assert o["total"] <= budget, f"order total {o['total']} over budget {budget}"

        def t_balance_debited(ctx: EvalContext):
            u = {p["id"]: p for p in ctx.end["users"]}[USER_ID]
            o = ctx.end["orders"][0]
            assert abs(u["balance"] - (budget - o["total"])) < 0.01, \
                "balance not debited by order total"

        def t_picked_target(ctx: EvalContext):
            assert ctx.end["orders"][0]["product_id"] == tid, \
                f"did not buy cheapest affordable product {tid}"

        return [
            Test("exactly one order exists", t_one_order),
            Test("order is within budget", t_affordable),
            Test("balance debited by order total", t_balance_debited),
            Test("bought cheapest affordable item", t_picked_target),
        ]

    return Task(
        task_id=f"budget_buy_{rng.randint(10**6, 10**7)}",
        instruction=(
            f"I have a limited balance. Buy the cheapest in-stock '{keyword}' I can "
            f"afford and ship to my default address."
        ),
        seed_rows=seed,
        context={"user_id": USER_ID, "budget": budget},
        build_tests=build_tests,
        write_scope={"orders", "products.stock", "users.balance"},
    )


# ── generator 6: cart-edit to a target state ─────────────────────────────────

def gen_cart_edit_to_target(rng: random.Random) -> Task:
    category = rng.choice(CATEGORIES)
    products = _sample_products(rng, category, n=8)
    in_stock = [p for p in products if p[4] >= 3]
    while len(in_stock) < 3:
        products = _sample_products(rng, category, n=8)
        in_stock = [p for p in products if p[4] >= 3]

    keep, drop, bump = rng.sample(in_stock, 3)
    # pre-seed a cart that has `drop` (to be removed), `bump` at qty 1 (to be qty 3),
    # and is missing `keep` (to be added at qty 1).
    seed = _sample_user_and_addresses()
    seed["products"] = products
    seed["cart_items"] = [
        (1, USER_ID, drop[0], 2),
        (2, USER_ID, bump[0], 1),
    ]
    target = {keep[0]: 1, bump[0]: 3}

    def build_tests(start: State) -> list[Test]:
        def t_target_cart(ctx: EvalContext):
            cart = {c["product_id"]: c["qty"] for c in ctx.end["cart_items"]
                    if c["user_id"] == USER_ID}
            assert cart == target, f"cart {cart} != target {target}"

        def t_no_orders(ctx: EvalContext):
            assert len(ctx.end["orders"]) == 0, "should not check out, only edit cart"

        return [
            Test("cart matches the requested target exactly", t_target_cart),
            Test("no orders placed (edit only)", t_no_orders),
        ]

    return Task(
        task_id=f"cart_edit_{rng.randint(10**6, 10**7)}",
        instruction=(
            f"Update my cart so it contains exactly: 1x '{keep[1]}' and 3x "
            f"'{bump[1]}'. Remove anything else. Do not check out."
        ),
        seed_rows=seed,
        context={"user_id": USER_ID, "target": target},
        build_tests=build_tests,
        write_scope={"cart_items"},
    )


# ── generator 7: reorder last (read history, repurchase) ─────────────────────

def gen_reorder_last(rng: random.Random) -> Task:
    category = rng.choice(CATEGORIES)
    products = _sample_products(rng, category, n=5)
    in_stock = [p for p in products if p[4] > 0]
    if not in_stock:
        forced = (94, f"basic {rng.choice(NOUNS[category])}", category,
                  round(rng.uniform(8, 25), 2), 5, 4.5)
        products.append(forced)
        in_stock = [forced]
    prev = in_stock[0]
    seed = _sample_user_and_addresses()
    seed["products"] = products
    seed["orders"] = [(1, USER_ID, prev[0], 1, 10, prev[3], "delivered")]

    def build_tests(start: State) -> list[Test]:
        prev_pid = start["orders"][0]["product_id"]

        def t_two_orders(ctx: EvalContext):
            assert len(ctx.end["orders"]) == 2, "expected a new order in addition to history"

        def t_same_product(ctx: EvalContext):
            new = [o for o in ctx.end["orders"] if o["id"] != 1]
            assert len(new) == 1 and new[0]["product_id"] == prev_pid, \
                "new order is not the previously ordered product"

        return [
            Test("a new order was added", t_two_orders),
            Test("new order repurchases the previous product", t_same_product),
        ]

    return Task(
        task_id=f"reorder_{rng.randint(10**6, 10**7)}",
        instruction="Order the same item I bought last time again, to my default address.",
        seed_rows=seed,
        context={"user_id": USER_ID},
        build_tests=build_tests,
        write_scope={"orders", "products.stock", "users.balance"},
    )


# ── generator 8: wishlist → cart purchase ────────────────────────────────────

def gen_wishlist_to_cart(rng: random.Random) -> Task:
    category = rng.choice(CATEGORIES)
    products = _sample_products(rng, category, n=6)
    in_stock = [p for p in products if p[4] > 0]
    while len(in_stock) < 1:
        products = _sample_products(rng, category, n=6)
        in_stock = [p for p in products if p[4] > 0]
    saved = in_stock[0]
    seed = _sample_user_and_addresses()
    seed["products"] = products
    seed["wishlist"] = [(1, USER_ID, saved[0])]

    def build_tests(start: State) -> list[Test]:
        saved_pid = start["wishlist"][0]["product_id"]

        def t_ordered_saved(ctx: EvalContext):
            assert any(o["product_id"] == saved_pid for o in ctx.end["orders"]), \
                "wishlisted item was not ordered"

        def t_one_order(ctx: EvalContext):
            assert len(ctx.end["orders"]) == 1, "expected exactly one order"

        return [
            Test("the wishlisted item was ordered", t_ordered_saved),
            Test("exactly one order exists", t_one_order),
        ]

    return Task(
        task_id=f"wishlist_buy_{rng.randint(10**6, 10**7)}",
        instruction="Buy the item from my wishlist and ship it to my default address.",
        seed_rows=seed,
        context={"user_id": USER_ID},
        build_tests=build_tests,
        # wishlist may or may not be cleared; we allow it to change but don't require it
        write_scope={"orders", "products.stock", "users.balance", "wishlist"},
    )


# ── generator 9: REFUSAL — out of stock everywhere ───────────────────────────

def gen_refuse_out_of_stock(rng: random.Random) -> Task:
    category = rng.choice(["audio", "kitchen", "office"])
    keyword = rng.choice(NOUNS[category])
    # every matching product is out of stock; non-matching products are in stock
    # (distractors the agent must not substitute).
    products = []
    for i in range(6):
        match = i < 3
        title = f"{rng.choice(ADJECTIVES)} {keyword}" if match else \
                f"{rng.choice(ADJECTIVES)} {rng.choice([n for n in NOUNS[category] if n != keyword])}"
        stock = 0 if match else rng.choice([3, 5])
        products.append((i + 1, title, category, round(rng.uniform(5, 30), 2), stock,
                         round(rng.uniform(3.5, 5.0), 1)))
    seed = _sample_user_and_addresses()
    seed["products"] = products

    def build_tests(start: State) -> list[Test]:
        def t_no_order(ctx: EvalContext):
            assert len(ctx.end["orders"]) == 0, \
                "placed an order though the requested item was out of stock"

        def t_no_substitute(ctx: EvalContext):
            # also must not buy a different product as a "close enough" sub
            assert len(ctx.end["orders"]) == 0, "must not substitute a different item"

        return [
            Test("no order placed for the out-of-stock item", t_no_order),
            Test("did not substitute a different product", t_no_substitute),
        ]

    return Task(
        task_id=f"refuse_oos_{rng.randint(10**6, 10**7)}",
        instruction=(
            f"Buy one in-stock '{keyword}' and ship to my default address. "
            f"If none is available, do not order anything."
        ),
        seed_rows=seed,
        context={"user_id": USER_ID},
        build_tests=build_tests,
        write_scope=set(),          # nothing may change
        expects_refusal=True,
    )


# ── generator 10: REFUSAL — all matches over budget ──────────────────────────

def gen_refuse_over_budget(rng: random.Random) -> Task:
    category = rng.choice(["audio", "kitchen"])
    keyword = rng.choice(NOUNS[category])
    products = _sample_products(rng, category, n=4)
    # in-stock matches, but all priced above the user's balance
    pricey = [
        (90 + i, f"{rng.choice(ADJECTIVES)} {keyword}", category,
         round(rng.uniform(50, 90), 2), 4, 4.5)
        for i in range(3)
    ]
    products += pricey
    seed = _sample_user_and_addresses()
    seed["products"] = products
    seed["users"] = [(USER_ID, "Sam Rivera", "sam@example.com", round(rng.uniform(10, 30), 2))]

    def build_tests(start: State) -> list[Test]:
        def t_no_order(ctx: EvalContext):
            assert len(ctx.end["orders"]) == 0, \
                "placed an order though all matches exceed the balance"

        def t_balance_intact(ctx: EvalContext):
            u = {p["id"]: p for p in ctx.end["users"]}[USER_ID]
            su = {p["id"]: p for p in ctx.start["users"]}[USER_ID]
            assert u["balance"] == su["balance"], "balance changed despite no valid purchase"

        return [
            Test("no order placed when all matches are unaffordable", t_no_order),
            Test("account balance is unchanged", t_balance_intact),
        ]

    return Task(
        task_id=f"refuse_budget_{rng.randint(10**6, 10**7)}",
        instruction=(
            f"Buy an in-stock '{keyword}' within my available balance, shipped to my "
            f"default address. If nothing is affordable, do not order anything."
        ),
        seed_rows=seed,
        context={"user_id": USER_ID},
        build_tests=build_tests,
        write_scope=set(),
        expects_refusal=True,
    )


# ── generator 11: COMPOUND — buy one, wishlist another ───────────────────────

def gen_compound_buy_and_wishlist(rng: random.Random) -> Task:
    category = rng.choice(CATEGORIES)
    products = _sample_products(rng, category, n=8)
    # need two in-stock items with DISTINCT titles (the instruction references
    # them by title, so a collision would make them ambiguous).
    in_stock = [p for p in products if p[4] > 0]
    distinct = {}
    for p in in_stock:
        distinct.setdefault(p[1], p)
    while len(distinct) < 2:
        products = _sample_products(rng, category, n=8)
        in_stock = [p for p in products if p[4] > 0]
        distinct = {}
        for p in in_stock:
            distinct.setdefault(p[1], p)
    buy_it, save_it = rng.sample(list(distinct.values()), 2)
    seed = _sample_user_and_addresses()
    seed["products"] = products

    def build_tests(start: State) -> list[Test]:
        def t_bought(ctx: EvalContext):
            assert any(o["product_id"] == buy_it[0] for o in ctx.end["orders"]), \
                "did not buy the item to purchase"

        def t_one_order(ctx: EvalContext):
            assert len(ctx.end["orders"]) == 1, "expected exactly one order"

        def t_wishlisted(ctx: EvalContext):
            assert any(w["product_id"] == save_it[0] for w in ctx.end["wishlist"]), \
                "did not wishlist the second item"

        def t_not_bought_wishlist(ctx: EvalContext):
            assert not any(o["product_id"] == save_it[0] for o in ctx.end["orders"]), \
                "wishlisted item should not be purchased"

        return [
            Test("bought the first item", t_bought),
            Test("exactly one order exists", t_one_order),
            Test("wishlisted the second item", t_wishlisted),
            Test("did not buy the wishlisted item", t_not_bought_wishlist),
        ]

    return Task(
        task_id=f"compound_buy_wish_{rng.randint(10**6, 10**7)}",
        instruction=(
            f"Buy 1x '{buy_it[1]}' shipped to my default address, and separately "
            f"add '{save_it[1]}' to my wishlist for later."
        ),
        seed_rows=seed,
        context={"user_id": USER_ID, "buy_id": buy_it[0], "wishlist_id": save_it[0]},
        build_tests=build_tests,
        write_scope={"orders", "products.stock", "users.balance", "wishlist"},
    )


# ── generator 12: COMPOUND — return an order, buy a replacement ───────────────

def gen_compound_return_and_rebuy(rng: random.Random) -> Task:
    category = rng.choice(CATEGORIES)
    products = _sample_products(rng, category, n=6)
    in_stock = [p for p in products if p[4] > 0]
    while len(in_stock) < 1:
        products = _sample_products(rng, category, n=6)
        in_stock = [p for p in products if p[4] > 0]
    old = products[0]
    replacement = in_stock[0] if in_stock[0][0] != old[0] else (
        in_stock[1] if len(in_stock) > 1 else in_stock[0]
    )
    seed = _sample_user_and_addresses()
    seed["products"] = products
    seed["orders"] = [(1, USER_ID, old[0], 1, 10, old[3], "delivered")]

    def build_tests(start: State) -> list[Test]:
        def t_returned(ctx: EvalContext):
            o = next(o for o in ctx.end["orders"] if o["id"] == 1)
            assert o["status"] == "returned", "original order not returned"

        def t_replacement_bought(ctx: EvalContext):
            new = [o for o in ctx.end["orders"]
                   if o["id"] != 1 and o["product_id"] == replacement[0]]
            assert len(new) >= 1, "replacement was not purchased"

        return [
            Test("original order is returned", t_returned),
            Test("replacement product is purchased", t_replacement_bought),
        ]

    return Task(
        task_id=f"compound_return_rebuy_{rng.randint(10**6, 10**7)}",
        instruction=(
            f"Return my most recent order, then buy '{replacement[1]}' as a "
            f"replacement, shipped to my default address."
        ),
        seed_rows=seed,
        context={"user_id": USER_ID, "order_id": 1, "replacement_id": replacement[0]},
        build_tests=build_tests,
        write_scope={"orders", "products.stock", "users.balance"},
    )


REGISTRY = {
    "cheapest_in_stock_buy": gen_cheapest_in_stock_buy,
    "cart_checkout": gen_cart_checkout,
    "return_order": gen_return_order,
    "constrained_buy": gen_constrained_buy,
    "budget_enforced_buy": gen_budget_enforced_buy,
    "cart_edit_to_target": gen_cart_edit_to_target,
    "reorder_last": gen_reorder_last,
    "wishlist_to_cart": gen_wishlist_to_cart,
    "refuse_out_of_stock": gen_refuse_out_of_stock,
    "refuse_over_budget": gen_refuse_over_budget,
    "compound_buy_and_wishlist": gen_compound_buy_and_wishlist,
    "compound_return_and_rebuy": gen_compound_return_and_rebuy,
}

# generators whose correct behavior is to make NO database change
REFUSAL_GENERATORS = {"refuse_out_of_stock", "refuse_over_budget"}


def sample_task(rng: random.Random, name: str | None = None) -> Task:
    """Sample one task. If name is None, pick a generator uniformly at random."""
    if name is None:
        name = rng.choice(list(REGISTRY))
    return REGISTRY[name](rng)


def make_dataset(n: int, seed: int = 0, name: str | None = None) -> list[Task]:
    """Build a fixed dataset of n tasks with a deterministic seed."""
    rng = random.Random(seed)
    return [sample_task(rng, name) for _ in range(n)]


def make_scenarios(
    n_scenarios: int, variants_per_scenario: int = 3, seed: int = 0,
    name: str | None = None,
) -> list[Task]:
    """Build tasks grouped into scenarios for Scenario Goal Completion (SGC).

    Each scenario draws `variants_per_scenario` tasks from the SAME generator —
    the AppWorld pattern of one goal under varied requirements / start states.
    All variants in a scenario share a scenario_id. A scenario counts as solved
    only if the agent gets TGC on every variant (see evaluator.scenario_goal_completion).

    Returns a flat list of tasks; group by `task.scenario_id` to score SGC.
    """
    rng = random.Random(seed)
    tasks: list[Task] = []
    for s in range(n_scenarios):
        gen_name = name or rng.choice(list(REGISTRY))
        sid = f"{gen_name}__scenario_{s}"
        for _ in range(variants_per_scenario):
            t = REGISTRY[gen_name](rng)
            t.scenario_id = sid
            tasks.append(t)
    return tasks


def make_stratified_scenarios(
    variants_per_scenario: int = 3, scenarios_per_family: int = 1, seed: int = 0,
) -> list[Task]:
    """Guarantee coverage: at least `scenarios_per_family` scenarios from EVERY
    generator family. Use this for a benchmark set where you want the full breadth
    represented deterministically rather than left to random sampling.
    """
    rng = random.Random(seed)
    tasks: list[Task] = []
    s = 0
    for gen_name in REGISTRY:
        for _ in range(scenarios_per_family):
            sid = f"{gen_name}__scenario_{s}"
            for _ in range(variants_per_scenario):
                t = REGISTRY[gen_name](rng)
                t.scenario_id = sid
                tasks.append(t)
            s += 1
    return tasks
