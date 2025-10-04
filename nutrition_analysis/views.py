# views.py

# Standard Library Imports
import json
import logging
import re
from typing import Any, Dict, Optional
from pprint import pprint

# Third-Party Imports
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render

# Local Application Imports
from accounts.models import User
from .forms import ScanForm
from .services import barcode_scanner, nutrition, product_lookup

# -----------------------------------------------------------------------------
# Constants & Logger
# -----------------------------------------------------------------------------

# Use constants for session keys to avoid typos and improve maintainability.
SESSION_SCAN_KEY = 'latest_scan'
SESSION_RESULT_KEY = 'latest_scan_results'

# Define the nutrient map as a constant for easy configuration.
DEFAULT_NUTRIENT_MAP = (
    "energy-kcal:Energy (kcal)|fat:Total Fat|saturated-fat:Saturated Fat|"
    "carbohydrates:Carbohydrate|fiber:Fiber|sugars:Sugar|proteins:Protein|"
    "salt:Salt|sodium:Sodium"
)

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Public Views
# -----------------------------------------------------------------------------

@login_required(login_url='login')
def scan_product(request: HttpRequest) -> HttpResponse:
    """
    Main endpoint for product scanning and analysis.
    - GET: Renders the scan form.
    - POST (AJAX): Handles barcode image scanning.
    - POST (Standard): Triggers product analysis.
    """
    if request.method == 'POST':
        # AJAX request for barcode scanning only
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return _handle_barcode_scan(request)
        # Standard form submission for full analysis
        return _handle_product_analysis(request)

    # GET request: render the initial upload form
    form = ScanForm()
    return render(request, 'analysis/scan.html', {'form': form})


@login_required(login_url='login')
def result(request: HttpRequest) -> HttpResponse:
    """
    Displays the final analysis results from the most recent scan.
    """
    # Retrieve and remove scan results from the session to prevent re-display.
    scan_results = request.session.pop(SESSION_RESULT_KEY, None)
    if not scan_results:
        messages.info(request, "No recent scan results found. Please scan a product first.")
        return redirect('scan_product')

    # Parse the nutrient map string into a dictionary for template usage.
    nutrient_map_str = scan_results.get('nutrient_map', '')
    nutrient_map_dict = {
        item.split(':', 1)[0]: item.split(':', 1)[1]
        for item in nutrient_map_str.split('|') if ':' in item
    }
    
    context = {
        'product': scan_results.get('product'),
        'analysis': scan_results.get('analysis'),
        'nutrient_map': nutrient_map_dict,
        'scan_image': scan_results.get('scan_image'),
        'user': request.user,
    }
    return render(request, 'analysis/result.html', context)


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

def _handle_barcode_scan(request: HttpRequest) -> JsonResponse:
    """Process an AJAX barcode scanning request and return scan metadata."""
    form = ScanForm(request.POST, request.FILES)
    if not form.is_valid():
        logger.debug("Scan form invalid: %s", form.errors)
        return JsonResponse({'success': False, 'message': 'Invalid form data.'}, status=400)

    try:
        uploaded_image = form.cleaned_data['image']
        scan_result = barcode_scanner.scan_barcode_with_display(uploaded_image)
        logger.debug("Barcode scanner result: %s", scan_result)

        # Store scan data in session only if a barcode was successfully found.
        barcode_data = scan_result.get('barcode_data') or scan_result.get('code')
        if barcode_data:
            request.session[SESSION_SCAN_KEY] = {
                'barcode_data': barcode_data,
                'scan_result': scan_result
            }
            request.session.modified = True

        return JsonResponse(scan_result)

    except Exception as exc:
        logger.exception("An unexpected error occurred in _handle_barcode_scan")
        return JsonResponse({'success': False, 'message': str(exc)}, status=500)


def _get_user_profile_for_analysis(user: User) -> Optional[Dict[str, Any]]:
    """
    Validate and retrieve necessary user profile data for nutrition analysis.
    Returns a dictionary of data or None if the profile is incomplete.
    """
    required_fields = ['age', 'weight_kg', 'height_cm']
    if any(not getattr(user, field) for field in required_fields):
        return None

    return {
        "age": user.age,
        "weight": user.weight_kg,
        "height": user.height_cm,
        "bmi": getattr(user, 'bmi', None),
        "health_conditions": getattr(user, 'health_issues', None) or getattr(user, 'health_conditions', None),
        "dietary_preferences": getattr(user, 'dietary_preferences', None),
        "goal": getattr(user, 'goals', None) or getattr(user, 'goal', None),
    }


def _handle_product_analysis(request: HttpRequest) -> HttpResponse:
    """
    Orchestrate the product lookup and nutrition analysis, then redirect to the result page.
    """
    # Get barcode from manual input or the last scan stored in the session.
    latest_scan = request.session.get(SESSION_SCAN_KEY, {})
    barcode_data = request.POST.get('manual_barcode_data') or latest_scan.get('barcode_data')

    if not barcode_data:
        messages.error(request, "No barcode provided. Please scan a product or enter one manually.")
        return redirect('scan_product')

    try:
        # Step 1: Fetch product data using the barcode.
        product = product_lookup.fetch_product_data(barcode_data)
        if not product:
            messages.error(request, f"Could not find product data for barcode: {barcode_data}")
            return redirect('scan_product')

        # Step 2: Validate and get user profile data.
        user_profile_data = _get_user_profile_for_analysis(request.user)
        if user_profile_data is None:
            messages.error(request, "Please complete your profile (age, height, weight) for a personalized analysis.")
            return redirect('profile')

        # Step 3: Run the core nutrition analysis.
        analysis_result = nutrition.analyze_nutrition(
            **user_profile_data,
            product_info=product
        )

        # The service returns a dict. If it's not a dict or contains an error, handle it.
        if not isinstance(analysis_result, dict) or 'error' in analysis_result:
            error_msg = analysis_result.get('error', "Invalid analysis result format.")
            messages.error(request, f"Analysis Error: {error_msg}")
            return redirect('scan_product')

        # Step 4: Persist final results to session for the result view.
        request.session[SESSION_RESULT_KEY] = {
            "product": product,
            "analysis": analysis_result,
            "nutrient_map": DEFAULT_NUTRIENT_MAP,
            "scan_image": latest_scan.get('scan_result', {}).get('image_with_boxes')
        }

        # Clean up temporary scan data and save the session.
        if SESSION_SCAN_KEY in request.session:
            del request.session[SESSION_SCAN_KEY]
        request.session.modified = True

        return redirect('result')

    except Exception as exc:
        logger.exception("An unexpected error occurred in _handle_product_analysis")
        messages.error(request, f"An unexpected error occurred: {str(exc)}")
        return redirect('scan_product')


def _safe_parse_llm_json(response_text: str) -> Dict[str, Any]:
    """
    Robustly parse a JSON object from a string, which might be wrapped in
    other text (a common issue with LLM responses).
    """
    if not isinstance(response_text, str):
        return {}
    # First, try a direct parse.
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        # If direct parse fails, find the first JSON-like structure ({...}).
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON fragment from LLM response.")
    return {}