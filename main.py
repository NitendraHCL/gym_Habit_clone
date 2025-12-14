"""
Gym Habit - FastAPI Backend Server (MongoDB Version)
Habit Health by HCL Healthcare
"""

from fastapi import FastAPI, HTTPException, Query, Form, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
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

# Initialize FastAPI app
app = FastAPI(
    title="Gym Habit API",
    description="Partner Gym Finder for Habit Health",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: ["https://habithealth.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database managers (will be initialized on startup)
gym_db = MongoGymDatabase()
lead_manager = MongoLeadManager()

# Mount static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")


# ============================================================================
# STARTUP/SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_db_client():
    """Connect to MongoDB on startup"""
    await MongoDB.connect_db()
    await gym_db.initialize()
    await lead_manager.initialize()
    print("[OK] MongoDB connection initialized")


@app.on_event("shutdown")
async def shutdown_db_client():
    """Close MongoDB connection on shutdown"""
    await MongoDB.close_db()
    print("[OK] MongoDB connection closed")


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

    @validator('phone')
    def validate_phone(cls, v):
        """Validate 10-digit Indian phone number"""
        if not v.isdigit() or len(v) != 10:
            raise ValueError('Phone must be 10 digits')
        if not v[0] in '6789':
            raise ValueError('Phone must start with 6, 7, 8, or 9')
        return v

    @validator('full_name')
    def validate_name(cls, v):
        """Validate name length"""
        if len(v) < 3:
            raise ValueError('Name must be at least 3 characters')
        if len(v) > 100:
            raise ValueError('Name must be less than 100 characters')
        return v.strip()

    @validator('preferred_plan')
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

    # Calculate subscription plans
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
    """
    lead = await lead_manager.get_lead_by_id(lead_id)

    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")

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
        "Gym Name",
        "Partner",
        "Preferred Plan",
        "Payment Status",
        "Payment Amount",
        "Payment Link",
        "Billing Address",
        "Message",
        "Comments Count"
    ])

    # Write data rows
    for lead in leads:
        created_at = lead.get('created_at', '')
        if isinstance(created_at, datetime):
            created_at = created_at.strftime('%Y-%m-%d %H:%M:%S')

        user_location = lead.get('user_location', {})
        payment = lead.get('payment', {})
        comments = lead.get('comments', [])

        writer.writerow([
            lead.get('lead_id', ''),
            created_at,
            lead.get('status', ''),
            lead.get('full_name', ''),
            lead.get('email', ''),
            lead.get('phone', ''),
            user_location.get('city', ''),
            lead.get('gym_name', ''),
            lead.get('partner_name', ''),
            lead.get('preferred_plan', ''),
            payment.get('status', ''),
            payment.get('amount', ''),
            payment.get('payment_link', ''),
            lead.get('billing_address', ''),
            lead.get('message', ''),
            len(comments)
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

    # Prevent self-deactivation
    if user_id == current_user.get('user_id'):
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

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
