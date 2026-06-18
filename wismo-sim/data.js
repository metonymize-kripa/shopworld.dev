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
      { label: 'Detect exception (no scan 5d+)', type: 'native', detail: 'Shopworld logic: daysSinceScan > threshold' },
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
    id: 'cancel-early',
    emoji: '🚫',
    title: 'Cancel Order — Before Fulfillment',
    trigger: '"I just placed this — can you cancel it?"',
    level: 'L0',
    levelJustification: 'Single orderCancel mutation handles payment void + inventory restock',
    dataModel: {
      order: {
        id: 'gid://shopify/Order/7201928396',
        name: '#1026',
        financialStatus: 'PAID',
        fulfillmentStatus: 'UNFULFILLED',
        lineItems: [{ sku: 'SHIRT-001-M', quantity: 1 }],
        fulfillments: [],
        canCancel: true,
      },
      inventory: { 'SHIRT-001-M': { available: 42, committed: 1 } }
    },
    apiCalls: [
      { type: 'query', name: 'order', fields: ['financialStatus', 'fulfillmentStatus', 'fulfillments'] },
      { type: 'mutation', name: 'orderCancel', input: '{ orderId, notifyCustomer: true }' },
    ],
    stateTransitions: [
      { from: 'PAID_UNFULFILLED', to: 'CANCELING' },
      { from: 'CANCELING', to: 'CANCELLED', effects: ['Payment voided', 'Inventory restocked', 'Customer notified'] },
    ],
    steps: [
      { label: 'Query order eligibility',      type: 'native', detail: 'Check fulfillmentStatus === UNFULFILLED' },
      { label: 'Execute orderCancel mutation', type: 'native', detail: 'orderCancel → voids payment, restocks inventory' },
      { label: 'Customer auto-notified',       type: 'native', detail: 'Cancellation email with refund confirmation' },
    ],
    gapAnalysis: {
      filled: ['Eligibility check', 'Payment void', 'Inventory restock', 'Customer notification'],
      partial: [],
      missing: [],
    },
    metrics: { resolutionTime: '3-5 seconds', apiCalls: 2, manualSteps: 0, errorRate: '< 0.5%' },
    note: 'Clean L0. Shopify handles cancel end-to-end when unfulfilled. The catch: only works before label creation.',
  },
  {
    id: 'cancel-late',
    emoji: '📦',
    title: 'Cancel Order — After Label Created',
    trigger: '"Can you cancel? I see a label was created."',
    level: 'L2',
    levelJustification: 'Requires carrier label void + warehouse hold; no unified Shopify flow',
    dataModel: {
      order: {
        id: 'gid://shopify/Order/7201928397',
        name: '#1027',
        fulfillments: [{ status: 'LABEL_CREATED', trackingNumber: '1Z777CC30345678923' }],
      },
      label: { status: 'ACTIVE', voidDeadline: '2024-06-17T23:59:59Z' }
    },
    apiCalls: [
      { type: 'query', name: 'order', fields: ['fulfillments { status labelCreatedAt }'] },
      { type: 'external', name: 'carrier.voidLabel', fields: ['success', 'voidFee'] },
      { type: 'external', name: 'warehouse.holdOrder', fields: ['success'] },
      { type: 'mutation', name: 'orderCancel', input: '{ orderId, restock: true }' },
    ],
    stateTransitions: [
      { from: 'LABEL_CREATED', to: 'ATTEMPTING_LABEL_VOID' },
      { from: 'ATTEMPTING_LABEL_VOID', to: 'LABEL_VOIDED' },
      { from: 'LABEL_VOIDED', to: 'WAREHOUSE_HOLD_SET' },
      { from: 'WAREHOUSE_HOLD_SET', to: 'CANCELLED' },
    ],
    steps: [
      { label: 'Query fulfillment state',        type: 'native', detail: 'Detect fulfillment.status === LABEL_CREATED' },
      { label: 'Void shipping label',            type: 'external', detail: 'Carrier API: POST /void — $5-15 fee' },
      { label: 'Hold order at warehouse',        type: 'external', detail: '3PL API: PUT /hold — not all 3PLs support' },
      { label: 'Cancel order + restock',         type: 'native', detail: 'orderCancel only after successful hold' },
    ],
    gapAnalysis: {
      filled: ['Order state detection'],
      partial: ['Label void (carrier-dependent)', 'Warehouse hold (3PL-dependent)'],
      missing: ['Unified cancel flow', 'Automatic label void retry', '3PL hold status sync'],
    },
    metrics: { resolutionTime: '5-15 minutes', apiCalls: 4, manualSteps: 2, errorRate: '25%' },
    note: 'L2-L3 boundary. Shopify allows cancel, but label void and warehouse hold are external. Result: 25% of late cancels ship anyway → returns volume.',
  },
]
