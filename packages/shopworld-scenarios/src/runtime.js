export const SIM_BOUNDARIES = {
  hiddenTruth: 'ShopWorld canonical state, hidden actor state, world physics, evaluator logic, and reward functions',
  merchantSurface: 'Shopify-like Admin API, support inbox API, storefront/cart API, policy documents, schemas, and tool results',
  demoSurface: 'Component-level scenario slices that reveal operational choices without exposing evaluator ground truth',
}

export const TOOL_FAMILIES = [
  'orders',
  'customers',
  'fulfillments',
  'shipments',
  'inventory',
  'refunds',
  'returns',
  'products',
  'discounts',
  'tickets',
  'policy',
]

export const COMPONENT_SIM_PRINCIPLES = [
  'Keep data fixtures outside React components so scenarios can graduate into platform tests.',
  'Separate agent-visible tool surfaces from hidden scorer and simulator state.',
  'Expose granular workflow slices that make runtime-environment design choices tangible to prospective clients.',
  'Prefer reusable scenario fixtures over one-off demo copy.',
]
