import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

class Product:
    def __init__(self, name, price, available_amount):
        self.name = name
        self.price = price
        self.available_amount = available_amount

    def is_available(self, amount):
        return self.available_amount >= amount

    def buy(self, amount):
        if not self.is_available(amount):
            raise ValueError("Not enough product available")
        self.available_amount -= amount

    def __str__(self):
        return self.name

class ShoppingCart:
    def __init__(self):
        self.products = {}

    def add_product(self, product, amount):
        if not product.is_available(amount):
            raise ValueError(f"Product {product.name} is not available")
        self.products[product] = self.products.get(product, 0) + amount

    def remove_product(self, product):
        if product in self.products:
            del self.products[product]

    def submit_cart_order(self):
        product_ids = []
        for product, count in self.products.items():
            product.buy(count)
            product_ids.append(str(product))
        self.products.clear()
        return ",".join(product_ids)

@dataclass
class Order:
    cart: ShoppingCart
    shipping_service: any
    order_id: str = None

    def __post_init__(self):
        if not self.order_id:
            self.order_id = str(uuid.uuid4())

    def place_order(self, shipping_type, due_date: datetime = None):
        if not due_date:
            due_date = datetime.now(timezone.utc) + timedelta(seconds=3)
        product_ids_str = self.cart.submit_cart_order()
        product_ids_list = product_ids_str.split(",") if product_ids_str else []
        return self.shipping_service.create_shipping(shipping_type, product_ids_list, self.order_id, due_date)

@dataclass
class Shipment:
    shipping_id: str
    shipping_service: any

    def check_shipping_status(self):
        return self.shipping_service.check_status(self.shipping_id)