"""Logistics simulator - tracks packages, generates delivery events."""

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum


class PackageStatus(Enum):
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    EXCEPTION = "exception"
    LOST = "lost"


@dataclass
class Package:
    tracking_number: str
    order_id: str
    status: PackageStatus
    origin: str
    destination: str
    ship_date: datetime
    expected_delivery: datetime
    actual_delivery: Optional[datetime] = None
    last_scan: Optional[datetime] = None
    last_location: Optional[str] = None
    exception_reason: Optional[str] = None


class LogisticsSimulator:
    """Simulates carrier/package delivery."""
    
    CARRIERS = ["UPS", "FedEx", "USPS", "DHL"]
    LOCATIONS = [
        "Warehouse", "Distribution Center", "Regional Hub",
        "Local Facility", "Out for Delivery", "Delivered"
    ]
    
    EXCEPTION_REASONS = [
        "Address correction needed",
        "Customer not available",
        "Weather delay",
        "Damaged in transit",
        "Missed delivery cutoff",
    ]
    
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.packages: Dict[str, Package] = {}
    
    def create_shipment(
        self,
        order_id: str,
        origin: str,
        destination: str,
        ship_date: datetime,
        transit_days: int = 3,
    ) -> Package:
        """Create a new package shipment."""
        tracking = f"1Z{self.rng.randint(100000000000, 999999999999)}"
        
        pkg = Package(
            tracking_number=tracking,
            order_id=order_id,
            status=PackageStatus.PENDING,
            origin=origin,
            destination=destination,
            ship_date=ship_date,
            expected_delivery=ship_date + timedelta(days=transit_days),
        )
        
        self.packages[tracking] = pkg
        return pkg
    
    def step(self, current_time: datetime, world_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Advance simulation and generate tracking events."""
        events = []
        
        for pkg in self.packages.values():
            if pkg.status == PackageStatus.PENDING and current_time >= pkg.ship_date:
                pkg.status = PackageStatus.IN_TRANSIT
                pkg.last_scan = current_time
                pkg.last_location = self.LOCATIONS[1]
                
                events.append({
                    "type": "shipment_picked_up",
                    "tracking": pkg.tracking_number,
                    "order_id": pkg.order_id,
                    "location": pkg.last_location,
                })
            
            elif pkg.status == PackageStatus.IN_TRANSIT:
                # Progress through network
                days_in_transit = (current_time - pkg.ship_date).days
                
                # Random exception (2% chance per day)
                if self.rng.random() < 0.02:
                    pkg.status = PackageStatus.EXCEPTION
                    pkg.exception_reason = self.rng.choice(self.EXCEPTION_REASONS)
                    events.append({
                        "type": "delivery_exception",
                        "tracking": pkg.tracking_number,
                        "order_id": pkg.order_id,
                        "reason": pkg.exception_reason,
                    })
                    continue
                
                # Normal progression
                if days_in_transit >= 2 and pkg.last_location == self.LOCATIONS[1]:
                    pkg.last_location = self.LOCATIONS[2]
                    pkg.last_scan = current_time
                
                if current_time >= pkg.expected_delivery - timedelta(hours=12):
                    pkg.status = PackageStatus.OUT_FOR_DELIVERY
                    pkg.last_location = self.LOCATIONS[-2]
                    events.append({
                        "type": "out_for_delivery",
                        "tracking": pkg.tracking_number,
                        "order_id": pkg.order_id,
                    })
            
            elif pkg.status == PackageStatus.OUT_FOR_DELIVERY:
                # Deliver or fail
                if current_time >= pkg.expected_delivery:
                    if self.rng.random() < 0.95:  # 95% delivery success
                        pkg.status = PackageStatus.DELIVERED
                        pkg.actual_delivery = current_time
                        pkg.last_location = self.LOCATIONS[-1]
                        
                        events.append({
                            "type": "delivered",
                            "tracking": pkg.tracking_number,
                            "order_id": pkg.order_id,
                            "delivered_at": pkg.actual_delivery.isoformat(),
                        })
                    else:
                        pkg.status = PackageStatus.EXCEPTION
                        pkg.exception_reason = "Delivery attempted - customer not available"
                        events.append({
                            "type": "delivery_failed",
                            "tracking": pkg.tracking_number,
                            "order_id": pkg.order_id,
                            "reason": pkg.exception_reason,
                        })
        
        return events
    
    def get_tracking(self, tracking_number: str) -> Optional[Dict[str, Any]]:
        """Get tracking information for a package."""
        pkg = self.packages.get(tracking_number)
        if not pkg:
            return None
        
        return {
            "tracking_number": pkg.tracking_number,
            "status": pkg.status.value,
            "origin": pkg.origin,
            "destination": pkg.destination,
            "ship_date": pkg.ship_date.isoformat(),
            "expected_delivery": pkg.expected_delivery.isoformat(),
            "actual_delivery": pkg.actual_delivery.isoformat() if pkg.actual_delivery else None,
            "last_scan": {
                "time": pkg.last_scan.isoformat() if pkg.last_scan else None,
                "location": pkg.last_location,
            },
            "exception": pkg.exception_reason,
        }
