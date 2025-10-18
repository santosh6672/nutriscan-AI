# Standard Library Imports
import json
import logging
import re
from typing import Any, Dict, Optional, Union
from pprint import pprint

# Third-Party Imports
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

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
SESSION_BARCODE_KEY = 'current_barcode'

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
@require_http_methods(["GET", "POST"])
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
    
    # Pre-populate manual barcode if available from session
    current_barcode = request.session.get(SESSION_BARCODE_KEY)
    context = {
        'form': form,
        'current_barcode': current_barcode
    }
    
    return render(request, 'analysis/scan.html', context)


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
    nutrient_map_str = scan_results.get('nutrient_map', DEFAULT_NUTRIENT_MAP)
    nutrient_map_dict = {}
    try:
        for item in nutrient_map_str.split('|'):
            if ':' in item:
                key, value = item.split(':', 1)
                nutrient_map_dict[key.strip()] = value.strip()
    except Exception as e:
        logger.warning(f"Error parsing nutrient map: {e}")
        # Fallback to default mapping
        nutrient_map_dict = {
            'energy-kcal': 'Energy (kcal)', 'fat': 'Total Fat', 
            'saturated-fat': 'Saturated Fat', 'carbohydrates': 'Carbohydrate',
            'fiber': 'Fiber', 'sugars': 'Sugar', 'proteins': 'Protein',
            'salt': 'Salt', 'sodium': 'Sodium'
        }
    
    # Prepare product data for template
    product_data = scan_results.get('product', {})
    analysis_data = scan_results.get('analysis', {})
    
    # Ensure analysis has expected structure
    if not analysis_data.get('advisability'):
        analysis_data['advisability'] = 'Unknown'
    
    context = {
        'product': product_data,
        'analysis': analysis_data,
        'nutrient_map': nutrient_map_dict,
        'scan_image': scan_results.get('scan_image'),
        'user': request.user,
        'barcode': scan_results.get('barcode', 'Unknown'),
    }
    return render(request, 'analysis/result.html', context)


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

def _handle_barcode_scan(request: HttpRequest) -> JsonResponse:
    """Process an AJAX barcode scanning request and return scan metadata."""
    form = ScanForm(request.POST, request.FILES)
    if not form.is_valid():
        logger.warning(f"Scan form invalid: {form.errors}")
        return JsonResponse({
            'success': False, 
            'message': 'Invalid form data. Please check the uploaded image.'
        }, status=400)

    try:
        uploaded_image = form.cleaned_data['image']
        scan_result = barcode_scanner.scan_barcode_with_display(uploaded_image)
        logger.info(f"Barcode scanner result: {scan_result.get('success')} - {scan_result.get('message')}")

        # Store scan data in session only if a barcode was successfully found.
        barcode_data = scan_result.get('barcode_data')
        if barcode_data:
            # Store minimal data in session to avoid session size issues
            request.session[SESSION_SCAN_KEY] = {
                'barcode_data': barcode_data,
                'scan_image': scan_result.get('image_with_boxes'),
                'detection_count': scan_result.get('detection_count', 0)
            }
            # Also store current barcode for form pre-population
            request.session[SESSION_BARCODE_KEY] = barcode_data
            request.session.modified = True
            
            logger.info(f"Barcode {barcode_data} stored in session")

        return JsonResponse(scan_result)

    except Exception as exc:
        logger.exception("An unexpected error occurred in _handle_barcode_scan")
        return JsonResponse({
            'success': False, 
            'message': 'Server error during barcode scanning. Please try again.'
        }, status=500)


def _get_user_profile_for_analysis(user: User) -> Optional[Dict[str, Any]]:
    """
    Validate and retrieve necessary user profile data for nutrition analysis.
    Returns a dictionary of data or None if the profile is incomplete.
    """
    try:
        # Check for required fields with proper validation
        if not user.age or user.age <= 0 or user.age > 120:
            logger.warning(f"Invalid user age: {getattr(user, 'age', 'None')}")
            return None
            
        if not user.weight_kg or user.weight_kg <= 0 or user.weight_kg > 300:
            logger.warning(f"Invalid user weight: {getattr(user, 'weight_kg', 'None')}")
            return None
            
        if not user.height_cm or user.height_cm <= 0 or user.height_cm > 300:
            logger.warning(f"Invalid user height: {getattr(user, 'height_cm', 'None')}")
            return None

        # Calculate BMI if not provided
        bmi = getattr(user, 'bmi', None)
        if not bmi and user.height_cm > 0:
            height_m = user.height_cm / 100
            bmi = user.weight_kg / (height_m * height_m)

        profile_data = {
            "age": user.age,
            "weight": user.weight_kg,
            "height": user.height_cm,
            "bmi": round(bmi, 1) if bmi else None,
            "health_conditions": getattr(user, 'health_issues', '') or getattr(user, 'health_conditions', ''),
            "dietary_preferences": getattr(user, 'dietary_preferences', ''),
            "goal": getattr(user, 'goals', '') or getattr(user, 'goal', ''),
        }
        
        logger.debug(f"User profile data prepared: { {k: v for k, v in profile_data.items() if k not in ['health_conditions', 'dietary_preferences', 'goal']} }")
        return profile_data
        
    except Exception as e:
        logger.error(f"Error preparing user profile: {e}")
        return None


def _validate_product_data(product: Dict[str, Any]) -> bool:
    """
    Validate that product data has minimum required information.
    """
    if not product or not isinstance(product, dict):
        return False
        
    # Check for basic product identification
    product_name = product.get('product_name') or product.get('name')
    if not product_name or product_name == 'Unknown Product':
        return False
        
    # Check for at least some nutritional data
    has_nutriments = bool(product.get('nutriments'))
    has_nutrients = bool(product.get('nutrients'))
    has_nutriscore = bool(product.get('nutriscore_grade'))
    
    return has_nutriments or has_nutrients or has_nutriscore


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

    # Clean barcode data
    barcode_data = str(barcode_data).strip()
    logger.info(f"Starting product analysis for barcode: {barcode_data}")

    try:
        # Step 1: Fetch product data using the barcode.
        product = product_lookup.fetch_product_data(barcode_data)
        if not product:
            messages.error(request, f"Could not find product data for barcode: {barcode_data}")
            logger.warning(f"No product data found for barcode: {barcode_data}")
            return redirect('scan_product')
            
        # Validate product data
        if not _validate_product_data(product):
            messages.warning(request, f"Product found but nutritional data is limited for barcode: {barcode_data}")
            logger.warning(f"Incomplete product data for barcode: {barcode_data}")

        # Step 2: Validate and get user profile data.
        user_profile_data = _get_user_profile_for_analysis(request.user)
        if user_profile_data is None:
            messages.error(request, "Please complete your profile (age, height, weight) for a personalized analysis.")
            return redirect('profile')  # Assuming you have a profile URL

        # Step 3: Run the core nutrition analysis.
        logger.info("Starting nutrition analysis...")
        analysis_result = nutrition.analyze_nutrition(
            **user_profile_data,
            product_info=product
        )

        # The service returns a dict. If it's not a dict or contains an error, handle it.
        if not isinstance(analysis_result, dict):
            error_msg = "Invalid analysis result format."
            logger.error(f"Analysis returned non-dict result: {type(analysis_result)}")
            messages.error(request, f"Analysis Error: {error_msg}")
            return redirect('scan_product')
            
        if 'error' in analysis_result:
            error_msg = analysis_result.get('error', "Unknown analysis error.")
            logger.error(f"Analysis error: {error_msg}")
            messages.error(request, f"Analysis Error: {error_msg}")
            return redirect('scan_product')

        # Validate analysis result structure
        required_keys = ['advisability', 'pros', 'cons', 'summary']
        missing_keys = [key for key in required_keys if key not in analysis_result]
        if missing_keys:
            logger.warning(f"Analysis result missing keys: {missing_keys}")
            # Fill missing keys with defaults rather than failing
            for key in missing_keys:
                if key == 'advisability':
                    analysis_result[key] = 'Unknown'
                elif key in ['pros', 'cons']:
                    analysis_result[key] = []
                else:
                    analysis_result[key] = 'No summary available'

        # Step 4: Persist final results to session for the result view.
        request.session[SESSION_RESULT_KEY] = {
            "product": product,
            "analysis": analysis_result,
            "nutrient_map": DEFAULT_NUTRIENT_MAP,
            "scan_image": latest_scan.get('scan_image'),
            "barcode": barcode_data
        }

        # Clean up temporary scan data and save the session.
        for key in [SESSION_SCAN_KEY, SESSION_BARCODE_KEY]:
            if key in request.session:
                del request.session[key]
                
        request.session.modified = True

        logger.info(f"Product analysis completed successfully for barcode: {barcode_data}")
        return redirect('result')

    except Exception as exc:
        logger.exception(f"An unexpected error occurred in _handle_product_analysis for barcode {barcode_data}")
        messages.error(request, f"An unexpected error occurred during analysis. Please try again.")
        return redirect('scan_product')


def clear_scan_session(request: HttpRequest) -> JsonResponse:
    """
    Clear scan-related session data (useful for resetting state).
    """
    try:
        for key in [SESSION_SCAN_KEY, SESSION_RESULT_KEY, SESSION_BARCODE_KEY]:
            if key in request.session:
                del request.session[key]
                
        request.session.modified = True
        return JsonResponse({'success': True, 'message': 'Scan session cleared'})
        
    except Exception as e:
        logger.error(f"Error clearing scan session: {e}")
        return JsonResponse({'success': False, 'message': 'Failed to clear session'}, status=500)

