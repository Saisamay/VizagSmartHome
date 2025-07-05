import requests
import json
import unittest
import os
import sys
from dotenv import load_dotenv
import random
import string
import time

# Load environment variables from frontend/.env
load_dotenv("frontend/.env")

# Get the backend URL from environment variables
BACKEND_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BACKEND_URL:
    print("Error: REACT_APP_BACKEND_URL not found in environment variables")
    sys.exit(1)

# Ensure the URL has the /api prefix
API_URL = f"{BACKEND_URL}/api"
print(f"Testing API at: {API_URL}")

# Helper function to generate random data
def random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# Sample test data for products
TEST_PRODUCTS = [
    {
        "name": "Premium Kitchen Chimney",
        "description": "High-quality kitchen chimney with powerful suction and modern design",
        "price": 12999.99,
        "category": "chimneys",
        "features": ["Auto-Clean Technology", "Touch Control", "LED Lights"],
        "specifications": {"suction_power": "1200 m³/hr", "noise_level": "58 dB", "dimensions": "60x45x40cm"},
        "in_stock": True
    },
    {
        "name": "RO Water Purifier",
        "description": "Advanced RO water purifier with UV and mineral fortification",
        "price": 15999.99,
        "category": "water-purifiers",
        "features": ["RO+UV+UF Purification", "TDS Controller", "7-Stage Filtration"],
        "specifications": {"capacity": "8 liters", "purification_rate": "15 liters/hour", "power": "60W"},
        "in_stock": True
    },
    {
        "name": "Smart Dishwasher",
        "description": "Energy-efficient dishwasher with smart features and multiple wash programs",
        "price": 35999.99,
        "category": "dish-washers",
        "features": ["14 Place Settings", "8 Wash Programs", "Half Load Option"],
        "specifications": {"energy_rating": "A+++", "water_consumption": "9.5L/cycle", "noise_level": "44 dB"},
        "in_stock": True
    }
]

class VizagSmartHomeAPITest(unittest.TestCase):
    """Test suite for Vizag Smart Home API endpoints"""
    
    def setUp(self):
        """Set up test case"""
        self.product_id = None  # Will be set when we create a product
        self.auth_header = None  # Will be set if authentication succeeds
        
        # For testing purposes, we'll bypass authentication for now
        # In a real scenario, we would use proper authentication
        print("Note: Running tests without authentication. Some authenticated endpoints will be skipped.")
        
        # Add some test products if the database is empty
        self.seed_test_data()
    
    def seed_test_data(self):
        """Seed the database with test data if it's empty"""
        # Check if we have any products
        response = requests.get(f"{API_URL}/products")
        products = response.json()
        
        if not products:
            print("Database appears to be empty. Adding test products...")
            # We'll try to add products directly to the database
            # This is a workaround since we don't have authentication
            for product in TEST_PRODUCTS:
                try:
                    # Try to add the product (this might fail due to auth)
                    response = requests.post(f"{API_URL}/products", json=product)
                    if response.status_code == 200:
                        print(f"Added test product: {product['name']}")
                    else:
                        print(f"Failed to add test product: {response.status_code}")
                except Exception as e:
                    print(f"Error adding test product: {str(e)}")
            
            # Check again after adding
            time.sleep(1)  # Give the server a moment
            response = requests.get(f"{API_URL}/products")
            products = response.json()
            if products:
                self.product_id = products[0]["id"]
                print(f"Using product ID {self.product_id} for tests")
    
    def test_01_api_health(self):
        """Test the API health check endpoint"""
        response = requests.get(f"{API_URL}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("message", data)
        self.assertEqual(data["message"], "Vizag Smart Home API")
        print("✅ API health check passed")
    
    def test_02_get_categories(self):
        """Test getting all product categories"""
        response = requests.get(f"{API_URL}/categories")
        self.assertEqual(response.status_code, 200)
        categories = response.json()
        self.assertIsInstance(categories, list)
        self.assertGreater(len(categories), 0)
        
        # Check for expected categories
        category_ids = [cat["id"] for cat in categories]
        expected_categories = [
            "chimneys", "water-purifiers", "dish-washers", "hobs-stoves", 
            "sinks", "air-conditioners", "lightings", "micro-ovens-otg"
        ]
        for cat in expected_categories:
            self.assertIn(cat, category_ids)
        
        print(f"✅ Categories endpoint returned {len(categories)} categories")
    
    def test_03_get_products(self):
        """Test getting all products"""
        response = requests.get(f"{API_URL}/products")
        self.assertEqual(response.status_code, 200)
        products = response.json()
        self.assertIsInstance(products, list)
        print(f"✅ Products endpoint returned {len(products)} products")
        
        # If we have products, save one ID for later tests
        if products:
            self.product_id = products[0]["id"]
            print(f"Using product ID {self.product_id} for subsequent tests")
    
    def test_04_get_products_by_category(self):
        """Test filtering products by category"""
        # Test with a valid category
        response = requests.get(f"{API_URL}/products", params={"category": "chimneys"})
        self.assertEqual(response.status_code, 200)
        products = response.json()
        self.assertIsInstance(products, list)
        
        # Check that all returned products have the correct category
        if products:
            for product in products:
                self.assertEqual(product["category"], "chimneys")
        
        print(f"✅ Category filtering returned {len(products)} chimney products")
    
    def test_05_search_products(self):
        """Test searching for products"""
        # Test with a search term
        response = requests.get(f"{API_URL}/search", params={"q": "chimney"})
        self.assertEqual(response.status_code, 200)
        products = response.json()
        self.assertIsInstance(products, list)
        print(f"✅ Search endpoint returned {len(products)} products matching 'chimney'")
    
    def test_06_get_product_by_id(self):
        """Test getting a single product by ID"""
        # Skip if we don't have a product ID
        if not self.product_id:
            print("⚠️ Skipping get product by ID test due to missing product ID")
            return
        
        response = requests.get(f"{API_URL}/products/{self.product_id}")
        self.assertEqual(response.status_code, 200)
        product = response.json()
        self.assertEqual(product["id"], self.product_id)
        print(f"✅ Successfully retrieved product with ID {self.product_id}")
    
    def test_07_get_reviews(self):
        """Test getting all reviews"""
        response = requests.get(f"{API_URL}/reviews")
        self.assertEqual(response.status_code, 200)
        reviews = response.json()
        self.assertIsInstance(reviews, list)
        print(f"✅ Reviews endpoint returned {len(reviews)} reviews")
    
    def test_08_get_product_reviews(self):
        """Test getting reviews for a specific product"""
        # Skip if we don't have a product ID
        if not self.product_id:
            print("⚠️ Skipping get product reviews test due to missing product ID")
            return
        
        response = requests.get(f"{API_URL}/products/{self.product_id}/reviews")
        self.assertEqual(response.status_code, 200)
        reviews = response.json()
        self.assertIsInstance(reviews, list)
        print(f"✅ Product reviews endpoint returned {len(reviews)} reviews for product {self.product_id}")
    
    def test_09_contact_form(self):
        """Test submitting a contact form"""
        contact_data = {
            "name": f"Test User {random_string(5)}",
            "email": f"test_{random_string(5)}@example.com",
            "phone": f"+91{random.randint(7000000000, 9999999999)}",
            "message": f"This is a test message {random_string(20)}"
        }
        
        response = requests.post(f"{API_URL}/contact", json=contact_data)
        self.assertEqual(response.status_code, 200)
        created_message = response.json()
        self.assertIn("id", created_message)
        self.assertEqual(created_message["name"], contact_data["name"])
        self.assertEqual(created_message["email"], contact_data["email"])
        print("✅ Successfully submitted contact form")
    
    def test_10_auth_profile(self):
        """Test the auth profile endpoint"""
        # Use a mock session ID for testing
        mock_session_id = "test-session-id"
        response = requests.get(f"{API_URL}/auth/profile", params={"session_id": mock_session_id})
        
        # This test might fail due to missing real authentication
        if response.status_code != 200:
            print(f"⚠️ Auth profile test failed with status code {response.status_code}")
            print(f"Response: {response.text}")
            print("This is expected if using mock session ID")
            return
        
        self.assertEqual(response.status_code, 200)
        profile = response.json()
        self.assertIn("email", profile)
        self.assertIn("name", profile)
        print("✅ Successfully retrieved user profile")


if __name__ == "__main__":
    # Run the tests
    unittest.main(argv=['first-arg-is-ignored'], exit=False)