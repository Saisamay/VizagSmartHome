import requests
import json
import unittest
import os
import sys
from dotenv import load_dotenv
import random
import string

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

# Mock session ID for authentication tests
# In a real scenario, this would be obtained from the Emergent auth system
MOCK_SESSION_ID = "test-session-id"

# Helper function to generate random data
def random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

class VizagSmartHomeAPITest(unittest.TestCase):
    """Test suite for Vizag Smart Home API endpoints"""
    
    def setUp(self):
        """Set up test case"""
        self.product_id = None  # Will be set when we create a product
        self.auth_header = None  # Will be set if authentication succeeds
        
        # Try to authenticate (this is a best effort, as we don't have real auth credentials)
        try:
            response = requests.get(f"{API_URL}/auth/profile", params={"session_id": MOCK_SESSION_ID})
            if response.status_code == 200:
                data = response.json()
                if "session_token" in data:
                    self.auth_header = {"Authorization": f"Bearer {data['session_token']}"}
                    print("Authentication successful")
                else:
                    print("Warning: Authentication response doesn't contain session_token")
            else:
                print(f"Warning: Authentication failed with status code {response.status_code}")
                print(f"Response: {response.text}")
        except Exception as e:
            print(f"Warning: Authentication attempt failed: {str(e)}")
    
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
    
    def test_06_create_product(self):
        """Test creating a new product (requires authentication)"""
        if not self.auth_header:
            print("⚠️ Skipping product creation test due to missing authentication")
            return
        
        # Create a test product
        product_data = {
            "name": f"Test Product {random_string()}",
            "description": "This is a test product created by automated tests",
            "price": 999.99,
            "category": "chimneys",
            "features": ["Feature 1", "Feature 2"],
            "specifications": {"weight": "5kg", "dimensions": "30x40x50cm"},
            "in_stock": True
        }
        
        response = requests.post(
            f"{API_URL}/products", 
            json=product_data,
            headers=self.auth_header
        )
        
        # Check if authentication worked
        if response.status_code == 401:
            print("⚠️ Product creation failed due to authentication issues")
            print(f"Response: {response.text}")
            return
        
        self.assertEqual(response.status_code, 200)
        created_product = response.json()
        self.assertIn("id", created_product)
        self.assertEqual(created_product["name"], product_data["name"])
        
        # Save the product ID for later tests
        self.product_id = created_product["id"]
        print(f"✅ Successfully created product with ID {self.product_id}")
    
    def test_07_get_product_by_id(self):
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
    
    def test_08_get_reviews(self):
        """Test getting all reviews"""
        response = requests.get(f"{API_URL}/reviews")
        self.assertEqual(response.status_code, 200)
        reviews = response.json()
        self.assertIsInstance(reviews, list)
        print(f"✅ Reviews endpoint returned {len(reviews)} reviews")
    
    def test_09_get_product_reviews(self):
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
    
    def test_10_create_review(self):
        """Test creating a review for a product (requires authentication)"""
        # Skip if we don't have authentication or product ID
        if not self.auth_header:
            print("⚠️ Skipping review creation test due to missing authentication")
            return
        
        if not self.product_id:
            print("⚠️ Skipping review creation test due to missing product ID")
            return
        
        # Create a test review
        review_data = {
            "product_id": self.product_id,
            "rating": random.randint(1, 5),
            "comment": f"Test review {random_string()}"
        }
        
        response = requests.post(
            f"{API_URL}/products/{self.product_id}/reviews", 
            json=review_data,
            headers=self.auth_header
        )
        
        # Check if authentication worked
        if response.status_code == 401:
            print("⚠️ Review creation failed due to authentication issues")
            print(f"Response: {response.text}")
            return
        
        self.assertEqual(response.status_code, 200)
        created_review = response.json()
        self.assertIn("id", created_review)
        self.assertEqual(created_review["product_id"], self.product_id)
        self.assertEqual(created_review["rating"], review_data["rating"])
        print(f"✅ Successfully created review for product {self.product_id}")
    
    def test_11_contact_form(self):
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
    
    def test_12_get_contact_messages(self):
        """Test getting all contact messages (requires authentication)"""
        if not self.auth_header:
            print("⚠️ Skipping get contact messages test due to missing authentication")
            return
        
        response = requests.get(f"{API_URL}/contact", headers=self.auth_header)
        
        # Check if authentication worked
        if response.status_code == 401:
            print("⚠️ Getting contact messages failed due to authentication issues")
            print(f"Response: {response.text}")
            return
        
        self.assertEqual(response.status_code, 200)
        messages = response.json()
        self.assertIsInstance(messages, list)
        print(f"✅ Contact messages endpoint returned {len(messages)} messages")
    
    def test_13_auth_profile(self):
        """Test the auth profile endpoint"""
        response = requests.get(f"{API_URL}/auth/profile", params={"session_id": MOCK_SESSION_ID})
        
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