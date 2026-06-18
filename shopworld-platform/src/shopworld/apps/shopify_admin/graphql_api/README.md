# ShopWorld — Shopify GraphQL API Coverage

Development area for expanding the simulated Shopify Admin GraphQL surface.

## Why this exists

The research in `platform-rnd/shopify-graphql-api-overview-gpt-5.5.md` frames
the Shopify Admin GraphQL as a **~4,000-page typed commerce schema** across
**~21 top-level domains**. The simulator needs to cover the high-frequency
operational surface closely enough that agents develop real-world habits around:

- Node IDs (`gid://shopify/...`)
- Cursor-based pagination (`edges / node / pageInfo`)
- GraphQL query cost and throttle limits
- Scope enforcement per operation
- `userErrors` pattern on every mutation
- Partial failures and validation semantics

## Current coverage (as of Phase 2 MVP)

### Queries implemented (`graphql.py`)

| Query | Status | Notes |
|---|---|---|
| `shop` | ✅ | Hardcoded stub |
| `product(id)` | ✅ | |
| `products` | ✅ | Basic, no cursor pagination |
| `order(id)` | ✅ | |
| `orders` | ✅ | Basic, no cursor pagination |
| `customer(id)` | ✅ | |
| `customers` | ✅ | Basic, no cursor pagination |
| `inventoryLevels` | ✅ | Filtered by location_ids |
| `supportTickets` | ✅ | ShopWorld-specific |

### Queries missing (MVP backlog)

| Query | Domain | Priority |
|---|---|---|
| `node(id)` | Core | High — agents rely on generic node lookup |
| `productVariants` | Products | High |
| `inventoryItems` | Inventory | High |
| `inventoryItem(id)` | Inventory | High |
| `location(id)` / `locations` | Inventory | High |
| `fulfillmentOrder(id)` | Fulfillment | High |
| `fulfillmentOrders` | Fulfillment | High |
| `collections` / `collection(id)` | Products | Medium |
| `discountNodes` | Discounts | Medium |
| `metafields` | Metafields | Medium |
| `metaobjects` | Metaobjects | Low |
| `abandonedCheckouts` | Orders | Low |

### Mutations implemented (`graphql.py`)

| Mutation | Status | Notes |
|---|---|---|
| `productUpdate` | ✅ | title, description, status only |
| `inventoryAdjustQuantities` | ✅ | delta-based |
| `refundCreate` | ✅ | amount-level only, no line items |

### Mutations missing (MVP backlog)

| Mutation | Domain | Priority |
|---|---|---|
| `productCreate` | Products | High |
| `productSet` | Products | High — upsert pattern |
| `productVariantUpdate` | Products | High |
| `inventoryItemUpdate` | Inventory | High |
| `orderUpdate` | Orders | High |
| `orderClose` / `orderCancel` | Orders | High |
| `fulfillmentCreateV2` | Fulfillment | High |
| `fulfillmentOrderAcceptFulfillmentRequest` | Fulfillment | High |
| `customerCreate` | Customers | Medium |
| `customerUpdate` | Customers | High |
| `tagsAdd` | Tags | High |
| `tagsRemove` | Tags | High |
| `metafieldsSet` | Metafields | High |
| `discountCodeBasicCreate` | Discounts | High |
| `discountCodeUpdate` | Discounts | Medium |
| `returnCreate` | Returns | Post-MVP |

## API behavior gaps

| Behavior | Status | Notes |
|---|---|---|
| Cursor-based pagination (Connection/Edge/PageInfo) | ❌ Missing | All current queries return flat arrays |
| `userErrors` array on mutations | ⚠️ Partial | Some mutations return it, not all |
| `node(id)` generic lookup | ❌ Missing | Shopify agents often use this pattern |
| GraphQL cost points per field | ❌ Missing | Needed for throttle simulation |
| Throttle simulation (restore rate) | ❌ Missing | Critical for realistic API training |
| Scope enforcement per operation | ⚠️ Partial | Environment checks scopes but GraphQL layer doesn't |
| Bulk operations (`bulkOperationRunQuery`) | ❌ Deferred | Post-MVP |

## File layout

```
graphql_api/
  README.md          ← this file (gap tracker + design notes)
  __init__.py
  pagination.py      ← Connection/Edge/PageInfo types + cursor helpers
  cost.py            ← query cost model + throttle simulator
  scopes.py          ← scope definitions + per-operation enforcement
  queries/
    __init__.py
    catalog.py       ← products, productVariants, collections
    inventory.py     ← inventoryItems, inventoryLevels, locations
    orders.py        ← orders, fulfillmentOrders, abandonedCheckouts
    customers.py     ← customers
    discounts.py     ← discountNodes
    metafields.py    ← metafields, metaobjects
    node.py          ← node(id) generic interface
  mutations/
    __init__.py
    catalog.py       ← productCreate, productUpdate, productSet, variantUpdate
    inventory.py     ← inventoryAdjustQuantities, inventoryItemUpdate
    orders.py        ← orderUpdate, orderClose, orderCancel, fulfillmentCreateV2
    customers.py     ← customerCreate, customerUpdate, tagsAdd, tagsRemove
    discounts.py     ← discountCodeBasicCreate, discountCodeUpdate
    metafields.py    ← metafieldsSet
    refunds.py       ← refundCreate (moved from graphql.py)
  models_ext.py      ← Return, AbandonedCheckout, Metaobject model stubs
  schema.py          ← assembles full schema from query/mutation modules
```

## Scale limits to simulate

From `shopify-graphql-api-overview-gpt-5.5.md`:

| Limit | Value |
|---|---|
| Max variants per product | 2,048 |
| Max input array size | 250 |
| Max single-query cost | 1,000 points |
| Standard restore rate | 100 points/sec |
| Advanced restore rate | 200 points/sec |
| Plus restore rate | 1,000 points/sec |

## Design principles

1. **Shopify-idiomatic first** — agents should not need to unlearn habits when
   connecting to a real store. Use `gid://shopify/...` node IDs, `edges/node`,
   `userErrors`, and the same field names as the real schema.

2. **Depth before breadth** — implement the full behavior of fewer operations
   rather than thin stubs for many. Prioritize the operations that appear in
   the most support/fulfillment/inventory task scenarios.

3. **Cost tracking on every field** — attach a point cost to each field
   resolver so the throttle simulator has real signal. The cost model should
   match Shopify's documented tiers.

4. **Scope enforcement in the resolver** — the GraphQL layer should raise
   scope errors directly, not rely solely on the environment layer.
