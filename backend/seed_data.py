"""Initialize Cloud SQL from the official store snapshot and demo catalog."""
import json
from pathlib import Path

from sqlalchemy import text

from main import get_engine

ROOT = Path(__file__).resolve().parents[1]
STORES = json.loads((ROOT / "stores-tw.json").read_text(encoding="utf-8"))["stores"]
PRODUCTS = json.loads((Path(__file__).resolve().parent / "products-seed.json").read_text(encoding="utf-8"))
SPECIAL_STOCK = {
    "kunda": {"laundry": 18, "bath-cleaner": 12, "storage": 7, "mini-cooker": 5, "hair-dryer": 7},
    "kegong": {"laundry": 11, "bath-cleaner": 6, "storage": 5, "mini-cooker": 2, "hair-dryer": 3},
    "madou": {"laundry": 9, "bath-cleaner": 10, "storage": 12, "mini-cooker": 3, "hair-dryer": 4},
}


def main():
    engine = get_engine()
    schema = (Path(__file__).resolve().parent / "schema.sql").read_text(encoding="utf-8")
    statements = [part.strip() for part in schema.split(";") if part.strip()]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
        for store in STORES:
            conn.execute(text("""
                INSERT INTO stores (id,name,city,district,address,phone,hours,services,maps_url,is_active)
                VALUES (:id,:name,:city,:district,:address,:phone,:hours,:services,:maps_url,TRUE)
                ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name,city=EXCLUDED.city,
                district=EXCLUDED.district,address=EXCLUDED.address,phone=EXCLUDED.phone,
                hours=EXCLUDED.hours,services=EXCLUDED.services,maps_url=EXCLUDED.maps_url,is_active=TRUE
            """), {"id": store["id"], "name": store["name"], "city": store.get("city", ""), "district": store.get("district", ""), "address": store["address"], "phone": store.get("phone", ""), "hours": store.get("hours", ""), "services": store.get("services", ""), "maps_url": store.get("mapsUrl", "")})
        for product in PRODUCTS:
            conn.execute(text("""
                INSERT INTO products (id,name,category,description,keywords,aisle,price_twd,is_active)
                VALUES (:id,:name,:category,:description,:keywords,:aisle,:price,TRUE)
                ON CONFLICT (id) DO NOTHING
            """), {"id": product["id"], "name": product["name"], "category": product.get("category", ""), "description": product.get("description", ""), "keywords": product.get("keywords", ""), "aisle": product.get("aisle", ""), "price": int(product["price"])})
        for store_index, store in enumerate(STORES):
            for product_index, product in enumerate(PRODUCTS):
                quantity = SPECIAL_STOCK.get(store["id"], {}).get(product["id"])
                if quantity is None:
                    quantity = (store_index * 7 + product_index * 11) % 16 + 1
                conn.execute(text("""
                    INSERT INTO inventory (store_id,product_id,quantity)
                    VALUES (:store_id,:product_id,:quantity)
                    ON CONFLICT (store_id,product_id) DO NOTHING
                """), {"store_id": store["id"], "product_id": product["id"], "quantity": quantity})
    print(f"Seeded {len(STORES)} stores, {len(PRODUCTS)} representative products and inventory rows.")
    print("Inventory is simulated; replace it with POS/WMS synchronization before production.")


if __name__ == "__main__":
    main()
