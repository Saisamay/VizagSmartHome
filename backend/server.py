from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime
import httpx
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Vizag Smart Home API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()

# Define Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    picture: Optional[str] = None
    session_token: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    price: float
    category: str
    image_base64: Optional[str] = None
    features: List[str] = []
    specifications: dict = {}
    in_stock: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ProductCreate(BaseModel):
    name: str
    description: str
    price: float
    category: str
    image_base64: Optional[str] = None
    features: List[str] = []
    specifications: dict = {}
    in_stock: bool = True

class Review(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    user_id: str
    user_name: str
    rating: int = Field(ge=1, le=5)
    comment: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ReviewCreate(BaseModel):
    product_id: str
    rating: int = Field(ge=1, le=5)
    comment: str

class ContactMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    phone: Optional[str] = None
    message: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ContactMessageCreate(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    message: str

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    user = await db.users.find_one({"session_token": token})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session token")
    return User(**user)

# Authentication routes
@api_router.get("/auth/profile")
async def get_profile(session_id: str, request: Request):
    """Get user profile from Emergent auth API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": session_id}
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid session")
            
            auth_data = response.json()
            
            # Check if user exists
            existing_user = await db.users.find_one({"email": auth_data["email"]})
            
            if not existing_user:
                # Create new user
                new_user = User(
                    email=auth_data["email"],
                    name=auth_data["name"],
                    picture=auth_data.get("picture"),
                    session_token=auth_data["session_token"]
                )
                await db.users.insert_one(new_user.dict())
                return new_user
            else:
                # Update session token
                await db.users.update_one(
                    {"email": auth_data["email"]},
                    {"$set": {"session_token": auth_data["session_token"]}}
                )
                existing_user["session_token"] = auth_data["session_token"]
                return User(**existing_user)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")

# Product routes
@api_router.get("/products", response_model=List[Product])
async def get_products(category: Optional[str] = None):
    """Get all products or products by category"""
    if category:
        products = await db.products.find({"category": category}).to_list(1000)
    else:
        products = await db.products.find().to_list(1000)
    return [Product(**product) for product in products]

@api_router.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: str):
    """Get single product by ID"""
    product = await db.products.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return Product(**product)

@api_router.post("/products", response_model=Product)
async def create_product(product: ProductCreate, current_user: User = Depends(get_current_user)):
    """Create a new product (admin only)"""
    product_dict = product.dict()
    product_obj = Product(**product_dict)
    await db.products.insert_one(product_obj.dict())
    return product_obj

@api_router.get("/categories")
async def get_categories():
    """Get all product categories"""
    categories = [
        {"id": "chimneys", "name": "Chimneys", "description": "Kitchen chimneys and exhaust systems"},
        {"id": "water-purifiers", "name": "Water Purifiers", "description": "Water filtration and purification systems"},
        {"id": "dish-washers", "name": "Dish Washers", "description": "Automatic dishwashing machines"},
        {"id": "hobs-stoves", "name": "Hobs & Stoves", "description": "Gas and electric cooking hobs"},
        {"id": "sinks", "name": "Sinks", "description": "Kitchen and bathroom sinks"},
        {"id": "air-conditioners", "name": "Air Conditioners", "description": "Cooling and heating systems"},
        {"id": "lightings", "name": "Lightings", "description": "Smart lighting solutions"},
        {"id": "micro-ovens-otg", "name": "Micro Ovens & OTG", "description": "Microwave ovens and OTG units"}
    ]
    return categories

# Review routes
@api_router.get("/products/{product_id}/reviews", response_model=List[Review])
async def get_product_reviews(product_id: str):
    """Get all reviews for a product"""
    reviews = await db.reviews.find({"product_id": product_id}).to_list(1000)
    return [Review(**review) for review in reviews]

@api_router.post("/products/{product_id}/reviews", response_model=Review)
async def create_review(product_id: str, review: ReviewCreate, current_user: User = Depends(get_current_user)):
    """Create a new review for a product"""
    review_dict = review.dict()
    review_dict["user_id"] = current_user.id
    review_dict["user_name"] = current_user.name
    review_obj = Review(**review_dict)
    await db.reviews.insert_one(review_obj.dict())
    return review_obj

@api_router.get("/reviews", response_model=List[Review])
async def get_all_reviews():
    """Get all reviews"""
    reviews = await db.reviews.find().sort("created_at", -1).to_list(100)
    return [Review(**review) for review in reviews]

# Contact routes
@api_router.post("/contact", response_model=ContactMessage)
async def create_contact_message(contact: ContactMessageCreate):
    """Create a new contact message"""
    contact_dict = contact.dict()
    contact_obj = ContactMessage(**contact_dict)
    await db.contact_messages.insert_one(contact_obj.dict())
    return contact_obj

@api_router.get("/contact", response_model=List[ContactMessage])
async def get_contact_messages(current_user: User = Depends(get_current_user)):
    """Get all contact messages (admin only)"""
    messages = await db.contact_messages.find().sort("created_at", -1).to_list(1000)
    return [ContactMessage(**message) for message in messages]

# Search route
@api_router.get("/search", response_model=List[Product])
async def search_products(q: str):
    """Search products by name or description"""
    products = await db.products.find({
        "$or": [
            {"name": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}}
        ]
    }).to_list(1000)
    return [Product(**product) for product in products]

# Root route
@api_router.get("/")
async def root():
    return {"message": "Vizag Smart Home API"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()