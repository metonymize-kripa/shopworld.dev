"""Store seed data generator for ShopWorld."""

import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional


class StoreSeeder:
    """Generate realistic store data for scenarios."""
    
    PRODUCT_CATEGORIES = ["T-Shirts", "Hoodies", "Jeans", "Accessories", "Shoes"]
    
    COLORS = ["Black", "White", "Navy", "Gray", "Red", "Blue", "Green"]
    SIZES = ["XS", "S", "M", "L", "XL", "XXL"]
    
    FIRST_NAMES = ["Emma", "Liam", "Olivia", "Noah", "Ava", "Oliver", "Sophia", "Elijah"]
    LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller"]
    
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
    
    def generate_store(
        self,
        product_count: int = 10,
        variant_count: int = 30,
        customer_count: int = 50,
        order_count: int = 100,
        location_count: int = 2,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Generate complete store dataset."""
        data = {
            "products": [],
            "product_variants": [],
            "inventory_items": [],
            "inventory_levels": [],
            "locations": [],
            "customers": [],
            "orders": [],
            "order_line_items": [],
            "support_tickets": [],
        }
        
        # Generate locations
        data["locations"] = self._generate_locations(location_count)
        location_ids = [loc["id"] for loc in data["locations"]]
        
        # Generate products and variants
        inv_item_offset = 0
        for i in range(product_count):
            product, variants, inventory_items = self._generate_product(i, location_ids, inv_item_offset)
            data["products"].append(product)
            data["product_variants"].extend(variants)
            data["inventory_items"].extend(inventory_items)
            inv_item_offset += len(inventory_items)
        
        # Generate inventory levels
        for item in data["inventory_items"]:
            for loc_id in location_ids:
                level = {
                    "id": len(data["inventory_levels"]) + 1,
                    "inventory_item_id": item["id"],
                    "location_id": loc_id,
                    "available": self.rng.randint(10, 100),
                    "incoming": self.rng.randint(0, 50),
                    "reserved": 0,
                }
                data["inventory_levels"].append(level)
        
        # Generate customers
        data["customers"] = self._generate_customers(customer_count)
        customer_ids = [c["id"] for c in data["customers"]]
        
        # Generate orders
        for i in range(order_count):
            order, line_items = self._generate_order(i, customer_ids, data["product_variants"])
            data["orders"].append(order)
            data["order_line_items"].extend(line_items)
        
        # Add some support tickets
        data["support_tickets"] = self._generate_support_tickets(data["orders"])
        
        return data
    
    def _generate_locations(self, count: int) -> List[Dict[str, Any]]:
        """Generate store locations."""
        locations = []
        names = ["Main Warehouse", "Retail Store", "Backup Warehouse"]
        
        for i in range(count):
            locations.append({
                "id": f"gid://shopify/Location/{i+1}",
                "name": names[i] if i < len(names) else f"Location {i+1}",
                "active": True,
            })
        
        return locations
    
    def _generate_product(
        self,
        index: int,
        location_ids: List[str],
        inv_item_offset: int = 0,
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Generate a product with variants."""
        category = self.rng.choice(self.PRODUCT_CATEGORIES)
        color = self.rng.choice(self.COLORS)
        
        product_id = f"gid://shopify/Product/{index+1}"
        product = {
            "id": product_id,
            "title": f"{color} {category}",
            "handle": f"{color.lower()}-{category.lower().replace(' ', '-')}",
            "description": f"A quality {color.lower()} {category.lower()}",
            "product_type": category,
            "vendor": "ShopWorld Brand",
            "status": "ACTIVE",
            "price_range_min": Decimal("29.99"),
            "price_range_max": Decimal("29.99"),
            "created_at": datetime.now(timezone.utc) - timedelta(days=self.rng.randint(30, 365)),
            "updated_at": datetime.now(timezone.utc) - timedelta(days=self.rng.randint(1, 30)),
        }
        
        variants = []
        inventory_items = []
        
        # Generate 3-6 size variants (can't exceed available sizes)
        num_variants = self.rng.randint(3, min(6, len(self.SIZES)))
        selected_sizes = self.rng.sample(self.SIZES, num_variants)
        
        for size in selected_sizes:
            variant_id = f"{product_id}/Variant/{len(variants)+1}"
            sku = f"SW-{category[:3].upper()}-{color[:3].upper()}-{size}"
            
            variant = {
                "id": variant_id,
                "product_id": product_id,
                "sku": sku,
                "option1": size,
                "option2": color,
                "price": Decimal("29.99"),
                "compare_at_price": None,
                "cost": Decimal("12.00"),
            }
            variants.append(variant)
            
            # Create inventory item
            inv_item_id = f"gid://shopify/InventoryItem/{inv_item_offset + len(inventory_items) + 100}"
            inventory_item = {
                "id": inv_item_id,
                "sku": sku,
                "tracked": True,
            }
            inventory_items.append(inventory_item)
            
            # Link variant to inventory item
            variant["inventory_item_id"] = inv_item_id
        
        return product, variants, inventory_items
    
    def _generate_customers(self, count: int) -> List[Dict[str, Any]]:
        """Generate customers."""
        customers = []
        
        for i in range(count):
            first = self.rng.choice(self.FIRST_NAMES)
            last = self.rng.choice(self.LAST_NAMES)
            
            customer = {
                "id": f"gid://shopify/Customer/{i+1}",
                "email": f"{first.lower()}.{last.lower()}{self.rng.randint(1,999)}@example.com",
                "first_name": first,
                "last_name": last,
                "orders_count": self.rng.randint(0, 10),
                "total_spent": Decimal(str(self.rng.uniform(0, 500))),
                "state": "ENABLED",
                "created_at": datetime.now(timezone.utc) - timedelta(days=self.rng.randint(30, 365)),
            }
            customers.append(customer)
        
        return customers
    
    def _generate_order(
        self,
        index: int,
        customer_ids: List[str],
        variants: List[Dict[str, Any]],
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Generate an order with line items."""
        order_id = f"gid://shopify/Order/{index+1}"
        customer_id = self.rng.choice(customer_ids)
        
        created_at = datetime.now(timezone.utc) - timedelta(days=self.rng.randint(1, 60))
        
        # Determine order status
        status_roll = self.rng.random()
        if status_roll < 0.6:
            fulfillment_status = "FULFILLED"
        elif status_roll < 0.85:
            fulfillment_status = "UNFULFILLED"
        else:
            fulfillment_status = "PARTIAL"
        
        order = {
            "id": order_id,
            "name": f"#{1000 + index}",
            "customer_id": customer_id,
            "email": None,
            "display_financial_status": "PAID",
            "display_fulfillment_status": fulfillment_status,
            "subtotal_price": Decimal("0"),
            "total_tax": Decimal("8.50"),
            "total_shipping": Decimal("5.00"),
            "total_discounts": Decimal("0"),
            "total_price": Decimal("0"),
            "created_at": created_at,
            "updated_at": created_at,
        }
        
        # Generate 1-3 line items
        line_items = []
        subtotal = Decimal("0")
        
        num_items = self.rng.randint(1, 3)
        selected_variants = self.rng.sample(variants, min(num_items, len(variants)))
        
        for i, variant in enumerate(selected_variants):
            quantity = self.rng.randint(1, 2)
            price = variant["price"]
            line_total = price * quantity
            subtotal += line_total
            
            line_item = {
                "id": f"{order_id}/LineItem/{i+1}",
                "order_id": order_id,
                "product_id": variant["product_id"],
                "variant_id": variant["id"],
                "title": f"Product {i+1}",
                "variant_title": f"Size: {variant.get('option1', 'M')}",
                "sku": variant["sku"],
                "quantity": quantity,
                "fulfillable_quantity": quantity,
                "price": price,
                "discounted_price": price,
                "total_discount": Decimal("0"),
            }
            line_items.append(line_item)
        
        order["subtotal_price"] = subtotal
        order["total_price"] = subtotal + order["total_tax"] + order["total_shipping"]
        
        return order, line_items
    
    def _generate_support_tickets(
        self,
        orders: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate support tickets for delayed/problem orders."""
        tickets = []
        
        # Find unfulfilled orders older than 7 days
        now = datetime.now(timezone.utc)
        delayed_orders = [
            o for o in orders
            if o.get("display_fulfillment_status") == "UNFULFILLED"
            and (now - o.get("created_at", now)).days > 7
        ]
        
        # Create WISMO tickets for ~30% of delayed orders
        for order in delayed_orders[:max(3, len(delayed_orders) // 3)]:
            ticket = {
                "id": f"ticket-{len(tickets)+1}",
                "customer_id": order.get("customer_id"),
                "order_id": order.get("id"),
                "subject": "Where is my order?",
                "description": f"I placed this order {(now - order.get('created_at', now)).days} days ago and haven't received it yet.",
                "category": "WISMO",
                "priority": "MEDIUM",
                "status": "OPEN",
                "customer_sentiment": -0.3,
                "created_at": now - timedelta(days=1),
            }
            tickets.append(ticket)
        
        return tickets


def to_jsonable(value: Any) -> Any:
    """Convert generated simulator seed data into stable JSON primitives."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    return value


def build_simulator_dataset(
    seed: int = 42,
    product_count: int = 10,
    customer_count: int = 50,
    order_count: int = 100,
    location_count: int = 2,
) -> Dict[str, Any]:
    """Build all generated data needed by the current simulator stack.

    The platform simulators consume a shared commerce snapshot plus latent
    operational data. Keeping this export deterministic gives local demos,
    tests, and future task generation a single reproducible data source.
    """
    seeder = StoreSeeder(seed=seed)
    store = seeder.generate_store(
        product_count=product_count,
        customer_count=customer_count,
        order_count=order_count,
        location_count=location_count,
    )

    return to_jsonable(
        {
            "manifest": {
                "schema_version": 1,
                "seed": seed,
                "description": "Deterministic ShopWorld simulator seed data",
                "record_counts": {name: len(records) for name, records in store.items()},
            },
            "store": store,
        }
    )


def create_sample_store(seed: int = 42) -> Dict[str, List[Dict[str, Any]]]:
    """Create a sample store with default parameters."""
    seeder = StoreSeeder(seed=seed)
    return seeder.generate_store(
        product_count=10,
        variant_count=35,
        customer_count=50,
        order_count=100,
        location_count=2,
    )
