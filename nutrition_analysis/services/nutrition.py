import json
import logging
import os
import hashlib
import time
import re
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass

import fitz  # PyMuPDF
from huggingface_hub import InferenceClient
from django.conf import settings

logger = logging.getLogger(__name__)

# Configuration
CONFIG = {
    "model": "meta-llama/Meta-Llama-3-8B-Instruct",
    "max_tokens": 400,
    "temperature": 0.2,
    "timeout": 30,
    "max_retries": 2,
    "max_pdf_words": 2500,
    "cache_ttl": 3600,  # 1 hour cache TTL
}

@dataclass
class CacheEntry:
    text: str
    timestamp: float

# Enhanced cache with TTL
_pdf_cache: Dict[str, CacheEntry] = {}

# Initialize client once
HF_TOKEN = os.environ.get("HF_TOKEN") or getattr(settings, "HF_TOKEN", None)

_client = None
if HF_TOKEN:
    try:
        _client = InferenceClient(provider="novita", api_key=HF_TOKEN)
    except Exception as e:
        logger.error(f"Failed to initialize HF client: {e}")

def _clean_cache():
    """Remove expired cache entries"""
    current_time = time.time()
    expired_keys = [
        key for key, entry in _pdf_cache.items()
        if current_time - entry.timestamp > CONFIG["cache_ttl"]
    ]
    for key in expired_keys:
        del _pdf_cache[key]

def estimate_token_count(text: str) -> int:
    """More accurate token estimation (rough approximation)"""
    return len(text.split()) + len(text) // 4

def truncate_text_by_wordcount(text: str, max_words: int) -> str:
    """Truncate text preserving sentence boundaries when possible"""
    if not text:
        return ""
    
    words = text.split()
    if len(words) <= max_words:
        return text
    
    # Try to truncate at sentence boundary
    truncated = " ".join(words[:max_words])
    last_period = truncated.rfind('.')
    if last_period > len(truncated) * 0.7:  # Only if we have a reasonable sentence
        return truncated[:last_period + 1]
    
    return truncated

def extract_pdf_text(pdf_path: str) -> str:
    """
    Extract text from PDF with streaming and better error handling
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    try:
        with open(pdf_path, "rb") as f:
            file_bytes = f.read()
    except Exception as e:
        logger.error(f"Failed to read PDF file {pdf_path}: {e}")
        raise
    
    file_hash = hashlib.md5(file_bytes).hexdigest()
    
    # Clean cache before checking
    _clean_cache()
    
    cached = _pdf_cache.get(file_hash)
    if cached:
        return cached.text
    
    try:
        doc_text_parts = []
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            for page in doc:
                text = page.get_text().strip()
                if text:
                    doc_text_parts.append(text)
        
        full_text = "\n".join(doc_text_parts)
        
        # Cache with timestamp
        _pdf_cache[file_hash] = CacheEntry(text=full_text, timestamp=time.time())
        return full_text
        
    except Exception as e:
        logger.error(f"Failed to parse PDF {pdf_path}: {e}")
        raise

def format_nutrient_data(product_info: Dict[str, Any]) -> str:
    """Format nutrient data with filtering for relevant nutrients"""
    nutrients = product_info.get("nutriments") or product_info.get("nutrients") or {}
    if not isinstance(nutrients, dict):
        return ""
    
    # Common relevant nutrients to include
    relevant_nutrients = {
        'energy', 'energy-kcal', 'energy-kj', 'fat', 'saturated-fat', 
        'carbohydrates', 'sugars', 'fiber', 'proteins', 'salt', 'sodium',
        'cholesterol', 'calcium', 'iron', 'vitamin_a', 'vitamin_c', 'vitamin_d'
    }
    
    lines = []
    for k, v in nutrients.items():
        key_lower = k.lower()
        # Include if relevant or if we don't have many nutrients yet
        if any(relevant in key_lower for relevant in relevant_nutrients) or len(lines) < 10:
            key_str = str(k).replace('_', ' ').replace('-', ' ').title()
            # Add units if available in the key
            if any(unit in key_lower for unit in ['_100g', '_serving']):
                key_str = key_str.replace('100g', '(per 100g)')
            lines.append(f"- {key_str}: {v}")
    
    return "\n".join(lines[:15])  # Limit to 15 most relevant nutrients

def _build_prompt(
    age: Optional[int], 
    weight: Optional[float], 
    height: Optional[float], 
    bmi: Optional[float],
    health_conditions: Optional[str], 
    dietary_preferences: Optional[str], 
    goal: Optional[str],
    product_info: Dict[str, Any], 
    diet_knowledge: str
) -> Tuple[str, str]:
    """
    Build optimized prompts with better structure and examples
    """
    system_message = """You are an expert AI Nutritionist and Product Analyst. Analyze the given food product based on its ingredients and nutrition facts.

Respond with exactly one JSON object with these keys:
- "description": string, a detailed and factual description of the product (about 80–150 words). Describe what it is, its main ingredients, how it is typically used or consumed, and any notable characteristics.
- "advisability": string, one of "Yes", "No", or "With Caution"
- "pros": list of short factual strings (2–4 items)
- "cons": list of short factual strings (2–4 items)
- "summary": string with 1–3 concise points summarizing your dietary recommendation.

Example response:
{
  "description": "Nestlé KitKat is a chocolate-coated wafer snack composed of multiple crisp wafer layers covered in milk chocolate. It is sweet and crunchy, commonly consumed as a dessert or energy snack. It provides carbohydrates for quick energy but contains significant amounts of sugar and saturated fat. KitKat is widely available in individual and multipack servings and is not suitable for diabetics or those on low-sugar diets.",
  "advisability": "With Caution",
  "pros": ["Provides quick energy", "Tastes good and convenient to consume"],
  "cons": ["High in sugar", "Contains saturated fat", "Low in protein"],
  "summary": "A tasty but sugary snack that should be eaten occasionally, not regularly."
}"""


    # Build user profile efficiently
    user_profile_parts = []
    if age: user_profile_parts.append(f"Age: {age}")
    if weight: user_profile_parts.append(f"Weight: {weight} kg")
    if height: user_profile_parts.append(f"Height: {height} cm")
    if bmi: user_profile_parts.append(f"BMI: {bmi}")
    if health_conditions: user_profile_parts.append(f"Health Conditions: {health_conditions}")
    if dietary_preferences: user_profile_parts.append(f"Dietary Preferences: {dietary_preferences}")
    if goal: user_profile_parts.append(f"Goal: {goal}")
    
    user_profile_text = "\n".join(f"- {part}" for part in user_profile_parts) or "Not provided"

    # Extract product details
    product_name = product_info.get("product_name") or product_info.get("name", "Unknown Product")
    nutrients_text = format_nutrient_data(product_info)
    
    # Include additional product context if available
    additional_info = []
    if product_info.get("nutriscore_grade"):
        additional_info.append(f"Nutri-Score: {product_info['nutriscore_grade']}")
    if product_info.get("brands"):
        additional_info.append(f"Brand: {product_info['brands']}")

    additional_info_text = ""
    if additional_info:
        additional_info_text = "- " + "\n- ".join(additional_info)
    
    truncated_knowledge = truncate_text_by_wordcount(diet_knowledge or "", CONFIG["max_pdf_words"])

    # Build final user prompt
    user_prompt = f"""User Profile:
{user_profile_text}

Product Information:
- Name: {product_name}
{additional_info_text}
- Nutrients:
{nutrients_text if nutrients_text else 'No detailed nutrient data available'}

Dietary Principles:
{truncated_knowledge}

Please analyze this product and provide your assessment in the specified JSON format.
"""

    return system_message.strip(), user_prompt.strip()


def _parse_llm_response(content: str) -> Dict[str, Any]:
    """
    Robust JSON parsing with multiple fallback strategies
    """
    if not content:
        return {"error": "Empty response from model"}
    
    content = content.strip()
    
    # Strategy 1: Direct JSON parsing
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Extract JSON with regex
    json_patterns = [
        r'\{[^{}]*"[^"]*"[^{}]*\}',  # Simple single-line JSON
        r'\{.*\}',  # Multi-line JSON (DOTALL)
    ]
    
    for pattern in json_patterns:
        try:
            matches = re.finditer(pattern, content, re.DOTALL)
            for match in matches:
                try:
                    parsed = json.loads(match.group())
                    if isinstance(parsed, dict) and 'advisability' in parsed:
                        return parsed
                except json.JSONDecodeError:
                    # Try with single quotes replaced
                    try:
                        cleaned = match.group().replace("'", '"')
                        parsed = json.loads(cleaned)
                        if isinstance(parsed, dict) and 'advisability' in parsed:
                            return parsed
                    except json.JSONDecodeError:
                        continue
        except Exception:
            continue
    
    # Strategy 3: Try to parse as JSON lines or multiple objects
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('{') and line.endswith('}'):
            try:
                parsed = json.loads(line)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue
    
    # Final fallback: Return structured error with raw content
    return {
        "error": "Could not parse valid JSON from response",
        "raw": content[:500]  # First 500 chars for debugging
    }

def _call_model(system_message: str, user_prompt: str) -> Dict[str, Any]:
    """
    Call LLM with exponential backoff and comprehensive error handling
    """
    if not _client:
        return {"error": "HF client not initialized - check HF_TOKEN configuration"}
    
    last_exc = None
    for attempt in range(CONFIG["max_retries"] + 1):
        try:
            response = _client.chat_completion(
                model=CONFIG["model"],
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=CONFIG["max_tokens"],
                temperature=CONFIG["temperature"]
            )
            
            # Extract content from various response formats
            content = None
            if hasattr(response, 'choices') and response.choices:
                choice = response.choices[0]
                if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                    content = choice.message.content
                elif hasattr(choice, 'text'):
                    content = choice.text
            
            if content is None:
                content = getattr(response, 'generated_text', str(response))
            
            return _parse_llm_response(content)
            
        except Exception as exc:
            return {"error": f"LLM call failed: {str(exc)}"}
    
    return {"error": f"All retries failed: {str(last_exc)}"}

def _validate_product_info(product_info: Dict[str, Any]) -> bool:
    """Validate that product_info has minimal required data"""
    if not isinstance(product_info, dict):
        return False
    
    # Check for at least some product identification or nutrient data
    has_name = any(key in product_info for key in ['product_name', 'name', 'product'])
    has_nutrients = any(key in product_info for key in ['nutriments', 'nutrients', 'nutrition'])
    
    return has_name or has_nutrients

def analyze_nutrition(
    age: Optional[int],
    weight: Optional[float], 
    height: Optional[float],
    bmi: Optional[float],
    health_conditions: Optional[str],
    dietary_preferences: Optional[str],
    goal: Optional[str],
    product_info: Dict[str, Any],
) -> Dict[str, Any]:
    start_time = time.time()
    
    # Input validation
    if not _validate_product_info(product_info):
        return {"error": "Invalid product_info: must be a dict with product name or nutrient data"}
    
    try:
        # Handle PDF knowledge base
        diet_knowledge = ""
        pdf_path='static\\healthy-diet-fact-sheet-394.pdf'
        if pdf_path and os.path.exists(pdf_path):
            try:
                diet_knowledge = extract_pdf_text(pdf_path)
            except Exception as e:
                return {"error":f"Failed to load PDF {pdf_path}: {e}. Continuing without additional knowledge."}
        
        # Build and call model
        system_message, user_prompt = _build_prompt(
            age=age, weight=weight, height=height, bmi=bmi,
            health_conditions=health_conditions, dietary_preferences=dietary_preferences,
            goal=goal, product_info=product_info, diet_knowledge=diet_knowledge
        )
        
        llm_result = _call_model(system_message, user_prompt)
        
        # Handle errors from LLM call
        if "error" in llm_result:
            return {"error": f"LLM processing failed: {llm_result['error']}"}
        
        # Normalize response structure
        advisability = llm_result.get('advisability', 'Unknown')
        if advisability not in ['Yes', 'No', 'With Caution']:
            advisability = 'With Caution'  # Default to cautious
        
        pros = llm_result.get('pros', [])
        if not isinstance(pros, list):
            pros = [str(pros)] if pros else []
        
        cons = llm_result.get('cons', [])
        if not isinstance(cons, list):
            cons = [str(cons)] if cons else []
        
        summary = llm_result.get('summary', 'No summary provided')
        description = llm_result.get('description', 'No description provided')
        
        result = {
            "advisability": advisability,
            "pros": pros,
            "cons": cons, 
            "summary": summary,
            "description": description,
        }

        return result
        
    except Exception as e:
        return {"error": f"Analysis failed: {str(e)}"}