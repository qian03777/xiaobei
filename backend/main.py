"""Google Sign-In + Cloud SQL order API scaffold for the Xiaobei demo."""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from typing import List, Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
INSTANCE_CONNECTION_NAME = os.getenv("INSTANCE_CONNECTION_NAME", "")
DB_NAME = os.getenv("DB_NAME", "xiaobei")
DB_USER = os.getenv("DB_USER", "xiaobei_app")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_IP_TYPE = os.getenv("DB_IP_TYPE", "PUBLIC").upper()
DATABASE_URL = os.getenv("DATABASE_URL", "")
PUBLIC_API_URL = os.getenv("PUBLIC_API_URL", "").rstrip("/")
QR_SIGNING_SECRET = os.getenv("QR_SIGNING_SECRET", "")
ALLOWED_ORIGINS = [x.strip() for x in os.getenv("ALLOWED_ORIGINS", "https://qian03777.github.io").split(",") if x.strip()]

app = FastAPI(title="Xiaobei Orders API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    if DATABASE_URL:
        database_url = DATABASE_URL
        if database_url.startswith("postgres://"):
            database_url = "postgresql+pg8000://" + database_url[len("postgres://"):]
        elif database_url.startswith("postgresql://"):
            database_url = "postgresql+pg8000://" + database_url[len("postgresql://"):]
        return create_engine(database_url, pool_pre_ping=True, pool_size=5, max_overflow=2)
    if not INSTANCE_CONNECTION_NAME:
        raise RuntimeError("Cloud SQL is not configured: set INSTANCE_CONNECTION_NAME.")
    from google.cloud.sql.connector import Connector, IPTypes

    connector = Connector(refresh_strategy="LAZY")

    def getconn():
        return connector.connect(
            INSTANCE_CONNECTION_NAME,
            "pg8000",
            user=DB_USER,
            password=DB_PASSWORD,
            db=DB_NAME,
            ip_type=IPTypes.PRIVATE if DB_IP_TYPE == "PRIVATE" else IPTypes.PUBLIC,
        )

    return create_engine("postgresql+pg8000://", creator=getconn, pool_pre_ping=True, pool_size=5, max_overflow=2)


def current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google Sign-In is not configured.")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Sign in with Google first.")
    token = authorization.split(" ", 1)[1].strip()
    try:
        claims = id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)
    except Exception:
        raise HTTPException(status_code=401, detail="Google sign-in token is invalid or expired.")
    if not claims.get("email_verified"):
        raise HTTPException(status_code=403, detail="A verified Google email is required.")
    return {"sub": claims["sub"], "email": claims.get("email", ""), "name": claims.get("name", "")}


class OrderLine(BaseModel):
    productId: str = Field(min_length=1, max_length=100)
    quantity: int = Field(gt=0, le=30)


class CreateOrder(BaseModel):
    storeId: str = Field(min_length=1, max_length=120)
    items: List[OrderLine] = Field(min_length=1, max_length=30)
    paymentMethod: Literal["pickup", "online"] = "pickup"
    contactName: Optional[str] = Field(default=None, max_length=80)
    contactPhone: str = Field(min_length=8, max_length=24)
    couponCode: Optional[str] = Field(default=None, max_length=80)
    useShoppingCredit: bool = False


def ensure_member(conn, user: dict):
    row = conn.execute(text("SELECT google_sub,email,display_name,shopping_credit_twd FROM members WHERE google_sub=:sub FOR UPDATE"), {"sub": user["sub"]}).mappings().first()
    if row:
        conn.execute(text("UPDATE members SET email=:email,display_name=:name,updated_at=NOW() WHERE google_sub=:sub"), {"email": user["email"], "name": user["name"], "sub": user["sub"]})
        return conn.execute(text("SELECT google_sub,email,display_name,shopping_credit_twd FROM members WHERE google_sub=:sub"), {"sub": user["sub"]}).mappings().first()
    conn.execute(text("INSERT INTO members (google_sub,email,display_name,shopping_credit_twd) VALUES (:sub,:email,:name,50) ON CONFLICT (google_sub) DO UPDATE SET email=EXCLUDED.email,display_name=EXCLUDED.display_name,updated_at=NOW()"), {"sub": user["sub"], "email": user["email"], "name": user["name"]})
    conn.execute(text("INSERT INTO member_coupons (google_sub,coupon_code,title,discount_twd,min_spend_twd) VALUES (:sub,'WELCOME30','新會員滿額折抵券',30,299),(:sub,'SEASON20','季度生活提案券',20,199) ON CONFLICT (google_sub,coupon_code) DO NOTHING"), {"sub": user["sub"]})
    return conn.execute(text("SELECT google_sub,email,display_name,shopping_credit_twd FROM members WHERE google_sub=:sub"), {"sub": user["sub"]}).mappings().first()


def pickup_signature(order_code: str) -> str:
    if not QR_SIGNING_SECRET:
        raise HTTPException(status_code=503, detail="QR_SIGNING_SECRET is not configured.")
    return hmac.new(QR_SIGNING_SECRET.encode("utf-8"), order_code.encode("utf-8"), hashlib.sha256).hexdigest()


def pickup_url(order_code: str, request_base: str = "") -> str:
    base = PUBLIC_API_URL or request_base.rstrip("/")
    return f"{base}/api/pickup/{order_code}?sig={pickup_signature(order_code)}"


@app.get("/api/health")
def health():
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"ok": True, "database": "connected", "llm": False, "mode": "google-cloud-sql"}
    except Exception as exc:
        return {"ok": False, "database": "unavailable", "llm": False, "detail": "Database connection unavailable."}


@app.get("/api/stores")
def list_stores(city: Optional[str] = Query(default=None), district: Optional[str] = Query(default=None), q: Optional[str] = Query(default=None)):
    filters = ["is_active=TRUE"]
    params = {}
    if city:
        filters.append("city=:city"); params["city"] = city
    if district:
        filters.append("district=:district"); params["district"] = district
    if q:
        filters.append("(name ILIKE :q OR address ILIKE :q)"); params["q"] = f"%{q}%"
    with get_engine().connect() as conn:
        rows = conn.execute(text("SELECT id,name,city,district,address,phone,hours,services,maps_url FROM stores WHERE " + " AND ".join(filters) + " ORDER BY city,district,name"), params).mappings().all()
    return {"stores": [dict(row) for row in rows]}


@app.get("/api/products")
def list_products(q: Optional[str] = Query(default=None), category: Optional[str] = Query(default=None), store_id: Optional[str] = Query(default=None)):
    filters = ["p.is_active=TRUE"]
    params = {}
    if q:
        filters.append("(p.name ILIKE :q OR p.category ILIKE :q OR p.keywords ILIKE :q)"); params["q"] = f"%{q}%"
    if category:
        filters.append("p.category=:category"); params["category"] = category
    if store_id:
        filters.append("EXISTS (SELECT 1 FROM inventory i WHERE i.product_id=p.id AND i.store_id=:store_id AND i.quantity>0)"); params["store_id"] = store_id
    params["store_id"] = store_id
    with get_engine().connect() as conn:
        rows = conn.execute(text("SELECT p.id,p.name,p.category,p.description,p.aisle,p.price_twd,COALESCE(SUM(i.quantity),0) AS quantity FROM products p LEFT JOIN inventory i ON i.product_id=p.id AND (:store_id IS NULL OR i.store_id=:store_id) WHERE " + " AND ".join(filters) + " GROUP BY p.id,p.name,p.category,p.description,p.aisle,p.price_twd ORDER BY p.category,p.name LIMIT 200"), params).mappings().all()
    return {"products": [dict(row) for row in rows]}


@app.get("/api/me")
def get_me(user=Depends(current_user)):
    with get_engine().begin() as conn:
        member = ensure_member(conn, user)
        coupons = conn.execute(text("SELECT coupon_code,title,discount_twd,min_spend_twd,is_used,expires_at FROM member_coupons WHERE google_sub=:sub ORDER BY id"), {"sub": user["sub"]}).mappings().all()
    return {"googleSub": member["google_sub"], "email": member["email"], "displayName": member["display_name"], "shoppingCredit": member["shopping_credit_twd"], "coupons": [{"id": c["coupon_code"], "name": c["title"], "discount": c["discount_twd"], "min": c["min_spend_twd"], "used": c["is_used"], "expiresAt": c["expires_at"].isoformat() if c["expires_at"] else None} for c in coupons]}


@app.post("/api/orders")
def create_order(body: CreateOrder, request: Request, user=Depends(current_user)):
    phone = re.sub(r"\D", "", body.contactPhone)
    if not re.fullmatch(r"(09\d{8}|8869\d{8})", phone):
        raise HTTPException(status_code=422, detail="Valid Taiwan mobile phone is required.")
    if body.paymentMethod == "online":
        if not body.contactName or len(body.contactName.strip()) < 2:
            raise HTTPException(status_code=422, detail="Contact name is required for online payment.")
        raise HTTPException(status_code=501, detail="Online payment gateway is not configured. Use pickup payment for now.")
    if not QR_SIGNING_SECRET:
        raise HTTPException(status_code=503, detail="QR_SIGNING_SECRET is not configured.")
    if len({item.productId for item in body.items}) != len(body.items):
        raise HTTPException(status_code=422, detail="Use one line per product.")

    order_uuid = str(uuid.uuid4())
    order_code = "XB-" + datetime.now(timezone.utc).strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:8].upper()
    with get_engine().begin() as conn:
        member = ensure_member(conn, user)
        store = conn.execute(text("SELECT id,name,address FROM stores WHERE id=:id AND is_active=TRUE"), {"id": body.storeId}).mappings().first()
        if not store:
            raise HTTPException(status_code=404, detail="Pickup store not found.")
        subtotal = 0
        items = []
        for requested in body.items:
            product = conn.execute(text("SELECT id,name,price_twd FROM products WHERE id=:id AND is_active=TRUE"), {"id": requested.productId}).mappings().first()
            inventory = conn.execute(text("SELECT quantity FROM inventory WHERE store_id=:store AND product_id=:product FOR UPDATE"), {"store": body.storeId, "product": requested.productId}).mappings().first()
            if not product or not inventory:
                raise HTTPException(status_code=404, detail="Product or store inventory not found.")
            if inventory["quantity"] < requested.quantity:
                raise HTTPException(status_code=409, detail=f"Insufficient stock for {product['name']}.")
            subtotal += product["price_twd"] * requested.quantity
            items.append({"productId": product["id"], "name": product["name"], "unitPrice": product["price_twd"], "quantity": requested.quantity})

        discount = 0
        coupon = None
        if body.couponCode:
            coupon = conn.execute(text("SELECT id,discount_twd,min_spend_twd FROM member_coupons WHERE google_sub=:sub AND coupon_code=:code AND is_used=FALSE AND (expires_at IS NULL OR expires_at>NOW()) FOR UPDATE"), {"sub": user["sub"], "code": body.couponCode}).mappings().first()
            if not coupon:
                raise HTTPException(status_code=409, detail="Coupon is unavailable or already used.")
            if subtotal < coupon["min_spend_twd"]:
                raise HTTPException(status_code=422, detail="Order does not meet coupon minimum spend.")
            discount = min(coupon["discount_twd"], subtotal)
        credit = min(member["shopping_credit_twd"], subtotal - discount) if body.useShoppingCredit else 0
        total = subtotal - discount - credit
        conn.execute(text("INSERT INTO orders (id,order_code,google_sub,store_id,payment_method,payment_status,fulfillment_status,contact_name,contact_phone,subtotal_twd,discount_twd,credit_used_twd,total_twd) VALUES (:id,:code,:sub,:store,'pickup','unpaid','pending_pickup','',:phone,:subtotal,:discount,:credit,:total)"), {"id": order_uuid, "code": order_code, "sub": user["sub"], "store": body.storeId, "phone": phone, "subtotal": subtotal, "discount": discount, "credit": credit, "total": total})
        for item in items:
            conn.execute(text("INSERT INTO order_items (order_id,product_id,product_name,unit_price_twd,quantity) VALUES (:order_id,:product_id,:name,:price,:quantity)"), {"order_id": order_uuid, "product_id": item["productId"], "name": item["name"], "price": item["unitPrice"], "quantity": item["quantity"]})
            conn.execute(text("UPDATE inventory SET quantity=quantity-:quantity,updated_at=NOW() WHERE store_id=:store AND product_id=:product"), {"quantity": item["quantity"], "store": body.storeId, "product": item["productId"]})
        if coupon:
            conn.execute(text("UPDATE member_coupons SET is_used=TRUE WHERE id=:id"), {"id": coupon["id"]})
        if credit:
            conn.execute(text("UPDATE members SET shopping_credit_twd=shopping_credit_twd-:credit,updated_at=NOW() WHERE google_sub=:sub"), {"credit": credit, "sub": user["sub"]})

    return {"code": order_code, "storeId": store["id"], "storeName": store["name"], "storeAddress": store["address"], "items": items, "subtotal": subtotal, "discount": discount, "creditUsed": credit, "total": total, "paymentMethod": "取貨付款", "paymentStatus": "未付", "status": "待取貨", "createdAt": datetime.now(timezone.utc).isoformat(), "pickupUrl": pickup_url(order_code, str(request.base_url))}


@app.get("/api/orders")
def list_orders(request: Request, user=Depends(current_user)):
    with get_engine().connect() as conn:
        orders = conn.execute(text("SELECT o.id,o.order_code,o.store_id,s.name AS store_name,s.address AS store_address,o.payment_method,o.payment_status,o.fulfillment_status,o.total_twd,o.created_at FROM orders o JOIN stores s ON s.id=o.store_id WHERE o.google_sub=:sub ORDER BY o.created_at DESC LIMIT 100"), {"sub": user["sub"]}).mappings().all()
        result = []
        for order in orders:
            items = conn.execute(text("SELECT product_id AS id,product_name AS name,unit_price_twd AS price,quantity AS qty FROM order_items WHERE order_id=:id ORDER BY id"), {"id": order["id"]}).mappings().all()
            result.append({"code": order["order_code"], "storeId": order["store_id"], "storeName": order["store_name"], "storeAddress": order["store_address"], "items": [dict(i) for i in items], "total": order["total_twd"], "paymentMethod": order["payment_method"], "paymentStatus": "已付" if order["payment_status"] == "paid" else "未付", "status": "待取貨" if order["fulfillment_status"] == "pending_pickup" else order["fulfillment_status"], "createdAt": order["created_at"].isoformat(), "pickupUrl": pickup_url(order["order_code"], str(request.base_url))})
    return {"orders": result}


@app.get("/api/pickup/{order_code}")
def verify_pickup_qr(order_code: str, sig: str = Query(...)):
    expected = pickup_signature(order_code)
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(status_code=403, detail="Invalid pickup code.")
    with get_engine().connect() as conn:
        order = conn.execute(text("SELECT o.order_code,s.name AS store_name,s.address AS store_address,o.payment_method,o.payment_status,o.fulfillment_status,o.total_twd,o.created_at FROM orders o JOIN stores s ON s.id=o.store_id WHERE o.order_code=:code"), {"code": order_code}).mappings().first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found.")
        items = conn.execute(text("SELECT product_name AS name,quantity AS qty FROM order_items WHERE order_id=(SELECT id FROM orders WHERE order_code=:code) ORDER BY id"), {"code": order_code}).mappings().all()
    return {"orderCode": order["order_code"], "store": order["store_name"], "storeAddress": order["store_address"], "items": [dict(i) for i in items], "paymentStatus": order["payment_status"], "fulfillmentStatus": order["fulfillment_status"], "total": order["total_twd"], "createdAt": order["created_at"].isoformat()}
