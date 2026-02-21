import argparse
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path
import sys
from dotenv import load_dotenv

CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from infrastructure.firebase_service import save_purchase, list_products  # noqa: E402

# Cargar variables de entorno
load_dotenv()

JUSTIFICATIONS = [
    "Reposición de inventario.",
    "Nueva necesidad del equipo de operaciones.",
    "Renovación de equipos obsoletos.",
    "Soporte para crecimiento del área comercial.",
    "Estándar de actualización tecnológica.",
]


def random_purchase(user_id, products):
    product = random.choice(products)
    quantity = random.randint(1, 20)
    unit_price = float(product.get("price", 0))
    total_amount = round(quantity * unit_price, 2)
    return {
        "id": str(uuid.uuid4()),
        "purchase_date": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "action": "CREATE_PURCHASE_ORDER",
        "product_id": product["product_id"],
        "detail": product.get("detail", ""),
        "unit_price": unit_price,
        "quantity": quantity,
        "total_amount": total_amount,
        "justification": random.choice(JUSTIFICATIONS),
        "status": "EXECUTED",
    }

def main():
    parser = argparse.ArgumentParser(description="Seed Firebase with purchase orders.")
    parser.add_argument("--user_id", required=True, help="Owner user_id for generated orders")
    parser.add_argument("--n", type=int, default=50, help="Number of purchase orders to create")
    args = parser.parse_args()

    if args.n <= 0:
        raise ValueError("--n debe ser mayor a 0")

    products = list_products(limit=500)
    if not products:
        raise ValueError("No hay productos en la colección 'products'. Ejecuta seed_products primero.")

    for _ in range(args.n):
        order = random_purchase(args.user_id, products)
        save_purchase(order)
    print(f"Inserted {args.n} purchase_orders for user_id={args.user_id}.")

if __name__ == "__main__":
    main()
