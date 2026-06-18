# Amazon Simulator Toggle for ShopWorld

## Goal
Create an Amazon e-commerce simulator app using AppWorld's `apps/lib/` framework, enabling agents to be tested against both Shopify and Amazon environments.

## Why This Matters
- **Cross-platform agent testing**: Verify agents work across different e-commerce APIs
- **Competitive scenarios**: Simulate multi-channel selling (Shopify store + Amazon marketplace)
- **Migration scenarios**: Test inventory/order sync between platforms
- **Arbitrage detection**: Train agents to spot opportunities across marketplaces

## Salvage from AppWorld

### 1. Copy the Framework (from `/tmp/appworld-explore/`)

**Keep and port to shopworld:**
```
src/appworld/apps/lib/
  ├── models/
  │   ├── db.py          → shopworld/apps/lib/db.py
  │   ├── orm.py         → shopworld/apps/lib/orm.py
  │   └── filter_sort.py → shopworld/apps/lib/filter_sort.py
  ├── apis/
  │   ├── callers.py     → shopworld/apps/lib/api_callers.py
  │   ├── authentication.py → shopworld/apps/lib/auth.py
  │   └── pagination.py  → shopworld/apps/lib/pagination.py
  └── factories/         → shopworld/apps/lib/factories/
```

**Core runtime to port:**
```
src/appworld/environment.py    → shopworld/environment.py
src/appworld/task.py           → shopworld/task.py
src/appworld/evaluator.py      → shopworld/evaluator.py
src/appworld/serve/_mcp.py     → shopworld/serve/mcp.py
```

### 2. Build Amazon Simulator App

**File structure:**
```
src/shopworld/apps/amazon_simulator/
├── __init__.py
├── design.yaml              # API design spec
├── info.toml               # App metadata
├── models.py               # SQLModel tables
├── factories.py            # Test data generators
├── apis.py                 # FastAPI endpoints
├── responses.py            # Pydantic response types
├── base.db                 # SQLite seed database
└── tests.py                # API unit tests
```

**Core Models (inferred from AppWorld patterns):**
```python
# models.py
@SQLModel.register("Product")
class Product(SQLModel, table=True):
    table_name: ClassVar[str] = "products"
    id: int | None = Field(None, primary_key=True)
    asin: str = Field(..., description="Amazon Standard Identification Number")
    title: str = Field(..., description="Product title")
    price: float = Field(..., description="Current price")
    currency: str = Field(default="USD")
    stock_quantity: int = Field(default=0)
    category: str = Field(...)
    seller_id: int = Field(..., foreign_key="sellers.id")
    created_at: datetime = Field(default_factory=DateTime.now)
    
    has_one: ClassVar[tuple[str, ...]] = ("seller",)
    has_many: ClassVar[tuple[str, ...]] = ("reviews", "order_items")
    
    @property
    def computed_search_text(self) -> str:
        return f"{self.title} {self.category}"

@SQLModel.register("Order")
class Order(SQLModel, table=True):
    table_name: ClassVar[str] = "orders"
    id: int | None = Field(None, primary_key=True)
    amazon_order_id: str = Field(...)
    buyer_id: int = Field(..., foreign_key="buyers.id")
    status: str = Field(default="pending")  # pending, shipped, delivered, cancelled
    total_amount: float = Field(...)
    shipping_address: str = Field(...)
    created_at: datetime = Field(default_factory=DateTime.now)
    
    has_one: ClassVar[tuple[str, ...]] = ("buyer",)
    has_many: ClassVar[tuple[str, ...]] = ("items",)
```

**Key APIs to implement:**
```python
# apis.py
@app.get("/products/search")
def search_products(
    query: str = Query(..., description="Search query"),
    category: str | None = Query(None),
    min_price: float | None = Query(None),
    max_price: float | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> ProductSearchResponse:
    """Search for products on Amazon."""
    pass

@app.get("/products/{asin}")
def get_product(asin: str) -> ProductResponse:
    """Get detailed product information by ASIN."""
    pass

@app.post("/cart/items")
def add_to_cart(
    asin: str = Body(...),
    quantity: int = Body(..., ge=1),
    buyer_token: str = Header(...),
) -> CartResponse:
    """Add an item to the buyer's cart."""
    pass

@app.post("/orders")
def create_order(
    shipping_address: str = Body(...),
    payment_method_id: int = Body(...),
    buyer_token: str = Header(...),
) -> OrderResponse:
    """Place an order from the cart contents."""
    pass

@app.get("/orders/{order_id}")
def get_order(
    order_id: int,
    buyer_token: str = Header(...),
) -> OrderResponse:
    """Get order details."""
    pass

@app.patch("/orders/{order_id}/cancel")
def cancel_order(
    order_id: int,
    reason: str = Body(...),
    buyer_token: str = Header(...),
) -> CancelResponse:
    """Cancel an existing order."""
    pass
```

### 3. Toggle Mechanism

**Task-level app selection:**
```python
# In task specification
task = ShopWorldTask(
    task_id="cross_platform_001",
    instruction="Sync inventory between Shopify and Amazon",
    allowed_apps=["shopify_admin", "amazon_simulator"],  # Toggle here
    initial_state_path="...",
)
```

**Agent capability matrix:**
```yaml
# experiments/configs/agent_capabilities.yaml
agents:
  shopify_only:
    allowed_apps: ["shopify_admin", "suppliers", "customers"]
  
  multi_platform:
    allowed_apps: ["shopify_admin", "amazon_simulator", "suppliers"]
  
  amazon_only:
    allowed_apps: ["amazon_simulator", "customers"]
```

### 4. Multi-App Scenarios

**Scenario 1: Inventory Sync**
```
Task: Keep Shopify and Amazon inventory in sync
- Agent monitors Shopify inventory levels
- Updates Amazon listings when stock changes
- Handles "reserved" inventory across platforms
- Prevents overselling
```

**Scenario 2: Price Monitoring**
```
Task: Monitor competitor prices on Amazon
- Search Amazon for similar products
- Compare prices with Shopify store
- Suggest price adjustments
- Maintain margin targets
```

**Scenario 3: Order Routing**
```
Task: Route orders to optimal fulfillment channel
- Check inventory on both platforms
- Compare shipping costs
- Select best fulfillment option
- Update both systems
```

## Implementation Steps (Gradual Approach)

### Phase 1: Staging Area Setup ✅

Created `/platform-rnd/amazon_from_appworld/` as a **modification sandbox**:

```
amazon_from_appworld/
├── apis/           # authentication.py, callers.py, pagination.py, etc.
├── models/         # db.py, orm.py, filter_sort.py, users.py
├── factories/      # Test data generators
├── responses/      # Response wrappers
├── common/         # safety_guard.py, datetime.py
└── core_runtime/   # environment.py, task.py, evaluator.py
```

**Commands used:**
```bash
# Create staging area
mkdir -p /Users/kripar/Documents/coding/shopworld.dev/platform-rnd/amazon_from_appworld

# Copy framework (lib/)
cp -r /tmp/appworld-explore/src/appworld/apps/lib/* \
   /Users/kripar/Documents/coding/shopworld.dev/platform-rnd/amazon_from_appworld/

# Copy core runtime
mkdir -p /Users/kripar/Documents/coding/shopworld.dev/platform-rnd/amazon_from_appworld/core_runtime
cp /tmp/appworld-explore/src/appworld/environment.py \
   /tmp/appworld-explore/src/appworld/task.py \
   /tmp/appworld-explore/src/appworld/evaluator.py \
   /Users/kripar/Documents/coding/shopworld.dev/platform-rnd/amazon_from_appworld/core_runtime/

# Copy common utilities
mkdir -p /Users/kripar/Documents/coding/shopworld.dev/platform-rnd/amazon_from_appworld/common
cp /tmp/appworld-explore/src/appworld/common/safety_guard.py \
   /tmp/appworld-explore/src/appworld/common/datetime.py \
   /Users/kripar/Documents/coding/shopworld.dev/platform-rnd/amazon_from_appworld/common/
```

### Phase 2: Audit & Adapt Framework

Before moving files to `shopworld-platform/`:

1. **Compare `models/orm.py`** with existing `shopworld/apps/lib/` — note differences in relationship patterns
2. **Check `models/db.py`** — verify SQLModel compatibility with Shopify's existing models
3. **Review `apis/`** — ensure patterns align with Shopify's GraphQL approach or plan REST coexistence

### Phase 3: Create Amazon Simulator

Build in `shopworld-platform/src/shopworld/apps/amazon_simulator/`:

```python
# models.py — with prefixed table names
__tablename__ = "amazon_products"  # NOT "products"

# apis.py — FastAPI endpoints
@app.get("/products/search")
def search_products(...) -> ProductSearchResponse:
```

### Phase 4: Integration

1. **Add toggle in task config** (allowed_apps list)
2. **Write cross-platform tasks** (inventory sync, price arbitrage)
3. **Test agent performance** across single vs multi-app scenarios

## Staging Area Structure

Files recovered from AppWorld are staged at `/platform-rnd/amazon_from_appworld/` for review and modification before integration:

### Framework Files (from `apps/lib/`)

| Staged File | Purpose | Shopify Check |
|-------------|---------|---------------|
| `models/db.py` | Database connection/session mgmt | Compare with existing `shopworld/apps/lib/db.py` |
| `models/orm.py` | SQLModel base with relationships | Check `has_one`/`has_many` vs `Relationship()` patterns |
| `models/filter_sort.py` | Query filtering utilities | Verify compatible with Shopify queries |
| `models/users.py` | User model base | May conflict with Shopify's Customer model |
| `apis/callers.py` | API request wrappers | REST-focused; needs GraphQL adapter? |
| `apis/authentication.py` | Auth patterns | Shopify uses OAuth scopes — different model |
| `apis/pagination.py` | Cursor/page pagination | May overlap with `graphql_api/pagination.py` |
| `factories/` | Test data generators | Reusable for Amazon seed data |
| `responses/` | Response wrappers | FastAPI-specific |

### Core Runtime Files

| Staged File | Purpose | Integration Risk |
|-------------|---------|------------------|
| `core_runtime/environment.py` | AppWorld environment | High — may conflict with ShopWorld's task runner |
| `core_runtime/task.py` | Task definition base | Medium — `allowed_apps` toggle needs coordination |
| `core_runtime/evaluator.py` | Evaluation/scoring | High — ShopWorld likely has its own |

### Next Steps for Staged Files

1. **Audit each file** against existing `shopworld-platform` code
2. **Modify in staging** to support prefixed table names (`amazon_*`)
3. **Copy selectively** — only files that add new capability
4. **Delete staging copies** once integrated (or keep as reference)

## Architectural Separation & Precautions

### Database Isolation

To prevent conflicts with the Shopify simulator, Amazon models **must** use prefixed table names:

```python
# models.py — Amazon-specific table naming
class Product(SQLModel, table=True):
    __tablename__ = "amazon_products"  # NOT "products"
    # ...

class Order(SQLModel, table=True):
    __tablename__ = "amazon_orders"    # NOT "orders"
    # ...

class Seller(SQLModel, table=True):
    __tablename__ = "amazon_sellers"
    # ...
```

**Why**: Shopify already owns `products`, `orders`, `customers` tables. Shared table names would cause immediate collisions.

### Framework Compatibility Check

Before porting AppWorld's `apps/lib/`:

1. **Audit existing `shopworld/apps/lib/`** — Check if db.py/orm.py already support the patterns Shopify GraphQL needs
2. **Avoid blind overwrites** — If the existing lib has diverged, adapt Amazon to use it rather than replacing it
3. **Verify relationship patterns** — Shopify uses SQLModel `Relationship(back_populates=...)`; ensure ORM supports both this and AppWorld's `has_one`/`has_many` style

### API Protocol Divergence

| Aspect | Shopify | Amazon |
|--------|---------|--------|
| Protocol | GraphQL (strawberry) | REST (FastAPI) |
| Auth | OAuth scopes | `buyer_token` header |
| IDs | `gid://shopify/Resource/123` | ASINs, numeric IDs |

**Task runner must support mixed protocols** — Verify the environment runtime can handle tasks with both GraphQL and REST calls before implementing.

### Dependency Management (uv run)

This project uses `uv` for dependency management. Key reminders:

```bash
# Add new dependencies to pyproject.toml
uv add strawberry-graphql fastapi sqlmodel

# Run commands within the venv
uv run python -m shopworld.apps.amazon_simulator.seed

# Sync after manual pyproject.toml edits
uv sync
```

**Do not** use `pip install` directly — always use `uv run` or `uv add` to keep dependencies tracked.

### Multi-App Task Isolation

When `allowed_apps` includes both platforms:

- **State snapshots** must support seeding data for both apps independently
- **Cross-app transactions** — Clarify whether agents can coordinate changes across both platforms atomically
- **Database sessions** — Determine if apps share a connection or have isolated sessions per task

## Key Insight

The real value isn't the encrypted Amazon app—it's the **framework for building such apps**. With `apps/lib/` and the environment runtime, you can build a better Amazon simulator that's fully under your control and tailored to your agent training needs.

**Critical**: Maintain strict architectural separation through prefixed table names, compatible ORM patterns, and clean app boundaries.
