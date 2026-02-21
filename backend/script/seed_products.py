import argparse
import random
from pathlib import Path
import sys

from dotenv import load_dotenv


CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from infrastructure.firebase_service import save_product  # noqa: E402


load_dotenv()


ADJECTIVES = [
    "Industrial",
    "Premium",
    "Compact",
    "Smart",
    "Wireless",
    "Heavy Duty",
    "Eco",
    "High-Performance",
    "Portable",
    "Advanced",
]

NOUNS = [
    "Laptop",
    "Monitor",
    "Keyboard",
    "Mouse",
    "Headset",
    "Router",
    "Printer",
    "Scanner",
    "Docking Station",
    "Projector",
]


def random_product(index):
    adjective = random.choice(ADJECTIVES)
    noun = random.choice(NOUNS)
    product_id = f"PRD-{index:04d}"
    detail = f"{adjective} {noun} {index:02d}"
    price = round(random.uniform(25, 2500), 2)
    return {
        "product_id": product_id,
        "detail": detail,
        "price": price,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Seed Firebase products collection with random products."
    )
    parser.add_argument("--n", type=int, default=50, help="Number of products to insert")
    args = parser.parse_args()

    if args.n <= 0:
        raise ValueError("--n debe ser mayor a 0")

    for i in range(1, args.n + 1):
        save_product(random_product(i))

    print(f"Inserted {args.n} products into 'products' collection.")


if __name__ == "__main__":
    main()
