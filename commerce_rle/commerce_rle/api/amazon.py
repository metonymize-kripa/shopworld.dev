"""
The Amazon mock API — the agent's ENTIRE action surface.

This is the boundary that enforces "Amazon and nothing more." The agent can only
do what these endpoints allow. There is no venmo router, no spotify router; they
don't exist, so a misfiring policy physically cannot call them.

The API is a thin layer over a sqlite3 connection. It is intentionally written
as plain functions (not a running server) so the Gym env can call them in-process
for fast rollouts. A FastAPI app is also exposed (`build_app`) if you want to
serve it over HTTP for containerized / cross-language agents — mirrors AppWorld's
serve model.

Every mutating call validates inputs and raises ActionError on bad requests, the
same way a real API returns a 4xx. The env converts that into an observation, not
a crash — the agent learns from the error string.
"""

from __future__ import annotations
import sqlite3
from dataclasses import dataclass


class ActionError(Exception):
    """Raised on invalid agent actions (bad id, insufficient stock, etc.)."""


@dataclass
class AmazonAPI:
    conn: sqlite3.Connection

    def _q(self, sql: str, params: tuple = ()) -> list[dict]:
        self.conn.row_factory = sqlite3.Row
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def _one(self, sql: str, params: tuple = ()) -> dict | None:
        rows = self._q(sql, params)
        return rows[0] if rows else None

    # ── read APIs ────────────────────────────────────────────────────────────

    def search_products(self, query: str, category: str | None = None,
                        in_stock_only: bool = False) -> list[dict]:
        sql = "SELECT * FROM products WHERE lower(title) LIKE ?"
        params: tuple = (f"%{query.lower()}%",)
        if category:
            sql += " AND category = ?"
            params += (category,)
        if in_stock_only:
            sql += " AND stock > 0"
        sql += " ORDER BY price ASC"
        return self._q(sql, params)

    def show_product(self, product_id: int) -> dict:
        p = self._one("SELECT * FROM products WHERE id = ?", (product_id,))
        if p is None:
            raise ActionError(f"no product with id {product_id}")
        return p

    def list_addresses(self, user_id: int) -> list[dict]:
        return self._q("SELECT * FROM addresses WHERE user_id = ?", (user_id,))

    def default_address(self, user_id: int) -> dict:
        a = self._one(
            "SELECT * FROM addresses WHERE user_id = ? AND is_default = 1",
            (user_id,),
        )
        if a is None:
            raise ActionError(f"user {user_id} has no default address")
        return a

    def show_cart(self, user_id: int) -> list[dict]:
        return self._q("SELECT * FROM cart_items WHERE user_id = ?", (user_id,))

    def list_orders(self, user_id: int) -> list[dict]:
        return self._q("SELECT * FROM orders WHERE user_id = ?", (user_id,))

    def show_wishlist(self, user_id: int) -> list[dict]:
        return self._q("SELECT * FROM wishlist WHERE user_id = ?", (user_id,))

    # ── write APIs ───────────────────────────────────────────────────────────

    def add_to_cart(self, user_id: int, product_id: int, qty: int = 1) -> dict:
        if qty < 1:
            raise ActionError("qty must be >= 1")
        p = self.show_product(product_id)  # raises if missing
        if p["stock"] < qty:
            raise ActionError(
                f"insufficient stock for product {product_id}: "
                f"have {p['stock']}, want {qty}"
            )
        existing = self._one(
            "SELECT * FROM cart_items WHERE user_id = ? AND product_id = ?",
            (user_id, product_id),
        )
        cur = self.conn.cursor()
        if existing:
            cur.execute(
                "UPDATE cart_items SET qty = qty + ? WHERE id = ?",
                (qty, existing["id"]),
            )
        else:
            cur.execute(
                "INSERT INTO cart_items (user_id, product_id, qty) VALUES (?,?,?)",
                (user_id, product_id, qty),
            )
        self.conn.commit()
        return {"ok": True, "product_id": product_id, "qty": qty}

    def remove_from_cart(self, user_id: int, product_id: int) -> dict:
        cur = self.conn.cursor()
        cur.execute(
            "DELETE FROM cart_items WHERE user_id = ? AND product_id = ?",
            (user_id, product_id),
        )
        self.conn.commit()
        return {"ok": True, "removed": product_id}

    def place_order(self, user_id: int, product_id: int, qty: int,
                   ship_address_id: int) -> dict:
        """Direct buy of a single product (bypasses cart). Decrements stock."""
        if qty < 1:
            raise ActionError("qty must be >= 1")
        p = self.show_product(product_id)
        if p["stock"] < qty:
            raise ActionError(
                f"insufficient stock for product {product_id}: "
                f"have {p['stock']}, want {qty}"
            )
        addr = self._one(
            "SELECT * FROM addresses WHERE id = ? AND user_id = ?",
            (ship_address_id, user_id),
        )
        if addr is None:
            raise ActionError(
                f"address {ship_address_id} does not belong to user {user_id}"
            )
        total = round(p["price"] * qty, 2)
        user = self._one("SELECT * FROM users WHERE id = ?", (user_id,))
        if user is None:
            raise ActionError(f"no user with id {user_id}")
        if user["balance"] < total:
            raise ActionError(
                f"insufficient balance: have {user['balance']:.2f}, "
                f"order total {total:.2f}"
            )
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO orders (user_id, product_id, qty, ship_address_id, total) "
            "VALUES (?,?,?,?,?)",
            (user_id, product_id, qty, ship_address_id, total),
        )
        cur.execute(
            "UPDATE products SET stock = stock - ? WHERE id = ?", (qty, product_id)
        )
        cur.execute(
            "UPDATE users SET balance = balance - ? WHERE id = ?", (total, user_id)
        )
        self.conn.commit()
        return {"ok": True, "order_total": total, "balance_remaining": round(user["balance"] - total, 2)}

    def checkout_cart(self, user_id: int, ship_address_id: int) -> dict:
        """Convert every cart item into an order, then empty the cart."""
        items = self.show_cart(user_id)
        if not items:
            raise ActionError("cart is empty")
        results = []
        for it in items:
            results.append(
                self.place_order(user_id, it["product_id"], it["qty"], ship_address_id)
            )
        self.conn.execute("DELETE FROM cart_items WHERE user_id = ?", (user_id,))
        self.conn.commit()
        return {"ok": True, "orders_placed": len(results)}

    def return_order(self, user_id: int, order_id: int) -> dict:
        o = self._one(
            "SELECT * FROM orders WHERE id = ? AND user_id = ?", (order_id, user_id)
        )
        if o is None:
            raise ActionError(f"order {order_id} not found for user {user_id}")
        if o["status"] == "returned":
            raise ActionError(f"order {order_id} already returned")
        cur = self.conn.cursor()
        cur.execute("UPDATE orders SET status = 'returned' WHERE id = ?", (order_id,))
        cur.execute(
            "UPDATE products SET stock = stock + ? WHERE id = ?",
            (o["qty"], o["product_id"]),
        )
        self.conn.commit()
        return {"ok": True, "returned": order_id}

    def add_to_wishlist(self, user_id: int, product_id: int) -> dict:
        self.show_product(product_id)
        self.conn.execute(
            "INSERT INTO wishlist (user_id, product_id) VALUES (?,?)",
            (user_id, product_id),
        )
        self.conn.commit()
        return {"ok": True, "wishlisted": product_id}


# ── optional HTTP server (mirrors AppWorld's serve model) ────────────────────

def build_app(api_factory):
    """
    Build a FastAPI app over the Amazon API. `api_factory()` returns an AmazonAPI
    bound to the current task's connection. Only imported if FastAPI is installed;
    the in-process path needs none of this.
    """
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel

    app = FastAPI(title="Amazon Commerce Mock", version="0.1.0")

    class Buy(BaseModel):
        user_id: int
        product_id: int
        qty: int
        ship_address_id: int

    @app.get("/amazon/search")
    def search(query: str, category: str | None = None, in_stock_only: bool = False):
        return api_factory().search_products(query, category, in_stock_only)

    @app.get("/amazon/products/{product_id}")
    def product(product_id: int):
        try:
            return api_factory().show_product(product_id)
        except ActionError as e:
            raise HTTPException(422, str(e))

    @app.post("/amazon/orders")
    def order(body: Buy):
        try:
            return api_factory().place_order(
                body.user_id, body.product_id, body.qty, body.ship_address_id
            )
        except ActionError as e:
            raise HTTPException(422, str(e))

    return app
