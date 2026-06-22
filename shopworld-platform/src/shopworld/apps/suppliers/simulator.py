"""Supplier simulator - manages POs, lead times, delays, defects."""

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone
from enum import Enum


class SupplierStatus(Enum):
    ACTIVE = "active"
    DISRUPTED = "disrupted"


class POStatus(Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    PARTIAL = "partial"
    RECEIVED = "received"


@dataclass
class SupplierProfile:
    supplier_id: str
    name: str
    lead_time_days: int
    moq: int
    fill_rate: float
    defect_rate: float
    current_status: SupplierStatus = SupplierStatus.ACTIVE


@dataclass
class PurchaseOrder:
    po_id: str
    supplier_id: str
    sku: str
    quantity: int
    status: POStatus
    submitted_at: Optional[datetime] = None
    expected_delivery: Optional[datetime] = None
    quantity_received: int = 0


class SupplierSimulator:
    """Simulates supplier behavior and PO lifecycle."""
    
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.suppliers: Dict[str, SupplierProfile] = {}
        self.pos: Dict[str, PurchaseOrder] = {}
    
    def register_supplier(
        self,
        supplier_id: str,
        name: str,
        lead_time_days: int = 14,
        moq: int = 50,
    ) -> SupplierProfile:
        profile = SupplierProfile(
            supplier_id=supplier_id,
            name=name,
            lead_time_days=lead_time_days,
            moq=moq,
            fill_rate=0.95,
            defect_rate=0.02,
        )
        self.suppliers[supplier_id] = profile
        return profile
    
    def create_po(self, supplier_id: str, sku: str, quantity: int) -> Optional[PurchaseOrder]:
        supplier = self.suppliers.get(supplier_id)
        if not supplier or quantity < supplier.moq:
            return None
        
        po_id = f"PO-{self.rng.randint(10000, 99999)}"
        po = PurchaseOrder(
            po_id=po_id,
            supplier_id=supplier_id,
            sku=sku,
            quantity=quantity,
            status=POStatus.DRAFT,
        )
        self.pos[po_id] = po
        return po
    
    def step(self, current_time: datetime, world_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Advance simulation and generate events."""
        events = []
        
        for po in self.pos.values():
            if po.status == POStatus.SUBMITTED and po.submitted_at:
                # Confirm after 1-2 days
                hours = (current_time - po.submitted_at).total_seconds() / 3600
                if hours >= 24:
                    po.status = POStatus.CONFIRMED
                    supplier = self.suppliers.get(po.supplier_id)
                    if supplier:
                        po.expected_delivery = current_time + timedelta(days=supplier.lead_time_days)
                    
                    events.append({
                        "type": "po_confirmed",
                        "po_id": po.po_id,
                        "expected_delivery": po.expected_delivery.isoformat() if po.expected_delivery else None,
                    })
            
            elif po.status == POStatus.CONFIRMED and po.expected_delivery:
                # Ship halfway through
                ship_date = po.expected_delivery - timedelta(days=7)
                if current_time >= ship_date:
                    po.status = POStatus.SHIPPED
                    events.append({
                        "type": "po_shipped",
                        "po_id": po.po_id,
                        "tracking": f"1Z{self.rng.randint(100000000, 999999999)}",
                    })
            
            elif po.status == POStatus.SHIPPED and po.expected_delivery:
                if current_time >= po.expected_delivery:
                    po.status = POStatus.RECEIVED
                    po.quantity_received = po.quantity
                    events.append({
                        "type": "po_received",
                        "po_id": po.po_id,
                        "quantity": po.quantity_received,
                    })
        
        return events
    
    def submit_po(self, po_id: str) -> bool:
        po = self.pos.get(po_id)
        if po and po.status == POStatus.DRAFT:
            po.status = POStatus.SUBMITTED
            po.submitted_at = datetime.now(timezone.utc)
            return True
        return False
