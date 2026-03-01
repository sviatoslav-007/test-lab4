import pytest
import uuid
import boto3
from app.eshop import Product, ShoppingCart, Order
from services.service import ShippingService
from services.repository import ShippingRepository
from services.publisher import ShippingPublisher
from services.config import AWS_ENDPOINT_URL, AWS_REGION, SHIPPING_QUEUE
from datetime import datetime, timedelta, timezone

@pytest.mark.parametrize("order_id, shipping_id", [
    ("order_1", "shipping_1"),
    (str(uuid.uuid4()), str(uuid.uuid4()))
])
def test_place_order_logic(mocker, order_id, shipping_id):
    mock_repo = mocker.Mock()
    mock_pub = mocker.Mock()
    service = ShippingService(mock_repo, mock_pub)
    mock_repo.create_shipping.return_value = shipping_id
    order = Order(ShoppingCart(), service, order_id)
    assert order.place_order("Нова Пошта") == shipping_id

def test_invalid_shipping_type(dynamo_resource):
    service = ShippingService(ShippingRepository(), ShippingPublisher())
    with pytest.raises(ValueError, match="Shipping type is not available"):
        service.create_shipping("Кур'єр на голубів", [], "o1", datetime.now(timezone.utc) + timedelta(days=1))

def test_sqs_integration(dynamo_resource):
    service = ShippingService(ShippingRepository(), ShippingPublisher())
    ship_id = service.create_shipping("Укр Пошта", ["p1"], "o1", datetime.now(timezone.utc) + timedelta(days=1))
    pub = ShippingPublisher()
    assert ship_id in pub.poll_shipping()

def test_check_status_integration(dynamo_resource):
    service = ShippingService(ShippingRepository(), ShippingPublisher())
    ship_id = service.create_shipping("Самовивіз", ["p1"], "o1", datetime.now(timezone.utc) + timedelta(days=1))
    assert service.check_status(ship_id) == 'in progress'

def test_batch_process(dynamo_resource):
    service = ShippingService(ShippingRepository(), ShippingPublisher())
    service.create_shipping("Нова Пошта", ["p1"], "o1", datetime.now(timezone.utc) + timedelta(days=1))
    results = service.process_shipping_batch()
    assert len(results) > 0

def test_fail_expired_shipping(dynamo_resource, mocker):
    service = ShippingService(ShippingRepository(), ShippingPublisher())
    repo = ShippingRepository()
    ship_id = repo.create_shipping("Нова Пошта", ["p1"], "o1", "created", datetime.now(timezone.utc) - timedelta(days=1))
    service.process_shipping(ship_id)
    assert service.check_status(ship_id) == 'failed'

def test_order_inventory_sync(dynamo_resource):
    service = ShippingService(ShippingRepository(), ShippingPublisher())
    prod = Product(name="SyncTest", price=10, available_amount=5)
    cart = ShoppingCart()
    cart.add_product(prod, 2)
    order = Order(cart, service)
    order.place_order("Нова Пошта")
    assert prod.available_amount == 3

def test_sqs_batch_receive(dynamo_resource):
    service = ShippingService(ShippingRepository(), ShippingPublisher())
    service.create_shipping("Нова Пошта", ["p1"], "o1", datetime.now(timezone.utc) + timedelta(days=1))
    service.create_shipping("Укр Пошта", ["p2"], "o2", datetime.now(timezone.utc) + timedelta(days=1))
    pub = ShippingPublisher()
    messages = pub.client.receive_message(QueueUrl=pub.queue_url, MaxNumberOfMessages=10)
    assert len(messages.get('Messages', [])) >= 2

def test_cart_remove_before_order_integration(dynamo_resource):
    service = ShippingService(ShippingRepository(), ShippingPublisher())
    p1 = Product("Phone", 100, 5)
    cart = ShoppingCart()
    cart.add_product(p1, 1)
    cart.remove_product(p1)  # Видаляємо товар
    order = Order(cart, service)
    ship_id = order.place_order("Самовивіз")

    repo = ShippingRepository()
    ship_data = repo.get_shipping(ship_id)
    assert ship_data['product_ids'] == ""