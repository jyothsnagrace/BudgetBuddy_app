"""
Cost of Living API Integration
Uses RapidAPI for city cost-of-living data
Includes caching and graceful degradation
"""

import os
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import httpx
from cachetools import TTLCache

# API Configuration
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = "cost-of-living-and-prices.p.rapidapi.com"

# US Cities Database (Top 50)
US_CITIES = [
    "Atlanta, GA", "Austin, TX", "Baltimore, MD", "Boston, MA",
    "Charlotte, NC", "Chicago, IL", "Cleveland, OH", "Columbus, OH",
    "Dallas, TX", "Denver, CO", "Detroit, MI", "El Paso, TX",
    "Fort Worth, TX", "Houston, TX", "Indianapolis, IN", "Jacksonville, FL",
    "Kansas City, MO", "Las Vegas, NV", "Los Angeles, CA", "Memphis, TN",
    "Miami, FL", "Milwaukee, WI", "Minneapolis, MN", "Nashville, TN",
    "New Orleans, LA", "New York, NY", "Oakland, CA", "Oklahoma City, OK",
    "Orlando, FL", "Philadelphia, PA", "Phoenix, AZ", "Pittsburgh, PA",
    "Portland, OR", "Raleigh, NC", "Sacramento, CA", "San Antonio, TX",
    "San Diego, CA", "San Francisco, CA", "San Jose, CA", "Seattle, WA",
    "Tampa, FL", "Tucson, AZ", "Tulsa, OK", "Virginia Beach, VA",
    "Washington, DC"
]

# Fallback data for common cities (when API is unavailable)
FALLBACK_DATA = {
    "New York, NY": {
        "cost_index": 100,
        "rent_index": 100,
        "groceries_index": 100,
        "restaurant_index": 100
    },
    "San Francisco, CA": {
        "cost_index": 104.5,
        "rent_index": 145.2,
        "groceries_index": 108.3,
        "restaurant_index": 115.7
    },
    "Seattle, WA": {
        "cost_index": 89.3,
        "rent_index": 92.5,
        "groceries_index": 95.1,
        "restaurant_index": 88.4
    },
    "Austin, TX": {
        "cost_index": 73.4,
        "rent_index": 68.2,
        "groceries_index": 78.9,
        "restaurant_index": 76.2
    },
    "Chicago, IL": {
        "cost_index": 79.8,
        "rent_index": 72.4,
        "groceries_index": 82.1,
        "restaurant_index": 79.6
    },
    "Los Angeles, CA": {
        "cost_index": 85.7,
        "rent_index": 95.3,
        "groceries_index": 88.4,
        "restaurant_index": 87.2
    }
}


class CostOfLivingAPI:
    """Cost of Living API client with caching and fallback"""
    
    def __init__(self):
        self.api_key = RAPIDAPI_KEY
        self.cache = TTLCache(maxsize=100, ttl=86400)  # 24-hour cache
        self.rate_limit_reset = None
        self.fallback_mode = not bool(RAPIDAPI_KEY)
    
    def health_check(self) -> bool:
        """Check if API is available"""
        if self.fallback_mode:
            return True  # Fallback always available
        
        try:
            # Simple connectivity check
            return bool(self.api_key)
        except Exception:
            return False
    
    async def get_city_data(self, city: str) -> Dict[str, Any]:
        """
        Get cost of living data for a city
        With caching and fallback
        """
        # Check cache first
        if city in self.cache:
            data = self.cache[city]
            data['cached'] = True
            return data
        
        # Check rate limiting
        if self._is_rate_limited():
            return self._get_fallback_data(city)
        
        # Try to fetch from API
        try:
            if self.fallback_mode:
                data = self._get_fallback_data(city)
            else:
                data = await self._fetch_from_api(city)
            
            # Cache the result
            self.cache[city] = data
            return data
            
        except Exception as e:
            print(f"API error for {city}: {e}")
            return self._get_fallback_data(city)
    
    async def _fetch_from_api(self, city: str) -> Dict[str, Any]:
        """Fetch data from RapidAPI"""
        
        # Parse city name
        city_name = city.split(',')[0].strip()
        
        url = f"https://{RAPIDAPI_HOST}/v1/city"
        
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": RAPIDAPI_HOST
        }
        
        params = {
            "name": city_name
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=headers,
                params=params,
                timeout=10.0
            )
            
            if response.status_code == 429:
                # Rate limited
                self.rate_limit_reset = datetime.now() + timedelta(hours=1)
                raise Exception("Rate limit exceeded")
            
            response.raise_for_status()
            data = response.json()
            
            # Parse response
            return self._parse_api_response(data, city)
    
    def _parse_api_response(self, data: Dict, city: str) -> Dict[str, Any]:
        """Parse API response to standard format"""
        return {
            "city": city,
            "cost_index": data.get("cost_of_living_index", 0),
            "rent_index": data.get("rent_index", 0),
            "groceries_index": data.get("groceries_index", 0),
            "restaurant_index": data.get("restaurant_price_index", 0),
            "purchasing_power": data.get("local_purchasing_power_index", 0),
            "cached": False,
            "source": "api"
        }
    
    def _get_fallback_data(self, city: str) -> Dict[str, Any]:
        """Get fallback data when API is unavailable"""
        
        # Check if we have fallback data for this city
        if city in FALLBACK_DATA:
            data = FALLBACK_DATA[city].copy()
            data['city'] = city
            data['cached'] = True
            data['source'] = 'fallback'
            return data
        
        # Return estimated average data
        return {
            "city": city,
            "cost_index": 75,  # Average US city
            "rent_index": 65,
            "groceries_index": 80,
            "restaurant_index": 78,
            "cached": True,
            "source": "estimated",
            "note": "Estimated data - actual data unavailable"
        }
    
    def _is_rate_limited(self) -> bool:
        """Check if we're currently rate limited"""
        if not self.rate_limit_reset:
            return False
        
        return datetime.now() < self.rate_limit_reset
    
    def get_supported_cities(self) -> list[Dict[str, str]]:
        """Get list of supported US cities"""
        # Sort alphabetically
        sorted_cities = sorted(US_CITIES)
        
        return [
            {
                "name": city,
                "state": city.split(',')[-1].strip() if ',' in city else ""
            }
            for city in sorted_cities
        ]
    
    def search_cities(self, query: str) -> list[str]:
        """Search cities by name"""
        query = query.lower()
        return [
            city for city in US_CITIES
            if query in city.lower()
        ]
    
    async def compare_cities(self, city1: str, city2: str) -> Dict[str, Any]:
        """Compare cost of living between two cities"""
        data1 = await self.get_city_data(city1)
        data2 = await self.get_city_data(city2)
        
        return {
            "city1": {
                "name": city1,
                "data": data1
            },
            "city2": {
                "name": city2,
                "data": data2
            },
            "comparison": {
                "cost_difference": data2['cost_index'] - data1['cost_index'],
                "rent_difference": data2['rent_index'] - data1['rent_index'],
                "cheaper_city": city1 if data1['cost_index'] < data2['cost_index'] else city2
            }
        }
    
    def get_budget_recommendation(self, city: str, current_budget: float) -> Dict[str, Any]:
        """Get budget recommendation based on city cost of living"""
        # This is synchronous since it's using cached/fallback data
        col_data = self.cache.get(city) or self._get_fallback_data(city)
        
        cost_index = col_data.get('cost_index', 75)
        
        # Adjust budget based on cost index
        # Base index is 100 (NYC)
        adjustment_factor = cost_index / 75  # 75 is average US city
        
        recommended_budget = current_budget * adjustment_factor
        
        categories = {
            "Food": recommended_budget * 0.30,
            "Housing": recommended_budget * 0.35,
            "Transportation": recommended_budget * 0.15,
            "Entertainment": recommended_budget * 0.10,
            "Other": recommended_budget * 0.10
        }
        
        return {
            "city": city,
            "current_budget": current_budget,
            "recommended_budget": round(recommended_budget, 2),
            "adjustment_factor": round(adjustment_factor, 2),
            "suggested_categories": {
                k: round(v, 2) for k, v in categories.items()
            },
            "note": f"Based on {city} cost index: {cost_index}"
        }


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def test():
        api = CostOfLivingAPI()
        
        print("Supported cities:", len(api.get_supported_cities()))
        
        # Test getting city data
        seattle_data = await api.get_city_data("Seattle, WA")
        print("Seattle data:", json.dumps(seattle_data, indent=2))
        
        # Test search
        search_results = api.search_cities("san")
        print("Cities matching 'san':", search_results)
        
        # Test budget recommendation
        recommendation = api.get_budget_recommendation("Seattle, WA", 2000)
        print("Budget recommendation:", json.dumps(recommendation, indent=2))
    
    asyncio.run(test())
