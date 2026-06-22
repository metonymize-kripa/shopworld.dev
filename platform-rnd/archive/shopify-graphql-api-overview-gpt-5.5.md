# Shopify GraphQL Gazetteer — Numbers

The Shopify Admin GraphQL surface is best treated as a **4,000+ page typed commerce schema**, across **21 top-level domains**, with cardinality concentrated in products, orders, fulfillment, customers, discounts, and extensibility. Shopify’s full index exposes the top-level domains directly. ([Shopify][1])

| Area                             | Queries | Mutations | Objects | Scale meaning                       |
| -------------------------------- | ------: | --------: | ------: | ----------------------------------- |
| Products & collections           |     ~40 |       ~74 |   ~100+ | Largest product/catalog world model |
| Orders / returns / subscriptions |     ~30 |       ~90 |    ~165 | Deepest transaction lifecycle model |
| Shipping & fulfillment           |     ~20 |       ~45 |     ~56 | Operational logistics model         |
| Inventory                        |       8 |        29 |      16 | Stock-state model                   |
| Customers                        |      17 |        31 |      36 | Buyer identity + segmentation       |
| Discounts & marketing            |     ~27 |       ~48 |     ~59 | Promotion/rule engine               |
| B2B                              |       7 |        31 |      10 | Company/account buying graph        |
| Markets                          |       8 |        15 |      11 | Geography/currency/localization     |
| Privacy                          |       3 |         3 |       7 | Consent/compliance state            |

Sources: product/catalog counts from the full index lines covering `Products and collections`; inventory, orders, fulfillment, customers, and markets from the corresponding full-index sections. ([Shopify][2])

# Hard Scale Limits

| Dimension                                     |                           Number |
| --------------------------------------------- | -------------------------------: |
| Max product variants per product              |                            2,048 |
| Historical variant limit                      |                              100 |
| Max input array size                          |                              250 |
| Max single-query cost                         |                     1,000 points |
| Standard GraphQL restore rate                 |                   100 points/sec |
| Advanced Shopify restore rate                 |                   200 points/sec |
| Plus restore rate                             |                 1,000 points/sec |
| Enterprise / Commerce Components restore rate |                 2,000 points/sec |
| Bulk query concurrency, API 2026-01+          |                       5 per shop |
| Bulk query max runtime                        |                          10 days |
| Variant creation throttle after 50k variants  | 1,000 new variants/day, non-Plus |

Sources: Shopify rate limits, bulk operations, and product variant changelog. ([Shopify][3])

# Compression

```text
Shopify Admin GraphQL =
  ~21 world domains
  ~4,000 documented schema pages
  ~hundreds of object types
  ~hundreds of mutations
  strict cost/cardinality controls
  bulk export for full-world synchronization
```

[INFERENCE] For WMIR, Shopify is not a “store API.” It is a **bounded commercial world model** with strong entity/state/action coverage and explicit throughput limits.

[1]: https://shopify.dev/docs/api/admin-graphql/latest "GraphQL Admin API reference"
[2]: https://shopify.dev/docs/api/admin-graphql/2026-04/full-index "GraphQL Admin API reference"
[3]: https://shopify.dev/docs/api/usage/limits "Shopify API limits"
