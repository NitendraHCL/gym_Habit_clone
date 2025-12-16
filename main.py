"""
Gym Habit - FastAPI Backend Server (MongoDB Version)
Habit Health by HCL Healthcare
"""

from fastapi import FastAPI, HTTPException, Query, Form, Depends, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from contextlib import asynccontextmanager
import uvicorn
import os
import requests
import csv
import io
from datetime import datetime

from mongo_database import MongoGymDatabase, MongoLeadManager, calculate_subscription_plans
from mongodb import MongoDB
from auth import create_access_token, get_current_user, verify_password
import config

# Initialize database managers
gym_db = MongoGymDatabase()
lead_manager = MongoLeadManager()


# ============================================================================
# LIFESPAN EVENTS
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events"""
    # Startup
    await MongoDB.connect_db()
    await gym_db.initialize()
    await lead_manager.initialize()
    print("[OK] MongoDB connection initialized")

    yield

    # Shutdown
    await MongoDB.close_db()
    print("[OK] MongoDB connection closed")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Gym Habit API",
    description="Partner Gym Finder for Habit Health",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: ["https://habithealth.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")


# ============================================================================
# HELPER FUNCTIONS - LOCATION SEARCH
# ============================================================================

def is_pincode(search_text: str) -> bool:
    """Check if input is a 6-digit Indian pincode"""
    cleaned = search_text.strip()
    return cleaned.isdigit() and len(cleaned) == 6


def geocode_location(location_text: str) -> dict:
    """
    Convert location text to lat/lon using Google Geocoding API

    Args:
        location_text: City, town, or area (e.g., "Andheri Mumbai")

    Returns:
        {
            "lat": 19.1136,
            "lon": 72.8697,
            "formatted_address": "Andheri West, Mumbai, Maharashtra, India",
            "city": "Mumbai"
        }
    """
    if not config.GOOGLE_GEOCODING_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Google Geocoding API key not configured"
        )

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": location_text,
        "key": config.GOOGLE_GEOCODING_API_KEY,
        "region": "in",  # Bias results to India
        "components": "country:IN"  # Restrict to India only
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        if data['status'] == 'OK' and len(data['results']) > 0:
            result = data['results'][0]
            location = result['geometry']['location']

            # Extract city from address components
            city = None
            for component in result.get('address_components', []):
                if 'locality' in component['types']:
                    city = component['long_name']
                    break
                elif 'administrative_area_level_2' in component['types']:
                    city = component['long_name']

            return {
                "lat": location['lat'],
                "lon": location['lng'],
                "formatted_address": result['formatted_address'],
                "city": city
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Location not found: {location_text}"
            )
    except requests.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calling Google Geocoding API: {str(e)}"
        )


# ============================================================================
# PYDANTIC MODELS FOR REQUEST VALIDATION
# ============================================================================

class SubscriptionRequest(BaseModel):
    """Subscription form data"""
    gym_id: int
    gym_name: str
    partner_name: str
    full_name: str
    email: Optional[EmailStr] = ""
    phone: str
    preferred_plan: str
    billing_address: str
    message: Optional[str] = ""
    user_latitude: Optional[float] = None
    user_longitude: Optional[float] = None
    user_city: Optional[str] = None

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        """Validate 10-digit Indian phone number"""
        if not v.isdigit() or len(v) != 10:
            raise ValueError('Phone must be 10 digits')
        if not v[0] in '6789':
            raise ValueError('Phone must start with 6, 7, 8, or 9')
        return v

    @field_validator('full_name')
    @classmethod
    def validate_name(cls, v):
        """Validate name length"""
        if len(v) < 3:
            raise ValueError('Name must be at least 3 characters')
        if len(v) > 100:
            raise ValueError('Name must be less than 100 characters')
        return v.strip()

    @field_validator('preferred_plan')
    @classmethod
    def validate_plan(cls, v):
        """Validate plan selection"""
        valid_plans = ['1-month', '3-month', '12-month']
        if v not in valid_plans:
            raise ValueError(f'Plan must be one of: {valid_plans}')
        return v


class LoginRequest(BaseModel):
    """Login request"""
    email: EmailStr
    password: str


class GymCreateRequest(BaseModel):
    """Request model for creating a new gym"""
    gym_name: str
    partner_name: str
    address: str
    city: str
    state: str
    pincode: str
    latitude: float
    longitude: float
    amenities: list[str]
    subscription_amount: Optional[int] = 1499
    icon: Optional[str] = None  # Emoji or base64 image
    custom_plans: Optional[dict] = None  # Custom pricing for 1_month, 3_months, 6_months, 12_months

    @field_validator('pincode')
    @classmethod
    def validate_pincode(cls, v):
        """Validate 6-digit pincode"""
        if not v.isdigit() or len(v) != 6:
            raise ValueError('Pincode must be 6 digits')
        return v

    @field_validator('gym_name', 'partner_name', 'city', 'state')
    @classmethod
    def validate_non_empty(cls, v):
        """Validate non-empty strings"""
        if not v or len(v.strip()) == 0:
            raise ValueError('Field cannot be empty')
        return v.strip()


class PartnerCreateRequest(BaseModel):
    """Request model for creating a new partner"""
    name: str
    description: Optional[str] = ""
    icon: Optional[str] = None  # Emoji or base64 image

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate partner name"""
        if not v or len(v.strip()) == 0:
            raise ValueError('Partner name cannot be empty')
        if len(v) > 100:
            raise ValueError('Partner name must be less than 100 characters')
        return v.strip()


# ============================================================================
# FRONTEND ROUTES
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve main user page"""
    try:
        return FileResponse("frontend/index.html")
    except:
        return HTMLResponse("<h1>Frontend not found. Please build frontend first.</h1>")


@app.get("/admin", response_class=HTMLResponse)
async def serve_admin():
    """Serve admin panel"""
    try:
        return FileResponse("frontend/admin.html")
    except:
        return HTMLResponse("<h1>Admin panel not found.</h1>")


# ============================================================================
# API ENDPOINTS - PUBLIC
# ============================================================================

@app.get("/api/partners")
async def get_partners():
    """
    Get list of all gym partners with counts
    Returns: {"partners": [{"name": "Cult", "count": 10}], "total": 5}
    """
    partners = await gym_db.get_all_partners()
    return {
        "partners": partners,
        "total": len(partners)
    }


@app.get("/api/gyms")
async def get_gyms(partner: Optional[str] = None):
    """
    Get all gyms, optionally filtered by partner
    Query params:
        partner (optional): Filter by partner name
    """
    if partner:
        gyms = await gym_db.get_gyms_by_partner(partner)
        return {
            "gyms": gyms,
            "total": len(gyms),
            "partner": partner
        }
    else:
        gyms = await gym_db.get_all_gyms()
        return {
            "gyms": gyms,
            "total": len(gyms)
        }


@app.get("/api/gyms/nearby")
async def get_nearby_gyms(
    lat: float = Query(..., description="User latitude"),
    lon: float = Query(..., description="User longitude"),
    partner: Optional[str] = Query(None, description="Filter by partner"),
    limit: int = Query(10, ge=1, le=50, description="Max results")
):
    """
    Find nearest gyms based on user location
    Query params:
        lat: User's latitude
        lon: User's longitude
        partner (optional): Filter by partner name
        limit (optional): Max number of results (default: 10)
    """
    gyms = await gym_db.get_nearby_gyms(lat, lon, partner=partner, limit=limit)

    return {
        "gyms": gyms,
        "total": len(gyms),
        "user_location": {"latitude": lat, "longitude": lon}
    }


@app.get("/api/gyms/search-by-location")
async def search_gyms_by_location(
    location: str = Query(..., description="City, area, or 6-digit pincode"),
    partner: Optional[str] = Query(None, description="Filter by partner"),
    limit: int = Query(20, ge=1, le=50, description="Max results")
):
    """
    Search gyms by location text or pincode (optimized for iframe use)

    Supports three search modes:
    1. Pincode (6 digits): Instant search using pincode index
    2. Text location: Uses Google Geocoding API + geospatial search
    3. City name: Direct city filtering + distance sort

    Query params:
        location: "400053" OR "Andheri Mumbai" OR "Mumbai"
        partner (optional): Filter by partner name
        limit (optional): Max number of results (default: 20)

    Returns:
        {
            "gyms": [...],
            "total": 10,
            "search_type": "pincode" | "geocoded" | "city",
            "location": "Formatted address or pincode",
            "coordinates": {"lat": 19.11, "lon": 72.86}
        }
    """
    location_clean = location.strip()

    # MODE 1: Pincode Search (Instant, no API call)
    if is_pincode(location_clean):
        gyms = await gym_db.search_by_pincode(location_clean, limit=limit)

        # Apply partner filter if provided
        if partner:
            gyms = [g for g in gyms if g['partner_name'].lower() == partner.lower()]

        return {
            "gyms": gyms[:limit],
            "total": len(gyms),
            "search_type": "pincode",
            "location": f"Pincode {location_clean}",
            "coordinates": None
        }

    # MODE 2: Text Location Search (Google API + geospatial)
    try:
        geocode_result = geocode_location(location_clean)

        # Use city filter if available to speed up search
        gyms = await gym_db.get_nearby_gyms(
            user_lat=geocode_result['lat'],
            user_lon=geocode_result['lon'],
            partner=partner,
            city=geocode_result.get('city'),
            limit=limit
        )

        return {
            "gyms": gyms,
            "total": len(gyms),
            "search_type": "geocoded",
            "location": geocode_result['formatted_address'],
            "coordinates": {
                "lat": geocode_result['lat'],
                "lon": geocode_result['lon']
            }
        }
    except HTTPException:
        # If geocoding fails, return empty result
        raise


@app.get("/api/gyms/{gym_id}")
async def get_gym_details(gym_id: int):
    """
    Get detailed information about a specific gym
    Path param:
        gym_id: Gym ID
    """
    gym = await gym_db.get_gym_by_id(gym_id)

    if not gym:
        raise HTTPException(status_code=404, detail="Gym not found")

    # Calculate subscription plans - use custom plans if available, otherwise auto-calculate
    if gym.get('custom_plans'):
        # Use custom plans and calculate derived values
        plans = {}
        custom = gym['custom_plans']

        for key, total in custom.items():
            duration_map = {'1_month': 1, '3_months': 3, '6_months': 6, '12_months': 12}
            months = duration_map.get(key, 1)
            duration_text = f"{months} month{'s' if months > 1 else ''}"

            # Calculate monthly rate and savings based on base price
            base_price = gym['subscription_amount']
            expected_total = base_price * months
            savings = expected_total - total
            monthly = total // months
            discount = int((savings / expected_total) * 100) if expected_total > 0 else 0

            plans[key.replace('_', '-')] = {
                'duration': duration_text,
                'total': total,
                'monthly': monthly,
                'savings': max(0, savings),
                'discount': discount
            }
    else:
        # Auto-calculate plans based on base price
        base_price = gym['subscription_amount']
        plans = calculate_subscription_plans(base_price)

    # Parse amenities
    amenities_list = [a.strip() for a in gym['amenities'].split(',')]

    response = gym.copy()
    response['subscription_plans'] = plans
    response['amenities_list'] = amenities_list

    return response


@app.post("/api/subscription/request")
async def submit_subscription_request(request: SubscriptionRequest):
    """
    Submit subscription inquiry form
    Body: SubscriptionRequest model
    """
    try:
        # Validate gym exists
        gym = await gym_db.get_gym_by_id(request.gym_id)
        if not gym:
            raise HTTPException(status_code=404, detail="Gym not found")

        # Save lead
        lead_id = await lead_manager.save_lead(request.dict())

        return {
            "success": True,
            "message": "Thank you! Our wellness team will contact you within 24 hours to help you start your fitness journey.",
            "lead_id": lead_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API ENDPOINTS - AUTHENTICATION
# ============================================================================

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    """
    Admin/Facilitator login with JWT
    Body: {"email": "admin@habithealth.com", "password": "Admin@2025"}
    Returns: {"access_token": "...", "user": {...}}
    """
    # Find user
    user = await MongoDB.db.users.find_one({"email": request.email})

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # Verify password
    if not verify_password(request.password, user['password_hash']):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # Check if user is active
    if not user.get('is_active', False):
        raise HTTPException(
            status_code=403,
            detail="Account is inactive. Please contact administrator."
        )

    # Create JWT token
    token_data = {
        "user_id": str(user['_id']),
        "email": user['email'],
        "role": user['role'],
        "name": user['name']
    }
    access_token = create_access_token(token_data)

    # Update last login
    from datetime import datetime
    await MongoDB.db.users.update_one(
        {"_id": user['_id']},
        {
            "$set": {"last_login": datetime.utcnow()},
            "$inc": {"login_count": 1}
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "email": user['email'],
            "name": user['name'],
            "role": user['role']
        }
    }


@app.get("/api/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Get current logged-in user information
    Requires JWT authentication
    """
    # Fetch full user details from database
    user = await MongoDB.db.users.find_one({"email": current_user['email']})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "email": user['email'],
        "name": user['name'],
        "role": user['role'],
        "is_active": user.get('is_active', True),
        "created_at": user.get('created_at'),
        "last_login": user.get('last_login'),
        "login_count": user.get('login_count', 0)
    }


@app.post("/api/auth/change-password")
async def change_password(
    old_password: str = Form(...),
    new_password: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Change user password
    Requires JWT authentication and current password verification
    """
    # Validate new password
    if len(new_password) < 8:
        raise HTTPException(
            status_code=400,
            detail="New password must be at least 8 characters long"
        )

    # Get user from database
    user = await MongoDB.db.users.find_one({"email": current_user['email']})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify old password
    if not verify_password(old_password, user['password_hash']):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    # Hash new password
    from auth import hash_password
    new_password_hash = hash_password(new_password)

    # Update password
    await MongoDB.db.users.update_one(
        {"email": current_user['email']},
        {
            "$set": {
                "password_hash": new_password_hash,
                "password_updated_at": datetime.utcnow()
            }
        }
    )

    return {"message": "Password changed successfully"}


@app.post("/api/auth/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Logout endpoint (optional - mostly for client-side token cleanup)
    In stateless JWT, logout is handled client-side by removing the token
    This endpoint can be used for audit logging
    """
    # Log logout event (optional)
    await MongoDB.db.users.update_one(
        {"email": current_user['email']},
        {"$set": {"last_logout": datetime.utcnow()}}
    )

    return {"message": "Logged out successfully"}


# ============================================================================
# API ENDPOINTS - ADMIN (Protected)
# ============================================================================

@app.get("/api/admin/leads")
async def get_leads(
    current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    payment_status: Optional[str] = Query(None),
    city: Optional[str] = Query(None)
):
    """
    Get all leads with filters (admin/facilitator only)
    Requires JWT authentication
    """
    # Calculate skip
    skip = (page - 1) * per_page

    # Get leads
    result = await lead_manager.get_all_leads(
        skip=skip,
        limit=per_page,
        status_filter=status,
        payment_status_filter=payment_status,
        city_filter=city
    )

    return result


@app.get("/api/admin/stats")
async def get_admin_stats(current_user: dict = Depends(get_current_user)):
    """
    Get admin dashboard statistics
    Requires JWT authentication
    """
    # Count leads by status
    pipeline_status = [
        {
            "$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }
        }
    ]
    status_counts = await MongoDB.db.leads.aggregate(pipeline_status).to_list(None)

    # Count leads by payment status
    pipeline_payment = [
        {
            "$group": {
                "_id": "$payment.status",
                "count": {"$sum": 1}
            }
        }
    ]
    payment_counts = await MongoDB.db.leads.aggregate(pipeline_payment).to_list(None)

    # Total gyms
    total_gyms = await MongoDB.db.gyms.count_documents({"is_active": True})

    # Total leads
    total_leads = await MongoDB.db.leads.count_documents({})

    return {
        "total_leads": total_leads,
        "total_gyms": total_gyms,
        "status_breakdown": {item['_id']: item['count'] for item in status_counts},
        "payment_breakdown": {item['_id']: item['count'] for item in payment_counts}
    }


@app.get("/api/admin/leads/{lead_id}")
async def get_lead_details(
    lead_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get detailed information for a specific lead
    Requires JWT authentication
    Auto-assigns lead to current user when viewed
    """
    lead = await lead_manager.get_lead_by_id(lead_id)

    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")

    # Assign lead to current user when they view it
    await lead_manager.assign_lead(lead_id, current_user['email'], current_user['name'])

    # Fetch updated lead with assignment
    lead = await lead_manager.get_lead_by_id(lead_id)

    return lead


@app.patch("/api/admin/leads/{lead_id}/status")
async def update_lead_status_endpoint(
    lead_id: str,
    status: str = Form(...),
    reason: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Update lead status
    Valid statuses: new, contacted, interested, not_interested, closed
    """
    valid_statuses = ["new", "contacted", "interested", "not_interested", "closed"]

    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )

    success = await lead_manager.update_lead_status(
        lead_id=lead_id,
        new_status=status,
        updated_by=current_user['email'],
        reason=reason
    )

    if not success:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")

    # Assign lead to user who made the change
    await lead_manager.assign_lead(lead_id, current_user['email'], current_user.get('name', current_user['email']))

    return {"message": "Status updated successfully", "lead_id": lead_id, "new_status": status}


@app.post("/api/admin/leads/{lead_id}/comments")
async def add_comment_endpoint(
    lead_id: str,
    comment: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Add a comment to a lead
    """
    if not comment or len(comment.strip()) == 0:
        raise HTTPException(status_code=400, detail="Comment cannot be empty")

    success = await lead_manager.add_comment(
        lead_id=lead_id,
        comment_text=comment,
        added_by=current_user['email']
    )

    if not success:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")

    # Assign lead to user who made the change
    await lead_manager.assign_lead(lead_id, current_user['email'], current_user.get('name', current_user['email']))

    return {"message": "Comment added successfully", "lead_id": lead_id}


@app.patch("/api/admin/leads/{lead_id}/payment")
async def update_payment_endpoint(
    lead_id: str,
    payment_status: str = Form(...),
    payment_link: Optional[str] = Form(None),
    amount: Optional[int] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Update payment information for a lead
    Valid payment statuses: pending, link_shared, paid, failed
    """
    valid_payment_statuses = ["pending", "link_shared", "paid", "failed"]

    if payment_status not in valid_payment_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid payment status. Must be one of: {', '.join(valid_payment_statuses)}"
        )

    success = await lead_manager.update_payment(
        lead_id=lead_id,
        payment_status=payment_status,
        updated_by=current_user['email'],
        payment_link=payment_link,
        amount=amount
    )

    if not success:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")

    # Assign lead to user who made the change
    await lead_manager.assign_lead(lead_id, current_user['email'], current_user.get('name', current_user['email']))

    return {
        "message": "Payment updated successfully",
        "lead_id": lead_id,
        "payment_status": payment_status
    }


@app.patch("/api/admin/leads/{lead_id}/plan")
async def update_plan_endpoint(
    lead_id: str,
    new_plan: str = Form(...),
    reason: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Update the membership plan for a lead
    Valid plans: 1 Month, 3 Months, 6 Months, 12 Months
    """
    valid_plans = ["1 Month", "3 Months", "6 Months", "12 Months"]

    if new_plan not in valid_plans:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid plan. Must be one of: {', '.join(valid_plans)}"
        )

    success = await lead_manager.update_plan(
        lead_id=lead_id,
        new_plan=new_plan,
        updated_by=current_user['email'],
        reason=reason
    )

    if not success:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")

    # Assign lead to user who made the change
    await lead_manager.assign_lead(lead_id, current_user['email'], current_user.get('name', current_user['email']))

    return {"message": "Plan updated successfully", "lead_id": lead_id, "new_plan": new_plan}


@app.get("/api/admin/leads/{lead_id}/audit")
async def get_audit_trail_endpoint(
    lead_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get audit trail for a lead
    Returns all changes made to the lead
    """
    audit_trail = await lead_manager.get_audit_trail(lead_id)

    if audit_trail is None:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")

    return {"lead_id": lead_id, "audit_trail": audit_trail}


# ============================================================================
# API ENDPOINTS - GYM & PARTNER MANAGEMENT (Admin Only)
# ============================================================================

@app.post("/api/admin/gyms")
async def create_gym_endpoint(
    request: GymCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new gym (admin only)
    Body: GymCreateRequest model
    """
    # Check if user is admin
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Access forbidden. Admin only.")

    try:
        # Debug: Log custom_plans
        print(f"[DEBUG] Creating gym '{request.gym_name}' with custom_plans: {request.custom_plans}")

        # Create gym using gym_db manager
        gym_id = await gym_db.create_gym(
            gym_name=request.gym_name,
            partner_name=request.partner_name,
            address=request.address,
            city=request.city,
            state=request.state,
            pincode=request.pincode,
            latitude=request.latitude,
            longitude=request.longitude,
            amenities=request.amenities,
            subscription_amount=request.subscription_amount,
            icon=request.icon,
            custom_plans=request.custom_plans
        )

        return {
            "message": "Gym created successfully",
            "gym_id": gym_id,
            "gym_name": request.gym_name,
            "partner_name": request.partner_name
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating gym: {str(e)}")


@app.post("/api/admin/gyms/upload")
async def upload_gyms_csv_endpoint(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload gyms from CSV file (admin only)
    CSV Format: gym_name,partner_name,address,city,state,pincode,latitude,longitude,amenities,subscription_amount,plan_1m,plan_3m,plan_6m,plan_12m
    Note: plan_1m, plan_3m, plan_6m, plan_12m are optional custom plan prices
    """
    # Check if user is admin
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Access forbidden. Admin only.")

    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    try:
        # Read CSV file
        content = await file.read()
        decoded_content = content.decode('utf-8').splitlines()

        csv_reader = csv.DictReader(decoded_content)

        gyms_created = 0
        errors = []

        for i, row in enumerate(csv_reader, start=2):  # Start at 2 (line 1 is header)
            try:
                # Parse amenities (pipe-separated for CSV)
                amenities_str = row.get('amenities', '')
                if amenities_str:
                    amenities = [a.strip() for a in amenities_str.split('|')]
                else:
                    amenities = []

                # Parse custom plans if provided
                custom_plans = None
                if row.get('plan_1m') or row.get('plan_3m') or row.get('plan_6m') or row.get('plan_12m'):
                    custom_plans = {}
                    if row.get('plan_1m'):
                        custom_plans['1_month'] = int(row['plan_1m'])
                    if row.get('plan_3m'):
                        custom_plans['3_months'] = int(row['plan_3m'])
                    if row.get('plan_6m'):
                        custom_plans['6_months'] = int(row['plan_6m'])
                    if row.get('plan_12m'):
                        custom_plans['12_months'] = int(row['plan_12m'])

                # Create gym
                await gym_db.create_gym(
                    gym_name=row['gym_name'],
                    partner_name=row['partner_name'],
                    address=row['address'],
                    city=row['city'],
                    state=row['state'],
                    pincode=row['pincode'],
                    latitude=float(row['latitude']),
                    longitude=float(row['longitude']),
                    amenities=amenities,
                    subscription_amount=int(row.get('subscription_amount', 1499)),
                    custom_plans=custom_plans
                )

                gyms_created += 1

            except Exception as e:
                errors.append(f"Line {i}: {str(e)}")

        return {
            "message": f"Successfully uploaded {gyms_created} gyms",
            "gyms_created": gyms_created,
            "errors": errors if errors else None
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")


@app.delete("/api/admin/gyms/{gym_id}")
async def delete_gym_endpoint(
    gym_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a gym (admin only)
    Note: Soft delete - gym is marked as inactive
    """
    # Check if user is admin
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Access forbidden. Admin only.")

    success = await gym_db.delete_gym(gym_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Gym {gym_id} not found")

    return {
        "message": "Gym deleted successfully",
        "gym_id": gym_id
    }


@app.post("/api/admin/partners")
async def create_partner_endpoint(
    request: PartnerCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new partner (admin only)
    Body: PartnerCreateRequest model
    Note: Partners are derived from gyms. This creates a placeholder.
    """
    # Check if user is admin
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Access forbidden. Admin only.")

    success = await gym_db.create_partner_entry(
        partner_name=request.name,
        description=request.description,
        icon=request.icon
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Partner '{request.name}' already exists"
        )

    return {
        "message": "Partner created successfully",
        "partner_name": request.name,
        "note": "Add gyms to this partner to activate it"
    }


@app.delete("/api/admin/partners/{partner_name}")
async def delete_partner_endpoint(
    partner_name: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a partner and all its gyms (admin only)
    Note: Soft delete - all gyms are marked as inactive
    """
    # Check if user is admin
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Access forbidden. Admin only.")

    gyms_deleted = await gym_db.delete_partner(partner_name)

    if gyms_deleted == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Partner '{partner_name}' not found or has no gyms"
        )

    return {
        "message": "Partner deleted successfully",
        "partner_name": partner_name,
        "gyms_deleted": gyms_deleted
    }


@app.get("/api/admin/reports/leads.csv")
async def export_leads_csv(
    current_user: dict = Depends(get_current_user),
    status: Optional[str] = Query(None),
    payment_status: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None)
):
    """
    Export leads to CSV with optional filters
    Requires JWT authentication
    """
    # Parse date filters if provided
    date_from = None
    date_to = None

    if from_date:
        try:
            date_from = datetime.strptime(from_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid from_date format. Use YYYY-MM-DD")

    if to_date:
        try:
            date_to = datetime.strptime(to_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid to_date format. Use YYYY-MM-DD")

    # Get all leads (no pagination for export)
    result = await lead_manager.get_all_leads(
        skip=0,
        limit=10000,  # Max 10k records for CSV
        status_filter=status,
        payment_status_filter=payment_status,
        city_filter=city,
        date_from=date_from,
        date_to=date_to
    )

    leads = result.get('leads', [])

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        "Lead ID",
        "Created At",
        "Status",
        "Full Name",
        "Email",
        "Phone",
        "City",
        "State",
        "Gym Name",
        "Partner",
        "Preferred Plan",
        "Payment Status",
        "Payment Amount",
        "Payment Link",
        "Billing Address",
        "Message",
        "Comments Count",
        "Total Audit Entries",
        "Latest Status Update",
        "Latest Payment Update",
        "Latest Plan Change",
        "All Comments"
    ])

    # Write data rows
    for lead in leads:
        created_at = lead.get('created_at', '')
        if isinstance(created_at, datetime):
            created_at = created_at.strftime('%Y-%m-%d %H:%M:%S')

        user_location = lead.get('user_location', {})
        payment = lead.get('payment', {})
        comments = lead.get('comments', [])
        audit_log = lead.get('audit_log', [])

        # Extract latest audit entries
        latest_status_update = ""
        latest_payment_update = ""
        latest_plan_change = ""

        # Process audit log (most recent first)
        for entry in reversed(audit_log):
            action = entry.get('action', '')
            timestamp = entry.get('timestamp', '')
            user = entry.get('user', '')

            if isinstance(timestamp, datetime):
                timestamp = timestamp.strftime('%Y-%m-%d %H:%M')

            if action == 'status_change' and not latest_status_update:
                old_val = entry.get('old_value', '')
                new_val = entry.get('new_value', '')
                reason = entry.get('reason', '')
                latest_status_update = f"{timestamp} | {user} | {old_val} → {new_val}"
                if reason:
                    latest_status_update += f" | Reason: {reason}"

            elif action == 'payment_update' and not latest_payment_update:
                old_val = entry.get('old_value', '')
                new_val = entry.get('new_value', '')
                details = entry.get('details', {})
                latest_payment_update = f"{timestamp} | {user} | {old_val} → {new_val}"
                if details:
                    if 'amount' in details:
                        latest_payment_update += f" | Amount: ₹{details['amount']}"
                    if 'payment_link' in details:
                        latest_payment_update += f" | Link: {details['payment_link']}"

            elif action == 'plan_change' and not latest_plan_change:
                old_val = entry.get('old_value', '')
                new_val = entry.get('new_value', '')
                reason = entry.get('reason', '')
                latest_plan_change = f"{timestamp} | {user} | {old_val} → {new_val}"
                if reason:
                    latest_plan_change += f" | Reason: {reason}"

        # Format all comments
        all_comments = ""
        for comment in comments:
            comment_time = comment.get('timestamp', '')
            if isinstance(comment_time, datetime):
                comment_time = comment_time.strftime('%Y-%m-%d %H:%M')
            comment_user = comment.get('added_by', '')
            comment_text = comment.get('comment', '')
            all_comments += f"[{comment_time} - {comment_user}] {comment_text}; "

        writer.writerow([
            lead.get('lead_id', ''),
            created_at,
            lead.get('status', ''),
            lead.get('full_name', ''),
            lead.get('email', ''),
            lead.get('phone', ''),
            user_location.get('city', ''),
            user_location.get('state', ''),
            lead.get('gym_name', ''),
            lead.get('partner_name', ''),
            lead.get('preferred_plan', ''),
            payment.get('status', ''),
            payment.get('amount', ''),
            payment.get('payment_link', ''),
            lead.get('billing_address', ''),
            lead.get('message', ''),
            len(comments),
            len(audit_log),
            latest_status_update,
            latest_payment_update,
            latest_plan_change,
            all_comments.strip()
        ])

    # Get CSV content
    csv_content = output.getvalue()
    output.close()

    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"gym_habit_leads_{timestamp}.csv"

    # Return as streaming response
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


# ============================================================================
# API ENDPOINTS - USER MANAGEMENT (Admin Only)
# ============================================================================

@app.get("/api/admin/users")
async def get_all_users(current_user: dict = Depends(get_current_user)):
    """
    Get all users (admin only)
    """
    # Check if user is admin
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Access forbidden. Admin only.")

    # Fetch all users
    users = await MongoDB.db.users.find({}).to_list(None)

    # Remove sensitive data
    safe_users = []
    for user in users:
        safe_users.append({
            "user_id": str(user['_id']),
            "email": user['email'],
            "name": user['name'],
            "role": user['role'],
            "is_active": user.get('is_active', True),
            "created_at": user.get('created_at'),
            "last_login": user.get('last_login'),
            "login_count": user.get('login_count', 0)
        })

    return {"users": safe_users, "total": len(safe_users)}



@app.put("/api/admin/gyms/{gym_id}")
async def update_gym_endpoint(
    gym_id: int,
    request: GymCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update an existing gym (admin only)
    """
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Access forbidden. Admin only.")

    try:
        success = await gym_db.update_gym(
            gym_id=gym_id,
            gym_name=request.gym_name,
            partner_name=request.partner_name,
            address=request.address,
            city=request.city,
            state=request.state,
            pincode=request.pincode,
            latitude=request.latitude,
            longitude=request.longitude,
            amenities=request.amenities,
            subscription_amount=request.subscription_amount,
            icon=request.icon,
            custom_plans=request.custom_plans
        )

        if not success:
            raise HTTPException(status_code=404, detail="Gym not found")

        return {"success": True, "message": "Gym updated successfully"}
    except Exception as e:
        print(f"Error updating gym: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/admin/partners/{partner_name}")
async def update_partner_endpoint(
    partner_name: str,
    request: PartnerCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update an existing partner (admin only)
    """
    print(f"\n=== UPDATE PARTNER ENDPOINT ===")
    print(f"Partner Name (from URL): {partner_name}")
    print(f"New Name: {request.name}")
    print(f"Description: {request.description}")
    print(f"Has Icon: {request.icon is not None}")
    if request.icon:
        print(f"Icon length: {len(request.icon)}")
    print(f"User: {current_user.get('email')}")

    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Access forbidden. Admin only.")

    try:
        success = await gym_db.update_partner(
            old_name=partner_name,
            new_name=request.name,
            description=request.description,
            icon=request.icon
        )

        print(f"Update result: {success}")

        if not success:
            print(f"[ERROR] Partner update failed - partner not found: {partner_name}")
            raise HTTPException(status_code=404, detail=f"Partner '{partner_name}' not found")

        print(f"[SUCCESS] Partner updated: {partner_name} -> {request.name}")
        return {"success": True, "message": "Partner updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Partner update exception: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/users")
async def create_user(
    email: EmailStr = Form(...),
    name: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new user (admin only)
    Valid roles: admin, facilitator, viewer
    """
    # Check if user is admin
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Access forbidden. Admin only.")

    # Validate role
    valid_roles = ["admin", "facilitator", "viewer"]
    if role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
        )

    # Validate password
    if len(password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters long"
        )

    # Check if user already exists
    existing_user = await MongoDB.db.users.find_one({"email": email})
    if existing_user:
        raise HTTPException(status_code=400, detail=f"User with email {email} already exists")

    # Hash password
    from auth import hash_password
    password_hash = hash_password(password)

    # Create user document
    new_user = {
        "email": email,
        "name": name,
        "password_hash": password_hash,
        "role": role,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "created_by": current_user['email'],
        "login_count": 0
    }

    # Insert user
    result = await MongoDB.db.users.insert_one(new_user)

    return {
        "message": "User created successfully",
        "user": {
            "user_id": str(result.inserted_id),
            "email": email,
            "name": name,
            "role": role
        }
    }


@app.patch("/api/admin/users/{user_id}")
async def update_user(
    user_id: str,
    role: Optional[str] = Form(None),
    is_active: Optional[bool] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Update user role or active status (admin only)
    """
    # Check if user is admin
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Access forbidden. Admin only.")

    # Validate role if provided
    if role is not None:
        valid_roles = ["admin", "facilitator", "viewer"]
        if role not in valid_roles:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
            )

    # Build update document
    from bson import ObjectId
    update_data = {"updated_at": datetime.utcnow(), "updated_by": current_user['email']}

    if role is not None:
        update_data["role"] = role

    if is_active is not None:
        update_data["is_active"] = is_active

    # Update user
    try:
        result = await MongoDB.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid user ID: {str(e)}")

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    return {"message": "User updated successfully", "user_id": user_id}


@app.delete("/api/admin/users/{user_id}")
async def deactivate_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Deactivate a user (admin only)
    Note: Users are not deleted, just marked as inactive
    """
    # Check if user is admin
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="Access forbidden. Admin only.")

    # Check if target user is admin - only facilitators can be deactivated
    try:
        from bson import ObjectId
        target_user = await MongoDB.db.users.find_one({"_id": ObjectId(user_id)})
        if target_user and target_user.get('role') == 'admin':
            raise HTTPException(status_code=403, detail="Cannot deactivate admin users")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Deactivate user
    from bson import ObjectId
    try:
        result = await MongoDB.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "is_active": False,
                    "deactivated_at": datetime.utcnow(),
                    "deactivated_by": current_user['email']
                }
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid user ID: {str(e)}")

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    return {"message": "User deactivated successfully", "user_id": user_id}


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    total_gyms = await MongoDB.db.gyms.count_documents({"is_active": True})
    partners = await gym_db.get_all_partners()

    return {
        "status": "healthy",
        "database": "mongodb",
        "gyms_loaded": total_gyms,
        "partners": len(partners)
    }


# ============================================================================
# SERVER STARTUP
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("GYM HABIT - Habit Health Partner Gym Finder (MongoDB)")
    print("=" * 60)
    print("[INFO] Starting server...")
    print("[INFO] Main page: http://localhost:8000")
    print("[INFO] Admin panel: http://localhost:8000/admin")
    print("[INFO] API docs: http://localhost:8000/docs")
    print("=" * 60)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

