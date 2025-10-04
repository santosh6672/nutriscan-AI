# nutrition.py
"""
nutrition.py - Service module for preparing prompts and calling an LLM to analyze nutrition.

Key features:
- Portable PDF path handling using Django settings (settings.BASE_DIR)
- Robust HF client response parsing
- Deterministic return type: ALWAYS return a Python dict; if an error occurs, return {"error": "..."}
- Simple caching for parsed PDFs
- Token / length truncation helpers (approximate)
"""

import json
import logging
import os
import hashlib
import time
from typing import Any, Dict, Optional

import fitz  # PyMuPDF
from huggingface_hub import InferenceClient
from django.conf import settings

logger = logging.getLogger(__name__)

# Create HF client once (safe to reuse)
HF_TOKEN = os.environ.get("HF_TOKEN") or getattr(settings, "HF_TOKEN", None)
if not HF_TOKEN:
    logger.warning("HF_TOKEN not found in environment or settings; calls will likely fail if required.")

# Use the same provider as original code (but handle response formats robustly)
_client = InferenceClient(provider="novita", api_key=HF_TOKEN)

# Simple in-memory cache for PDF text (keyed by md5(file_bytes))
_pdf_cache: Dict[str, str] = {}

# Simple utility: approximate token estimation by whitespace-separated words
def estimate_token_count(text: str) -> int:
    return len(text.split())


def truncate_text_by_wordcount(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


def extract_pdf_text(pdf_path: str) -> str:
    """
    Read PDF and return combined text. Caches by file hash to avoid repeat parsing.
    """
    try:
        with open(pdf_path, "rb") as f:
            file_bytes = f.read()
    except Exception as exc:
        logger.exception("Failed to open PDF path: %s", pdf_path)
        raise

    file_hash = hashlib.md5(file_bytes).hexdigest()
    cached = _pdf_cache.get(file_hash)
    if cached:
        return cached

    try:
        doc_text_parts = []
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            for page in doc:
                doc_text_parts.append(page.get_text())
        full_text = "\n".join(doc_text_parts)
        _pdf_cache[file_hash] = full_text
        return full_text
    except Exception as exc:
        logger.exception("Failed to parse PDF: %s", pdf_path)
        raise


def format_nutrient_data(product_info: Dict[str, Any]) -> str:
    """
    Formats the 'nutriments' dictionary into a clean, readable string for prompt inclusion.
    Accepts OpenFoodFacts-like structure or a fallback 'nutriments' key.
    """
    nutrients = product_info.get("nutriments") or product_info.get("nutrients") or {}
    if not isinstance(nutrients, dict):
        return ""
    lines = []
    for k, v in nutrients.items():
        # Make key human-friendly
        key_str = str(k).replace("_", " ").replace("-", " ").title()
        lines.append(f"- {key_str}: {v}")
    return "\n".join(lines)


def _build_prompt(age: Optional[int], weight: Optional[float], height: Optional[float], bmi: Optional[float],
                  health_conditions: Optional[str], dietary_preferences: Optional[str], goal: Optional[str],
                  product_info: Dict[str, Any], diet_knowledge: str) -> (str, str):
    """
    Compose system_message and user_prompt to send to the model.
    System message includes instructions and an example. The user prompt includes the live data.
    """

    # System message (instructions + persona + example)
    system_message = """
You are an expert AI Nutritionist. Your task is to analyze a food product based on a user's profile and
provided dietary principles. Produce exactly one JSON object and nothing else. The JSON object keys must be:
- "advisability": string, one of "Yes", "No", "With Caution"
- "pros": list of short factual strings
- "cons": list of short factual strings
- "summary": short string with up to three concise points explaining the reasoning

Do not include any commentary or additional text outside the JSON object.
"""

    # Example (few-shot)
    example_obj = {
        "advisability": "With Caution",
        "pros": [
            "Good source of fiber, which aids satiety.",
            "Provides a quick energy boost."
        ],
        "cons": [
            "Very high in sugar (25g per 100g).",
            "High in calories and fat, making it dense for a weight loss diet."
        ],
        "summary": "This bar provides satiety via fiber but is high in sugar and calories, so limit consumption."
    }

    example_text = "\n---EXAMPLE---\n" + json.dumps(example_obj, indent=2) + "\n---END EXAMPLE---\n"

    # User profile block
    user_profile = {
        "Age": age if age is not None else "Not provided",
        "Weight": f"{weight} kg" if weight is not None else "Not provided",
        "Height": f"{height} cm" if height is not None else "Not provided",
        "BMI": bmi if bmi is not None else "Not provided",
        "Health Conditions": health_conditions or "None",
        "Dietary Preferences": dietary_preferences or "None",
        "Goal": goal or "General health"
    }
    user_profile_text = "\n".join([f"- {k}: {v}" for k, v in user_profile.items()])

    product_name = product_info.get("product_name") or product_info.get("Product") or product_info.get("name") or "Unknown Product"
    nutrients_text = format_nutrient_data(product_info)

    # Truncate diet knowledge to keep prompt small (approx by words)
    truncated_knowledge = truncate_text_by_wordcount(diet_knowledge or "", 2500)

    user_prompt = f"""
<user_profile>
{user_profile_text}
</user_profile>

<product_info>
- Name: {product_name}
- Nutrients (per 100g if applicable):
{nutrients_text}
</product_info>

<dietary_principles>
{truncated_knowledge}
</dietary_principles>

Based on all the information provided, produce the single JSON object described above.
"""

    # Combine for clarity: system message also includes example to bias the response
    full_system = system_message + "\n" + example_text
    return full_system.strip(), user_prompt.strip()


def _call_model(system_message: str, user_prompt: str, max_retries: int = 2, timeout_s: int = 30) -> Dict[str, Any]:
    """
    Calls the HF InferenceClient chat_completion (or equivalent) and attempts to parse output into dict.
    Retries a small number of times on transient errors.
    """
    for attempt in range(max_retries + 1):
        try:
            # Keep model and parameters here; tune as needed
            response = _client.chat_completion(
                model="meta-llama/Meta-Llama-3-8B-Instruct",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=400,
                temperature=0.2
            )

            # response can be a rich object; try several common access patterns
            # 1) OpenAI-like: response.choices[0].message.content
            content = None
            if hasattr(response, "choices"):
                try:
                    content = response.choices[0].message.content
                except Exception:
                    # fallback to OpenAI-like but different path
                    try:
                        content = response.choices[0].text
                    except Exception:
                        content = None

            # 2) HF InferenceLibrary: response.generated_text or str(response)
            if content is None:
                content = getattr(response, "generated_text", None)

            if content is None:
                # Final fallback to stringifying
                content = str(response)

            # Ensure it's a string
            content_str = content.strip() if isinstance(content, str) else json.dumps(content)

            # Try to parse JSON robustly
            try:
                parsed = json.loads(content_str)
                if isinstance(parsed, dict):
                    return parsed
                # If model returned list or other structure, wrap it
                return {"parsed": parsed}
            except json.JSONDecodeError:
                # fallback to regex extraction
                import re
                match = re.search(r'\{.*\}', content_str, re.DOTALL)
                if match:
                    try:
                        parsed = json.loads(match.group())
                        return parsed if isinstance(parsed, dict) else {"parsed": parsed}
                    except json.JSONDecodeError:
                        # try replacing single quotes
                        try:
                            cleaned = match.group().replace("'", '"')
                            parsed = json.loads(cleaned)
                            return parsed if isinstance(parsed, dict) else {"parsed": parsed}
                        except Exception:
                            pass

            # If parsing failed, return raw content under 'raw' key
            return {"raw": content_str}

        except Exception as exc:
            logger.exception("Error calling LLM (attempt %s/%s)", attempt + 1, max_retries + 1)
            # small backoff
            time.sleep(1 + attempt * 2)
            last_exc = exc
            continue

    # After retries failed
    return {"error": f"LLM call failed: {str(last_exc)}"}


def analyze_nutrition(age: Optional[int],
                      weight: Optional[float],
                      height: Optional[float],
                      bmi: Optional[float],
                      health_conditions: Optional[str],
                      dietary_preferences: Optional[str],
                      goal: Optional[str],
                      product_info: Dict[str, Any],
                      pdf_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Main entrypoint for nutrition analysis. Returns a dict:
    - On success: keys advisability, pros, cons, summary (as defined)
    - On failure: {"error": "..."}
    """
    try:
        if not isinstance(product_info, dict):
            return {"error": "Invalid product_info (expected dict)."}

        if 'nutriments' not in product_info and 'nutrients' not in product_info:
            # Not strictly an error; but warn and continue
            logger.debug("product_info lacks 'nutriments' key; continuing with whatever is present.")

        # Resolve PDF path (default to a healthy-diet fact sheet inside static if not provided)
        if not pdf_path:
            default_rel = os.path.join("nutriscan_ai", "static", "healthy-diet-fact-sheet-394.pdf")
            pdf_path = os.path.join(getattr(settings, "BASE_DIR", "."), default_rel)

        if not os.path.exists(pdf_path):
            logger.warning("PDF not found at %s; proceeding without additional diet knowledge.", pdf_path)
            diet_knowledge = ""
        else:
            try:
                diet_knowledge = extract_pdf_text(pdf_path)
            except Exception as exc:
                logger.exception("Failed to extract PDF text; using empty knowledge base.")
                diet_knowledge = ""

        system_message, user_prompt = _build_prompt(
            age=age,
            weight=weight,
            height=height,
            bmi=bmi,
            health_conditions=health_conditions,
            dietary_preferences=dietary_preferences,
            goal=goal,
            product_info=product_info,
            diet_knowledge=diet_knowledge
        )

        llm_result = _call_model(system_message, user_prompt)

        # If llm_result contains "error" already, return it
        if 'error' in llm_result:
            return {"error": llm_result.get('error')}

        # Normalization: ensure keys exist and defaults
        advisability = llm_result.get('advisability') or llm_result.get('recommendation') or "Unknown"
        pros = llm_result.get('pros') or llm_result.get('benefits') or []
        cons = llm_result.get('cons') or llm_result.get('drawbacks') or []
        summary = llm_result.get('summary') or llm_result.get('explanation') or ""

        # If LLM returned raw text only, include it to help debugging
        if 'raw' in llm_result and not any([advisability != "Unknown", pros, cons, summary]):
            # Try one more attempt to parse the raw contents
            raw_text = llm_result.get('raw', '')
            try:
                parsed = json.loads(raw_text)
                advisability = parsed.get('advisability', advisability)
                pros = parsed.get('pros', pros)
                cons = parsed.get('cons', cons)
                summary = parsed.get('summary', summary)
            except Exception:
                logger.debug("Unable to parse 'raw' fallback content.")

        return {
            "advisability": advisability,
            "pros": pros if isinstance(pros, list) else [str(pros)],
            "cons": cons if isinstance(cons, list) else [str(cons)],
            "summary": summary
        }

    except Exception as exc:
        logger.exception("Unexpected error in analyze_nutrition")
        return {"error": str(exc)}
