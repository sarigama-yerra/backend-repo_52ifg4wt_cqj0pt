import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import (
    User, Product, ProductCreate, ProductOut, RegisterRequest, LoginRequest,
    CartItem, CartItemOut
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Utils

def to_str_id(doc):
    if not doc:
        return doc
    doc["id"] = str(doc.pop("_id"))
    return doc


def hash_password(plain: str) -> str:
    # Simple demo hash using sha256; in production use bcrypt
    import hashlib
    return hashlib.sha256(plain.encode()).hexdigest()


@app.get("/")
def read_root():
    return {"message": "Marketplace API ready"}


@app.get("/schema")
def get_schema():
    # Provide schemas description for viewer (simple signal)
    return {"schemas": ["user", "product", "cartitem"]}


# Auth endpoints
@app.post("/auth/register")
def register(payload: RegisterRequest):
    # check if email exists
    existing = db["user"].find_one({"email": payload.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        avatar_url=None,
        is_active=True,
    )
    user_id = create_document("user", user)
    return {"id": user_id, "name": user.name, "email": user.email}


@app.post("/auth/login")
def login(payload: LoginRequest):
    user = db["user"].find_one({"email": payload.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.get("password_hash") != hash_password(payload.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"token": str(user["_id"]), "user": {"id": str(user["_id"]), "name": user["name"], "email": user["email"]}}


# Products
@app.post("/products", response_model=ProductOut)
def create_product(payload: ProductCreate, token: Optional[str] = None):
    seller_id = token or None
    product = Product(
        title=payload.title,
        description=payload.description,
        price=payload.price,
        category=payload.category,
        images=payload.images or [],
        seller_id=seller_id,
        flash_sale=payload.flash_sale,
        in_stock=payload.in_stock,
    )
    pid = create_document("product", product)
    created = db["product"].find_one({"_id": ObjectId(pid)})
    return ProductOut(**to_str_id(created))


@app.get("/products", response_model=List[ProductOut])
def list_products(q: Optional[str] = None, flash_only: bool = False):
    filter_dict = {}
    if q:
        filter_dict["title"] = {"$regex": q, "$options": "i"}
    if flash_only:
        filter_dict["flash_sale"] = {"$ne": None}

    docs = get_documents("product", filter_dict=filter_dict)
    return [ProductOut(**to_str_id(d)) for d in docs]


# Cart
@app.post("/cart/add", response_model=CartItemOut)
def add_to_cart(item: CartItem):
    # Upsert behavior: increase quantity if exists
    existing = db["cartitem"].find_one({"user_id": item.user_id, "product_id": item.product_id})
    if existing:
        new_qty = min(10, existing.get("quantity", 1) + item.quantity)
        db["cartitem"].update_one({"_id": existing["_id"]}, {"$set": {"quantity": new_qty, "updated_at": datetime.now(timezone.utc)}})
        existing["quantity"] = new_qty
        return CartItemOut(id=str(existing["_id"]), product_id=existing["product_id"], quantity=new_qty)

    cid = create_document("cartitem", item)
    created = db["cartitem"].find_one({"_id": ObjectId(cid)})
    return CartItemOut(id=str(created["_id"]), product_id=created["product_id"], quantity=created["quantity"]) 


@app.get("/cart/{user_id}", response_model=List[CartItemOut])
def get_cart(user_id: str):
    docs = get_documents("cartitem", {"user_id": user_id})
    return [CartItemOut(id=str(d["_id"]), product_id=d["product_id"], quantity=d["quantity"]) for d in docs]


# Flash sales helper endpoint
@app.get("/flash", response_model=List[ProductOut])
def flash_sales():
    now = datetime.now(timezone.utc)
    docs = db["product"].find({"flash_sale.ends_at": {"$gt": now}}).sort("flash_sale.ends_at", 1)
    return [ProductOut(**to_str_id(d)) for d in docs]


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
