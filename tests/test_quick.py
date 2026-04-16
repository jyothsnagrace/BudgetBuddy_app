#!/usr/bin/env python3
"""Quick test for expense parsing"""

import requests

# Login first
print("Logging in...")
login_response = requests.post(
    "http://localhost:8000/api/auth/login",
    json={"username": "admin", "password": "admin123"}
)

if login_response.status_code == 200:
    token = login_response.json()["token"]
    print(f"✓ Login successful")
    
    # Test parse expense
    print("\nTesting parse expense...")
    response = requests.post(
        "http://localhost:8000/api/parse-expense",
        headers={"Authorization": f"Bearer {token}"},
        json={"text": "I spent 25 dollars on lunch"}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
else:
    print(f"Login failed: {login_response.status_code}")
