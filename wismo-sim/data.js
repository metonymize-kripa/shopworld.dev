/**
 * WISMO Simulator — Scenario Data & Constants
 */

export const WORKFLOW_LEVELS = {
  L0: { label: 'L0 — Native Clean', color: '#0FA47E', desc: 'One safe Shopify mutation resolves the issue' },
  L1: { label: 'L1 — Native Multi-step', color: '#9A7FF5', desc: 'Shopify supports it, but requires correct sequencing' },
  L2: { label: 'L2 — Native Data + External', color: '#E85F22', desc: 'Requires carrier/warehouse/payment network action' },
  L3: { label: 'L3 — App Pattern', color: '#FF5C7A', desc: 'Best workflow uses helpdesk/tracking/returns app' },
  L4: { label: 'L4 — Human Required', color: '#5C574E', desc: 'Policy override, legal risk, or ambiguous evidence' },
}

export const STEP_TYPES = {
  native:   { label: 'Shopify handles it',  color: '#0FA47E', bg: '#E8F9F4', icon: '✓' },
  external: { label: 'External API call',   color: '#9A7FF5', bg: '#F0EDFF', icon: '⇄' },
  manual:   { label: 'You handle it',       color: '#E85F22', bg: '#FFF0E8', icon: '⚙' },
  chaos:    { label: 'Nobody handles it',   color: '#FF5C7A', bg: '#FFE9EE', icon: '⚠' },
}

export const SCENARIOS = [
  {
    id: 'wismo-basic',
    emoji: '📡',
    title: 'WISMO — Basic Tracking',
    trigger: '"Where is my order? It should have arrived yesterday."',
    level: 'L0',
    levelJustification: 'Shopify has all data needed; single GraphQL query resolves it',
    dataModel: {
      order: {
        id: 'gid://shopify/Order/7201928394',
        name: '#1024',
        financialStatus: 'PAID',
        fulfillments: [
          { id: 'ful_001', status: 'SHIPPED', trackingNumber: '1Z999AA10123456784', carrier: 'UPS' }
        ]
      },
      shipment: {
        status: 'IN_TRANSIT',
        lastScan: '2024-06-15T14:30:00Z',
        lastLocation: 'Louisville, KY',
        estimatedDelivery: '2024-06-18',
      }
    },
    apiCalls: [
      { type: 'query', name: 'order', fields: ['id', 'name', 'financialStatus', 'fulfillments'] },
      { type: 'query', name: 'shipmentTracking', fields: ['status', 'estimatedDelivery', 'events'] },
    ],
    stateTransitions: [
      { from: 'CUSTOMER_INQUIRY', to: 'TRACKING_RETRIEVED', api: 'order + shipmentTracking' },
      { from: 'TRACKING_RETRIEVED', to: 'RESPONSE_SENT', api: 'sendNotification' },
    ],
    steps: [
      { label: 'Query order + fulfillments',     type: 'native', detail: 'GraphQL: order(id) { fulfillments { trackingNumber } }' },
      { label: 'Query carrier tracking API',     type: 'native', detail: 'Shopify returns UPS tracking events via FedEx integration' },
      { label: 'Compute ETA from last scan',     type: 'native', detail: 'estimatedDelivery calculated from carrier transit data' },
      { label: 'Send automated response',        type: 'native', detail: 'Email template with tracking link + ETA' },
    ],
    gapAnalysis: {
      filled: ['Order data retrieval', 'Carrier tracking', 'ETA computation', 'Customer notification'],
      partial: [],
      missing: [],
    },
    metrics: { resolutionTime: '2-5 seconds', apiCalls: 2, manualSteps: 0, errorRate: '< 1%' },
    note: 'Pure L0 workflow. Shopify has order state + carrier partnerships. No gaps here — but this is the happy path.',
  },
  {
    id: 'partial-fulfillment',
    emoji: '📋',
    title: 'Partial Fulfillment — Split Shipment',
    trigger: '"I got one box but I ordered three items — where\'s the rest?"',
    level: 'L1',
    levelJustification: 'Shopify supports partial fulfillment natively but requires correct multi-step sequencing across fulfillment orders',
    dataModel: {
      order: {
        id: 'gid://shopify/Order/7201928398',
        name: '#1028',
        financialStatus: 'PAID',
        fulfillmentStatus: 'PARTIALLY_FULFILLED',
        lineItems: [
          { sku: 'JACKET-BLK-L', quantity: 1, fulfilled: 1 },
          { sku: 'PANTS-BLK-32', quantity: 1, fulfilled: 0 },
          { sku: 'BELT-BRN-M', quantity: 1, fulfilled: 0 },
        ],
        fulfillments: [
          { id: 'ful_010', status: 'DELIVERED', trackingNumber: '1Z111AA10111111111', carrier: 'UPS', lineItems: ['JACKET-BLK-L'] }
        ],
      },
      fulfillmentOrders: [
        { id: 'fo_001', status: 'CLOSED', assignedLocation: 'Warehouse A' },
        { id: 'fo_002', status: 'OPEN', assignedLocation: 'Warehouse B', lineItems: ['PANTS-BLK-32', 'BELT-BRN-M'] },
      ]
    },
    apiCalls: [
      { type: 'query', name: 'order', fields: ['lineItems', 'fulfillments', 'fulfillmentOrders'] },
      { type: 'query', name: 'fulfillmentOrder', fields: ['id', 'status', 'assignedLocation', 'lineItems'] },
      { type: 'mutation', name: 'fulfillmentCreateV2', input: '{ fulfillmentOrderId, trackingInfo }' },
    ],
    stateTransitions: [
      { from: 'PARTIALLY_FULFILLED', to: 'FULFILLMENT_ORDER_QUERIED' },
      { from: 'FULFILLMENT_ORDER_QUERIED', to: 'REMAINING_ITEMS_LOCATED' },
      { from: 'REMAINING_ITEMS_LOCATED', to: 'SECOND_SHIPMENT_CREATED' },
      { from: 'SECOND_SHIPMENT_CREATED', to: 'FULLY_FULFILLED' },
    ],
    steps: [
      { label: 'Query order + fulfillment orders',    type: 'native', detail: 'GraphQL: order { fulfillmentOrders { status lineItems } }' },
      { label: 'Identify unfulfilled fulfillment order', type: 'native', detail: 'Filter fulfillmentOrders where status = OPEN' },
      { label: 'Check stock at assigned location',    type: 'native', detail: 'inventoryLevel query for remaining SKUs' },
      { label: 'Create fulfillment with tracking',    type: 'native', detail: 'fulfillmentCreateV2 mutation on open fulfillment order' },
      { label: 'Send split-shipment notification',    type: 'native', detail: 'Shopify email: "Part 2 of your order is on the way"' },
    ],
    gapAnalysis: {
      filled: ['Partial fulfillment tracking', 'Fulfillment order model', 'Multi-location inventory', 'Customer notification'],
      partial: ['Split shipment visibility in customer account'],
      missing: [],
    },
    metrics: { resolutionTime: '30-60 seconds', apiCalls: 3, manualSteps: 0, errorRate: '5%' },
    note: 'L1 workflow. Shopify handles it all natively, but you must sequence: query open fulfillment orders → check stock → create fulfillment. Misordering causes errors.',
  },
  {
    id: 'wismo-stale',
    emoji: '⏱️',
    title: 'WISMO — Stale Tracking (No Scan 5+ Days)',
    trigger: '"My tracking hasn\'t moved in a week — is it lost?"',
    level: 'L2',
    levelJustification: 'Shopify has order data, but carrier exception requires external investigation',
    dataModel: {
      order: {
        id: 'gid://shopify/Order/7201928395',
        name: '#1025',
        fulfillments: [{ id: 'ful_002', status: 'SHIPPED', trackingNumber: '1Z888BB20234567891', carrier: 'UPS' }]
      },
      shipment: {
        status: 'IN_TRANSIT',
        lastScan: '2024-06-10T16:45:00Z',
        daysSinceScan: 6,
        exceptionCode: 'DELAY_UNKNOWN',
      }
    },
    apiCalls: [
      { type: 'query', name: 'order', fields: ['fulfillments'] },
      { type: 'query', name: 'shipmentTracking', fields: ['status', 'lastScan', 'daysSinceScan'] },
      { type: 'external', name: 'carrier.openInvestigation', fields: ['caseId', 'estimatedResolution'] },
    ],
    stateTransitions: [
      { from: 'CUSTOMER_INQUIRY', to: 'TRACKING_RETRIEVED' },
      { from: 'TRACKING_RETRIEVED', to: 'EXCEPTION_DETECTED', condition: 'daysSinceScan > 5' },
      { from: 'EXCEPTION_DETECTED', to: 'CARRIER_INVESTIGATION_OPENED' },
      { from: 'CARRIER_INVESTIGATION_OPENED', to: 'ESCALATED_TO_HUMAN' },
    ],
    steps: [
      { label: 'Query order + tracking',         type: 'native', detail: 'GraphQL order query returns stale tracking' },
      { label: 'Detect exception (no scan 5d+)', type: 'native', detail: 'Our runtime logic: daysSinceScan > threshold' },
      { label: 'Open carrier investigation',     type: 'external', detail: 'POST /v1/cases { trackingNumber, reason: "no_scan" }' },
      { label: 'Set follow-up reminder',         type: 'manual', detail: 'No native Shopify reminder — manual calendar entry' },
    ],
    gapAnalysis: {
      filled: ['Stale tracking detection'],
      partial: ['Carrier investigation API'],
      missing: ['Automated follow-up reminders', 'Reship/refund decision logic', 'Carrier claim integration'],
    },
    metrics: { resolutionTime: '10-30 minutes', apiCalls: 3, manualSteps: 2, errorRate: '15%' },
    note: 'L2 workflow. Shopify shows tracking but doesn\'t monitor it. Gap: exception detection, carrier investigation API. AfterShip/Gorgias fill this.',
  },
  {
    id: 'return-exchange',
    emoji: '🔄',
    title: 'Return & Exchange — Size Swap',
    trigger: '"This shirt doesn\'t fit — can I swap for a medium?"',
    level: 'L3',
    levelJustification: 'Shopify has no native exchange flow; requires returns app (Loop, Returnly) or manual RMA + new order creation',
    dataModel: {
      order: {
        id: 'gid://shopify/Order/7201928399',
        name: '#1029',
        financialStatus: 'PAID',
        fulfillmentStatus: 'FULFILLED',
        lineItems: [
          { sku: 'SHIRT-BLU-L', quantity: 1, price: 59.00 }
        ],
      },
      returnRequest: {
        reason: 'SIZE_TOO_LARGE',
        requestedExchange: { sku: 'SHIRT-BLU-M', quantity: 1 },
        returnShippingMethod: 'PREPAID_LABEL',
      },
      inventory: {
        'SHIRT-BLU-M': { available: 8 }
      }
    },
    apiCalls: [
      { type: 'query', name: 'order', fields: ['lineItems', 'fulfillments'] },
      { type: 'query', name: 'inventoryLevel', fields: ['available'], note: 'Check exchange item in stock' },
      { type: 'external', name: 'returnsApp.createRMA', fields: ['rmaId', 'returnLabel'] },
      { type: 'mutation', name: 'draftOrderCreate', input: '{ lineItems: [SHIRT-BLU-M], note: "Exchange for #1029" }' },
      { type: 'mutation', name: 'draftOrderComplete', input: '{ paymentPending: false }' },
    ],
    stateTransitions: [
      { from: 'EXCHANGE_REQUESTED', to: 'RETURN_INITIATED' },
      { from: 'RETURN_INITIATED', to: 'RMA_CREATED', api: 'returnsApp' },
      { from: 'RMA_CREATED', to: 'EXCHANGE_ORDER_CREATED', api: 'draftOrderCreate' },
      { from: 'EXCHANGE_ORDER_CREATED', to: 'AWAITING_RETURN_ITEM' },
    ],
    steps: [
      { label: 'Verify original order eligibility',   type: 'native', detail: 'Check return window, item condition policy' },
      { label: 'Check exchange item stock',           type: 'native', detail: 'inventoryLevel for SHIRT-BLU-M' },
      { label: 'Create RMA + return label',           type: 'external', detail: 'Loop/Returnly API: POST /returns { items, exchangeFor }' },
      { label: 'Create exchange draft order',         type: 'manual', detail: 'draftOrderCreate with $0 total (swap) or price diff' },
      { label: 'Notify customer with return label',   type: 'external', detail: 'Returns app sends email with prepaid label + instructions' },
    ],
    gapAnalysis: {
      filled: ['Order eligibility lookup', 'Inventory check for exchange item'],
      partial: ['Return creation (requires app)', 'Exchange order creation (draft order workaround)'],
      missing: ['Native exchange flow', 'Automatic inventory reservation for exchange', 'Unified return-exchange status page'],
    },
    metrics: { resolutionTime: '3-10 minutes', apiCalls: 5, manualSteps: 2, errorRate: '12%' },
    note: 'L3 workflow. Shopify lacks native exchanges — you need Loop, Returnly, or a custom RMA flow. The draft-order-as-exchange pattern is brittle and doesn\'t track the link between return and exchange.',
  },
  {
    id: 'fraud-chargeback',
    emoji: '🚨',
    title: 'Fraud Dispute — Chargeback Received',
    trigger: 'Stripe webhook: dispute.created — customer claims "I didn\'t make this purchase"',
    level: 'L4',
    levelJustification: 'Requires human judgment on fraud evidence, legal liability, and policy override decision — no safe automation path',
    dataModel: {
      order: {
        id: 'gid://shopify/Order/7201928400',
        name: '#1030',
        financialStatus: 'PAID',
        fulfillmentStatus: 'FULFILLED',
        totalPrice: 347.00,
        riskLevel: 'HIGH',
      },
      dispute: {
        id: 'dp_1234567890',
        amount: 347.00,
        reason: 'fraudulent',
        status: 'needs_response',
        deadline: '2024-06-25T23:59:59Z',
        evidence: {
          deliveryConfirmation: true,
          ipMatch: false,
          avsMatch: 'PARTIAL',
          previousOrders: 2,
        }
      }
    },
    apiCalls: [
      { type: 'query', name: 'order', fields: ['riskLevel', 'financialStatus', 'billingAddress', 'shippingAddress'] },
      { type: 'query', name: 'customer', fields: ['ordersCount', 'totalSpent', 'createdAt'] },
      { type: 'external', name: 'stripe.retrieveDispute', fields: ['reason', 'deadline', 'evidence'] },
    ],
    stateTransitions: [
      { from: 'DISPUTE_RECEIVED', to: 'EVIDENCE_GATHERED' },
      { from: 'EVIDENCE_GATHERED', to: 'HUMAN_REVIEW_REQUIRED' },
      { from: 'HUMAN_REVIEW_REQUIRED', to: 'ACCEPT_DISPUTE | COUNTER_DISPUTE', condition: 'human decision' },
    ],
    steps: [
      { label: 'Retrieve order + risk data',          type: 'native', detail: 'GraphQL: order risk indicators, address match' },
      { label: 'Pull payment dispute details',        type: 'external', detail: 'Stripe API: GET /disputes/{id}' },
      { label: 'Gather delivery evidence',            type: 'external', detail: 'Carrier proof-of-delivery, signature, photos' },
      { label: 'Assess fraud likelihood',             type: 'chaos', detail: 'Ambiguous evidence — IP mismatch but valid AVS + delivery confirmed' },
      { label: 'Human decides: accept or counter',    type: 'chaos', detail: 'Policy override required: $347 at stake, legal liability both ways' },
      { label: 'Submit evidence or accept loss',      type: 'manual', detail: 'Stripe: POST /disputes/{id}/evidence or POST /disputes/{id}/close' },
    ],
    gapAnalysis: {
      filled: ['Order risk data', 'Basic dispute webhook handling'],
      partial: ['Evidence compilation (manual + scattered)', 'Carrier proof-of-delivery'],
      missing: ['Automated fraud scoring with dispute context', 'Decision support with P&L impact', 'Legal risk assessment', 'Policy playbook integration'],
    },
    metrics: { resolutionTime: '2-48 hours', apiCalls: 3, manualSteps: 4, errorRate: '35%' },
    note: 'L4 workflow. No safe automation path — wrong decision means either eating $347 or losing a legitimate customer. Requires human judgment on ambiguous evidence with legal and financial implications.',
  },
]
