/**
 * Post-purchase support scenario fixtures.
 */

export const STEP_TYPES = {
  native:  { label: 'Shopify handles it',  color: 'var(--mint-deep)',      bg: '#E8F9F4', icon: '✓' },
  app:     { label: 'App Store patch',     color: '#7C5FF5',               bg: '#F0EDFF', icon: '⬡' },
  manual:  { label: 'You handle it',       color: 'var(--tangerine-deep)', bg: '#FFF0E8', icon: '⚙' },
  chaos:   { label: 'Nobody handles it',   color: 'var(--rose)',           bg: '#FFE9EE', icon: '⚠' },
}

export const VERDICTS = {
  clean:   {
    label: 'Shopify covers this',
    color: 'var(--mint-deep)',
    bg: '#E8F9F4',
    emoji: '✅',
    hook: null,
  },
  partial: {
    label: 'Gaps you\'re patching manually',
    color: 'var(--tangerine-deep)',
    bg: '#FFF0E8',
    emoji: '⚡',
    hook: 'The manual steps here are where Shopworld saves time per ticket.',
  },
  chaos:   {
    label: 'Nobody owns this — yet',
    color: 'var(--rose)',
    bg: '#FFE9EE',
    emoji: '🔥',
    hook: 'This is the gap Shopworld fills.',
  },
}

export const SCENARIOS = [
  {
    id: 'cancel',
    emoji: '🚫',
    title: 'Cancel order',
    trigger: '"I just ordered by mistake — can you cancel?"',
    steps: [
      { label: 'Look up order by email',           type: 'native', detail: 'Orders → Search' },
      { label: 'Confirm order not yet fulfilled',  type: 'native', detail: 'Fulfillment status visible' },
      { label: 'Cancel order + void payment',      type: 'native', detail: 'Orders → Cancel' },
      { label: 'Customer notified automatically',  type: 'native', detail: 'Shopify sends cancellation email' },
    ],
    verdict: 'clean',
    note: 'Shopify handles this end-to-end if the order hasn\'t shipped. Once a label is printed, you\'re calling the carrier.',
  },
  {
    id: 'address',
    emoji: '📍',
    title: 'Change shipping address',
    trigger: '"I moved — update my address before it ships?"',
    steps: [
      { label: 'Find order',                                type: 'native', detail: 'Orders → Search' },
      { label: 'Edit address (unfulfilled only)',           type: 'native', detail: 'Order → Edit → Shipping address' },
      { label: 'Reprint label if already generated',       type: 'manual', detail: 'Void + reprint in Shopify Shipping or carrier portal' },
      { label: 'Contact carrier if package is in transit', type: 'chaos',  detail: 'Phone/chat with UPS/FedEx — success rate ~50%' },
    ],
    verdict: 'partial',
    note: 'Works before fulfillment. After the label prints, someone has to call the carrier — and that someone is you.',
  },
  {
    id: 'swap',
    emoji: '🔄',
    title: 'Swap size or variant',
    trigger: '"I ordered a Medium but I need a Large — can you swap it?"',
    steps: [
      { label: 'Find order',                               type: 'native', detail: 'Orders → Search' },
      { label: 'Check inventory for correct variant',      type: 'native', detail: 'Products → Inventory' },
      { label: 'Cancel original order',                    type: 'native', detail: 'Orders → Cancel (if unfulfilled)' },
      { label: 'Customer manually places new order',       type: 'chaos',  detail: 'No native "swap variant on paid order" — customer must reorder' },
      { label: 'Handle price difference or discount code', type: 'manual', detail: 'Issue discount via email or draft order' },
    ],
    verdict: 'chaos',
    note: 'Shopify has no native variant-swap on a paid order. Cancel + new draft order is the cleanest path — but it\'s a 5-step manual process per ticket.',
  },
  {
    id: 'return',
    emoji: '📦',
    title: 'Return item',
    trigger: '"I want to return this — how do I send it back?"',
    steps: [
      { label: 'Customer requests return',                type: 'manual', detail: 'Via email or contact form — no native self-service portal' },
      { label: 'Generate return shipping label',          type: 'app',    detail: 'Loop Returns, AfterShip, or Shopify basic returns' },
      { label: 'Track return in transit',                 type: 'app',    detail: 'App provides tracking; native Shopify doesn\'t' },
      { label: 'Inspect item on receipt',                 type: 'manual', detail: 'Physical inspection before refunding' },
      { label: 'Issue refund',                            type: 'native', detail: 'Orders → Refund' },
    ],
    verdict: 'partial',
    note: 'Shopify has basic return support but no self-service portal. Apps patch the label and tracking gap — but intake and inspection are still on you.',
  },
  {
    id: 'refund',
    emoji: '💸',
    title: 'Partial refund',
    trigger: '"One item was wrong — can you refund just that one?"',
    steps: [
      { label: 'Open order',                  type: 'native', detail: 'Orders → find order' },
      { label: 'Select line items to refund', type: 'native', detail: 'Refund → choose quantities' },
      { label: 'Set refund amount',           type: 'native', detail: 'Shopify calculates; override if needed' },
      { label: 'Restock inventory',           type: 'native', detail: 'Toggle restock on refund screen' },
      { label: 'Customer notified',           type: 'native', detail: 'Automatic refund confirmation email' },
    ],
    verdict: 'clean',
    note: 'Partial refunds are fully native — one of the few post-purchase flows Shopify does cleanly out of the box.',
  },
  {
    id: 'damaged',
    emoji: '💔',
    title: 'Damaged package',
    trigger: '"My order arrived smashed — I have photos."',
    steps: [
      { label: 'Customer sends photo evidence',             type: 'manual', detail: 'Email or DM — no native damage reporting' },
      { label: 'Log incident in order notes',              type: 'native', detail: 'Orders → Add note' },
      { label: 'Decide: reship or refund',                 type: 'manual', detail: 'Judgment call — policy-dependent' },
      { label: 'Issue refund or create replacement order', type: 'native', detail: 'Refund or duplicate order' },
      { label: 'File carrier claim',                       type: 'manual', detail: 'UPS/FedEx claims portal — 10–20 min per claim' },
    ],
    verdict: 'partial',
    note: 'Customer resolution is fine — refund or reship natively. The carrier claim is manual every time, with no Shopify integration.',
  },
  {
    id: 'wismo',
    emoji: '📡',
    title: 'Late shipment / WISMO',
    trigger: '"I ordered 12 days ago and nothing arrived — where is it?"',
    steps: [
      { label: 'Look up order and fulfillment',         type: 'native', detail: 'Orders → Fulfillments → Tracking' },
      { label: 'Check carrier tracking page',           type: 'manual', detail: 'Copy tracking number → carrier site' },
      { label: 'Contact carrier about delay',           type: 'chaos',  detail: 'Phone/chat — often no resolution' },
      { label: 'Decide: wait, reship, or refund',       type: 'manual', detail: 'Judgment call based on days in transit and carrier SLA' },
      { label: 'Communicate update to customer',        type: 'manual', detail: 'Manual email — no native delay notification' },
    ],
    verdict: 'chaos',
    note: 'Highest-volume ticket type. Least automated. Shopify shows tracking numbers but doesn\'t monitor them — every delay is a manual investigation.',
  },
  {
    id: 'chargeback',
    emoji: '⚖️',
    title: 'Chargeback dispute',
    trigger: 'Card network files dispute: "Item not received."',
    steps: [
      { label: 'Shopify flags dispute in admin',          type: 'native', detail: 'Payments → Disputes' },
      { label: 'Gather order + payment proof',            type: 'native', detail: 'Order timeline, payment confirmation' },
      { label: 'Gather delivery confirmation',            type: 'manual', detail: 'Screenshot carrier delivery scan manually' },
      { label: 'Compile customer communication history',  type: 'chaos',  detail: 'Dig through email/DMs — no unified inbox' },
      { label: 'Write and submit dispute response',       type: 'manual', detail: 'Submit to bank via Shopify Payments — 72hr deadline' },
    ],
    verdict: 'chaos',
    note: 'Shopify surfaces the dispute but gathering evidence is a scavenger hunt. No native evidence packager — every chargeback is a manual scramble against the clock.',
  },
]

