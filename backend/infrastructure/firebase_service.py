
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
import os
from pathlib import Path

load_dotenv()

# Usar la variable de entorno FIREBASE_KEY_PATH definida en .env
raw_cred_path = os.getenv("FIREBASE_KEY_PATH", "firebase_key.json")


def _resolve_cred_path(path_value):
    candidate = Path(path_value)
    if candidate.is_absolute() and candidate.exists():
        return str(candidate)

    backend_dir = Path(__file__).resolve().parents[1]
    search_paths = [
        Path.cwd() / path_value,
        backend_dir / path_value,
        backend_dir.parent / path_value,
    ]
    for path in search_paths:
        if path.exists():
            return str(path)
    return path_value


cred_path = _resolve_cred_path(raw_cred_path)

if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()


def save_product(product):
    db.collection("products").document(product["product_id"]).set(product)
    return product


def get_product_by_id(product_id):
    if not product_id:
        return None
    doc = db.collection("products").document(product_id).get()
    if not doc.exists:
        return None
    product = doc.to_dict()
    if "product_id" not in product:
        product["product_id"] = doc.id
    return product

def get_product_by_detail(detail):
    if not detail:
        return None

    detail_clean = str(detail).strip().lower()
    if not detail_clean:
        return None

    docs = db.collection("products").stream()
    exact_match = None
    partial_matches = []

    for d in docs:
        product = d.to_dict()
        if "product_id" not in product:
            product["product_id"] = d.id

        product_detail = str(product.get("detail", "")).strip().lower()
        if product_detail == detail_clean:
            exact_match = product
            break
        if detail_clean in product_detail:
            partial_matches.append(product)

    if exact_match:
        return exact_match
    if len(partial_matches) == 1:
        return partial_matches[0]
    return None


def list_products(limit=100):
    docs = db.collection("products").limit(limit).stream()
    products = []
    for d in docs:
        product = d.to_dict()
        if "product_id" not in product:
            product["product_id"] = d.id
        products.append(product)
    return products

def save_purchase(order):
    db.collection("purchase_orders").document(order["id"]).set(order)
    return order

def list_purchase_orders(user_id=None, date=None, status=None, limit=20):
    docs = db.collection("purchase_orders").stream()
    orders = []

    for d in docs:
        order = d.to_dict()
        if "id" not in order:
            order["id"] = d.id

        if user_id and order.get("user_id") != user_id:
            continue
        if status and order.get("status") != status:
            continue
        if date and not str(order.get("purchase_date", "")).startswith(date):
            continue

        orders.append(order)

    orders.sort(key=lambda o: str(o.get("purchase_date", "")), reverse=True)
    try:
        limit_value = int(limit)
    except (TypeError, ValueError):
        limit_value = 20
    return orders[: max(1, limit_value)]

def get_purchase_order_by_id(order_id):
    if not order_id:
        return None
    doc = db.collection("purchase_orders").document(order_id).get()
    if not doc.exists:
        return None
    order = doc.to_dict()
    if "id" not in order:
        order["id"] = doc.id
    return order

def delete_purchase_order(order_id):
    order = get_purchase_order_by_id(order_id)
    if not order:
        return None
    db.collection("purchase_orders").document(order_id).delete()
    return order

def save_chat(user_id, message):
    db.collection("sessions").document(user_id).collection("messages").add(message)

def get_chat_history(user_id):
    docs = db.collection("sessions").document(user_id).collection("messages").stream()
    return [d.to_dict() for d in docs]
