import requests
from typing import Optional, Dict

OPEN_FOOD_FACTS_API = "https://world.openfoodfacts.org/api/v0/product/{}.json"

def fetch_product_data(barcode: str) -> Optional[Dict]:
    try:
        response = requests.get(OPEN_FOOD_FACTS_API.format(barcode), timeout=10)
        response.raise_for_status()  # Raises exception for 4XX/5XX responses
        
        product = response.json()
        
        if product.get("status") == 0 or not product.get("product"):
            return None
            
        # Ensure we always return a dictionary with expected structure
        return {
            "product_name": product.get("product", {}).get("product_name", "Unknown Product"),
            "nutriscore_grade": product.get("product", {}).get("nutriscore_grade", "N/A").upper(),
            "nutriscore_score": product.get("product", {}).get("nutriscore_score", 0),
            "nutriments": product.get("product", {}).get("nutriments", {}),
            "nutrient_levels": product.get("product", {}).get("nutrient_levels", {}),
            "image_url": product.get("product", {}).get("image_url", ""),
            "brands": product.get("product", {}).get("brands", "Unknown Brand"),
            "categories": product.get("product", {}).get("categories", ""),
        }
        
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"Error fetching product data: {e}")
        return None