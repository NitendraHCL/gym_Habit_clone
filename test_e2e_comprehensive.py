"""
COMPREHENSIVE END-TO-END TEST SUITE
Tests complete flow: Admin Panel → Database → Frontend
Tests all edge cases and data consistency
"""

import requests
import json
import time
from datetime import datetime
from pymongo import MongoClient
from config import MONGODB_URL, MONGODB_DB_NAME

# Configuration
BASE_URL = "http://localhost:8000"
ADMIN_EMAIL = "admin@habithealth.com"
ADMIN_PASSWORD = "Admin@2025"

# MongoDB Connection
mongo_client = None
db = None

# Test Results
test_results = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "tests": [],
    "edge_cases": [],
    "start_time": datetime.now().isoformat()
}

# Colors for console output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def log_test(module, test_name, status, message="", edge_case=False):
    """Log test result"""
    test_results["total"] += 1
    if status == "PASS":
        test_results["passed"] += 1
        symbol = "✓"
        color = Colors.GREEN
    else:
        test_results["failed"] += 1
        symbol = "✗"
        color = Colors.RED

    result = {
        "module": module,
        "test": test_name,
        "status": status,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "edge_case": edge_case
    }
    test_results["tests"].append(result)

    if edge_case:
        test_results["edge_cases"].append(result)

    print(f"{color}{symbol} [{module}] {test_name}: {status}{Colors.RESET}")
    if message:
        print(f"  → {message}")

def setup_database():
    """Setup MongoDB connection"""
    global mongo_client, db
    try:
        mongo_client = MongoClient(MONGODB_URL)
        db = mongo_client[MONGODB_DB_NAME]
        # Test connection
        db.command('ping')
        log_test("Setup", "MongoDB connection", "PASS", f"Connected to {MONGODB_DB_NAME}")
        return True
    except Exception as e:
        log_test("Setup", "MongoDB connection", "FAIL", str(e))
        return False

def cleanup_test_data():
    """Clean up test data from database"""
    if db is None:
        return

    try:
        # Delete test gyms
        result = db.gyms.delete_many({"gym_name": {"$regex": "^TEST_"}})
        # Delete test leads
        result2 = db.leads.delete_many({"full_name": {"$regex": "^TEST_"}})
        log_test("Cleanup", "Remove test data", "PASS", f"Removed {result.deleted_count} gyms, {result2.deleted_count} leads")
    except Exception as e:
        log_test("Cleanup", "Remove test data", "FAIL", str(e))

def get_auth_token():
    """Get authentication token"""
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            log_test("Auth", "Get JWT token", "PASS", f"Token: {token[:20]}...")
            return token
        else:
            log_test("Auth", "Get JWT token", "FAIL", f"Status: {response.status_code}")
            return None
    except Exception as e:
        log_test("Auth", "Get JWT token", "FAIL", str(e))
        return None

# ============================================================================
# TEST 1: ADMIN CREATES GYM → VERIFY IN DB → CHECK FRONTEND
# ============================================================================

def test_gym_create_flow(token):
    """E2E Test: Create gym in admin panel → Verify in DB → Check frontend"""
    print("\n" + "="*80)
    print("E2E TEST 1: GYM CREATE FLOW (Admin → DB → Frontend)")
    print("="*80)

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    test_gym_id = None

    # Step 1: Create gym via admin API
    gym_data = {
        "gym_name": "TEST_E2E_Gym_Create",
        "partner_name": "Cult",
        "address": "TEST 123 Main Street, Andheri West, Mumbai",
        "city": "Mumbai",
        "state": "Maharashtra",
        "pincode": "400053",
        "latitude": 19.1350,
        "longitude": 72.8352,
        "amenities": ["Cardio", "Weights", "Yoga", "Swimming"],
        "subscription_amount": 2999,
        "custom_plans": {
            "1_month": 2999,
            "3_months": 8500,
            "6_months": 16500,
            "12_months": 32000
        }
    }

    try:
        response = requests.post(f"{BASE_URL}/api/admin/gyms", headers=headers, json=gym_data)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                test_gym_id = data.get("gym_id")
                log_test("E2E-Create", "Step 1: Admin creates gym via API", "PASS", f"Gym ID: {test_gym_id}")
            else:
                log_test("E2E-Create", "Step 1: Admin creates gym via API", "FAIL", "Success flag false")
                return
        else:
            log_test("E2E-Create", "Step 1: Admin creates gym via API", "FAIL", f"Status: {response.status_code}, Body: {response.text}")
            return
    except Exception as e:
        log_test("E2E-Create", "Step 1: Admin creates gym via API", "FAIL", str(e))
        return

    # Small delay for DB write
    time.sleep(1)

    # Step 2: Verify gym exists in MongoDB
    try:
        gym_in_db = db.gyms.find_one({"gym_id": test_gym_id})
        if gym_in_db:
            # Verify all fields
            checks = [
                ("gym_name", gym_data["gym_name"]),
                ("partner_name", gym_data["partner_name"]),
                ("city", gym_data["city"]),
                ("subscription_amount", gym_data["subscription_amount"]),
                ("is_active", True)
            ]

            all_match = True
            for field, expected in checks:
                if gym_in_db.get(field) != expected:
                    log_test("E2E-Create", f"Step 2: Verify DB field '{field}'", "FAIL", f"Expected: {expected}, Got: {gym_in_db.get(field)}")
                    all_match = False

            if all_match:
                log_test("E2E-Create", "Step 2: Verify gym in MongoDB", "PASS", "All fields match")

            # Verify custom plans
            if "custom_plans" in gym_in_db:
                log_test("E2E-Create", "Step 2: Verify custom plans in DB", "PASS", f"Plans: {gym_in_db['custom_plans']}")
            else:
                log_test("E2E-Create", "Step 2: Verify custom plans in DB", "FAIL", "Custom plans not saved")

            # Verify GeoJSON location
            if "location" in gym_in_db and gym_in_db["location"].get("type") == "Point":
                coords = gym_in_db["location"]["coordinates"]
                if coords == [gym_data["longitude"], gym_data["latitude"]]:
                    log_test("E2E-Create", "Step 2: Verify GeoJSON location", "PASS", f"Coords: {coords}")
                else:
                    log_test("E2E-Create", "Step 2: Verify GeoJSON location", "FAIL", f"Coords mismatch")
            else:
                log_test("E2E-Create", "Step 2: Verify GeoJSON location", "FAIL", "No GeoJSON location")
        else:
            log_test("E2E-Create", "Step 2: Verify gym in MongoDB", "FAIL", "Gym not found in DB")
            return
    except Exception as e:
        log_test("E2E-Create", "Step 2: Verify gym in MongoDB", "FAIL", str(e))
        return

    # Step 3: Check gym appears on frontend (public API)
    try:
        response = requests.get(f"{BASE_URL}/api/gyms")
        if response.status_code == 200:
            data = response.json()
            gyms = data.get("gyms", [])
            test_gym = next((g for g in gyms if g.get("id") == test_gym_id or g.get("gym_id") == test_gym_id), None)

            if test_gym:
                log_test("E2E-Create", "Step 3: Gym appears on frontend", "PASS", f"Found in {len(gyms)} total gyms")

                # Verify frontend data matches
                if test_gym.get("gym_name") == gym_data["gym_name"]:
                    log_test("E2E-Create", "Step 3: Frontend data matches", "PASS", "Name matches")
                else:
                    log_test("E2E-Create", "Step 3: Frontend data matches", "FAIL", "Name mismatch")
            else:
                log_test("E2E-Create", "Step 3: Gym appears on frontend", "FAIL", "Gym not found in public API")
        else:
            log_test("E2E-Create", "Step 3: Gym appears on frontend", "FAIL", f"Status: {response.status_code}")
    except Exception as e:
        log_test("E2E-Create", "Step 3: Gym appears on frontend", "FAIL", str(e))

    # Step 4: Check gym details endpoint
    try:
        response = requests.get(f"{BASE_URL}/api/gyms/{test_gym_id}")
        if response.status_code == 200:
            data = response.json()
            if "subscription_plans" in data:
                plans = data["subscription_plans"]
                log_test("E2E-Create", "Step 4: Gym details with plans", "PASS", f"Plans: {list(plans.keys())}")

                # Verify custom plan calculation
                if "1_month" in plans:
                    expected_total = gym_data["custom_plans"]["1_month"]
                    actual_total = plans["1_month"]["total"]
                    if actual_total == expected_total:
                        log_test("E2E-Create", "Step 4: Custom plan calculation", "PASS", f"₹{actual_total}")
                    else:
                        log_test("E2E-Create", "Step 4: Custom plan calculation", "FAIL", f"Expected ₹{expected_total}, got ₹{actual_total}")
            else:
                log_test("E2E-Create", "Step 4: Gym details with plans", "FAIL", "No subscription plans")
        else:
            log_test("E2E-Create", "Step 4: Gym details with plans", "FAIL", f"Status: {response.status_code}")
    except Exception as e:
        log_test("E2E-Create", "Step 4: Gym details with plans", "FAIL", str(e))

    return test_gym_id

# ============================================================================
# TEST 2: ADMIN EDITS GYM → VERIFY IN DB → CHECK FRONTEND UPDATE
# ============================================================================

def test_gym_edit_flow(token, gym_id):
    """E2E Test: Edit gym in admin panel → Verify in DB → Check frontend update"""
    print("\n" + "="*80)
    print("E2E TEST 2: GYM EDIT FLOW (Admin → DB → Frontend)")
    print("="*80)

    if not gym_id:
        log_test("E2E-Edit", "Edit flow", "SKIP", "No gym ID provided")
        return

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Step 1: Edit gym via admin API
    updated_data = {
        "gym_name": "TEST_E2E_Gym_EDITED",
        "partner_name": "Cult",
        "address": "TEST 456 Updated Street, Andheri West, Mumbai",
        "city": "Mumbai",
        "state": "Maharashtra",
        "pincode": "400053",
        "latitude": 19.1350,
        "longitude": 72.8352,
        "amenities": ["Cardio", "Weights", "Yoga", "Swimming", "Sauna"],  # Added Sauna
        "subscription_amount": 3499,  # Changed price
        "custom_plans": {
            "1_month": 3499,
            "3_months": 9900,
            "6_months": 19000,
            "12_months": 36000
        }
    }

    try:
        response = requests.put(f"{BASE_URL}/api/admin/gyms/{gym_id}", headers=headers, json=updated_data)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                log_test("E2E-Edit", "Step 1: Admin edits gym via API", "PASS", f"Updated gym {gym_id}")
            else:
                log_test("E2E-Edit", "Step 1: Admin edits gym via API", "FAIL", "Success flag false")
                return
        else:
            log_test("E2E-Edit", "Step 1: Admin edits gym via API", "FAIL", f"Status: {response.status_code}, Body: {response.text}")
            return
    except Exception as e:
        log_test("E2E-Edit", "Step 1: Admin edits gym via API", "FAIL", str(e))
        return

    # Small delay for DB update
    time.sleep(1)

    # Step 2: Verify updates in MongoDB
    try:
        gym_in_db = db.gyms.find_one({"gym_id": gym_id})
        if gym_in_db:
            checks = [
                ("gym_name", "TEST_E2E_Gym_EDITED"),
                ("subscription_amount", 3499),
                ("address", "TEST 456 Updated Street, Andheri West, Mumbai")
            ]

            all_match = True
            for field, expected in checks:
                if gym_in_db.get(field) != expected:
                    log_test("E2E-Edit", f"Step 2: Verify updated '{field}' in DB", "FAIL", f"Expected: {expected}, Got: {gym_in_db.get(field)}")
                    all_match = False

            if all_match:
                log_test("E2E-Edit", "Step 2: Verify updates in MongoDB", "PASS", "All changes saved")

            # Verify amenities updated
            if "Sauna" in gym_in_db.get("amenities", []):
                log_test("E2E-Edit", "Step 2: Verify amenities updated", "PASS", "Sauna added")
            else:
                log_test("E2E-Edit", "Step 2: Verify amenities updated", "FAIL", "Amenities not updated")
        else:
            log_test("E2E-Edit", "Step 2: Verify updates in MongoDB", "FAIL", "Gym not found in DB")
            return
    except Exception as e:
        log_test("E2E-Edit", "Step 2: Verify updates in MongoDB", "FAIL", str(e))
        return

    # Step 3: Check updates appear on frontend
    try:
        response = requests.get(f"{BASE_URL}/api/gyms/{gym_id}")
        if response.status_code == 200:
            data = response.json()
            if data.get("gym_name") == "TEST_E2E_Gym_EDITED":
                log_test("E2E-Edit", "Step 3: Updated name on frontend", "PASS", data["gym_name"])
            else:
                log_test("E2E-Edit", "Step 3: Updated name on frontend", "FAIL", f"Got: {data.get('gym_name')}")

            if data.get("subscription_amount") == 3499:
                log_test("E2E-Edit", "Step 3: Updated price on frontend", "PASS", f"₹{data['subscription_amount']}")
            else:
                log_test("E2E-Edit", "Step 3: Updated price on frontend", "FAIL", f"Got: ₹{data.get('subscription_amount')}")

            # Check if Sauna is in amenities
            amenities = data.get("amenities_list", []) or data.get("amenities", "").split(",")
            if "Sauna" in amenities or "Sauna" in str(amenities):
                log_test("E2E-Edit", "Step 3: Updated amenities on frontend", "PASS", "Sauna visible")
            else:
                log_test("E2E-Edit", "Step 3: Updated amenities on frontend", "FAIL", f"Amenities: {amenities}")
        else:
            log_test("E2E-Edit", "Step 3: Check updates on frontend", "FAIL", f"Status: {response.status_code}")
    except Exception as e:
        log_test("E2E-Edit", "Step 3: Check updates on frontend", "FAIL", str(e))

# ============================================================================
# TEST 3: USER SUBMITS LEAD → VERIFY IN DB → CHECK ADMIN PANEL
# ============================================================================

def test_lead_submission_flow(token):
    """E2E Test: User submits subscription → Verify in DB → Check admin panel"""
    print("\n" + "="*80)
    print("E2E TEST 3: LEAD SUBMISSION FLOW (Frontend → DB → Admin)")
    print("="*80)

    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: Submit subscription request (as user)
    lead_data = {
        "gym_id": 1,
        "gym_name": "Cult Fit Andheri West",
        "partner_name": "Cult",
        "full_name": "TEST_E2E_User",
        "email": "test_e2e@example.com",
        "phone": "9876543210",
        "preferred_plan": "6-month",
        "billing_address": "TEST 789 User Street, Mumbai - 400001",
        "message": "E2E test subscription",
        "user_latitude": 19.1350,
        "user_longitude": 72.8352,
        "user_city": "Mumbai"
    }

    lead_id = None
    try:
        response = requests.post(f"{BASE_URL}/api/subscription/request", json=lead_data)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                lead_id = data.get("lead_id")
                log_test("E2E-Lead", "Step 1: User submits subscription", "PASS", f"Lead ID: {lead_id}")
            else:
                log_test("E2E-Lead", "Step 1: User submits subscription", "FAIL", "Success flag false")
                return
        else:
            log_test("E2E-Lead", "Step 1: User submits subscription", "FAIL", f"Status: {response.status_code}")
            return
    except Exception as e:
        log_test("E2E-Lead", "Step 1: User submits subscription", "FAIL", str(e))
        return

    time.sleep(1)

    # Step 2: Verify lead in MongoDB
    try:
        lead_in_db = db.leads.find_one({"lead_id": lead_id})
        if lead_in_db:
            checks = [
                ("full_name", "TEST_E2E_User"),
                ("email", "test_e2e@example.com"),
                ("phone", "9876543210"),
                ("status", "new"),
                ("preferred_plan", "6-month")
            ]

            all_match = True
            for field, expected in checks:
                if lead_in_db.get(field) != expected:
                    log_test("E2E-Lead", f"Step 2: Verify '{field}' in DB", "FAIL", f"Expected: {expected}, Got: {lead_in_db.get(field)}")
                    all_match = False

            if all_match:
                log_test("E2E-Lead", "Step 2: Verify lead in MongoDB", "PASS", "All fields saved correctly")

            # Verify initial status
            if lead_in_db.get("status") == "new":
                log_test("E2E-Lead", "Step 2: Verify initial status", "PASS", "Status: new")

            # Verify payment pending
            if lead_in_db.get("payment", {}).get("status") == "pending":
                log_test("E2E-Lead", "Step 2: Verify payment status", "PASS", "Payment: pending")
        else:
            log_test("E2E-Lead", "Step 2: Verify lead in MongoDB", "FAIL", "Lead not found in DB")
            return
    except Exception as e:
        log_test("E2E-Lead", "Step 2: Verify lead in MongoDB", "FAIL", str(e))
        return

    # Step 3: Check lead appears in admin panel
    try:
        response = requests.get(f"{BASE_URL}/api/admin/leads?page=1&limit=20", headers=headers)
        if response.status_code == 200:
            data = response.json()
            leads = data.get("leads", [])
            test_lead = next((l for l in leads if l.get("lead_id") == lead_id), None)

            if test_lead:
                log_test("E2E-Lead", "Step 3: Lead appears in admin panel", "PASS", f"Found in leads list")

                # Verify admin can see details
                if test_lead.get("full_name") == "TEST_E2E_User":
                    log_test("E2E-Lead", "Step 3: Admin sees lead details", "PASS", "Name visible")
            else:
                log_test("E2E-Lead", "Step 3: Lead appears in admin panel", "FAIL", "Lead not in admin list")
        else:
            log_test("E2E-Lead", "Step 3: Check admin panel", "FAIL", f"Status: {response.status_code}")
    except Exception as e:
        log_test("E2E-Lead", "Step 3: Check admin panel", "FAIL", str(e))

    return lead_id

# ============================================================================
# TEST 4: ADMIN UPDATES LEAD STATUS → VERIFY AUDIT TRAIL
# ============================================================================

def test_lead_status_update_flow(token, lead_id):
    """E2E Test: Admin updates lead status → Verify audit trail → Check updates"""
    print("\n" + "="*80)
    print("E2E TEST 4: LEAD STATUS UPDATE FLOW (Admin → Audit → DB)")
    print("="*80)

    if not lead_id:
        log_test("E2E-Status", "Status update flow", "SKIP", "No lead ID provided")
        return

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Step 1: Update lead status
    try:
        status_data = {
            "status": "contacted",
            "reason": "E2E test: Called customer successfully"
        }
        response = requests.patch(f"{BASE_URL}/api/admin/leads/{lead_id}/status", headers=headers, json=status_data)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                log_test("E2E-Status", "Step 1: Update lead status", "PASS", "Status: new → contacted")
            else:
                log_test("E2E-Status", "Step 1: Update lead status", "FAIL", "Success flag false")
                return
        else:
            log_test("E2E-Status", "Step 1: Update lead status", "FAIL", f"Status: {response.status_code}")
            return
    except Exception as e:
        log_test("E2E-Status", "Step 1: Update lead status", "FAIL", str(e))
        return

    time.sleep(1)

    # Step 2: Verify in database
    try:
        lead_in_db = db.leads.find_one({"lead_id": lead_id})
        if lead_in_db:
            if lead_in_db.get("status") == "contacted":
                log_test("E2E-Status", "Step 2: Verify status in DB", "PASS", "Status updated to 'contacted'")
            else:
                log_test("E2E-Status", "Step 2: Verify status in DB", "FAIL", f"Status: {lead_in_db.get('status')}")

            # Step 3: Verify audit trail
            audit_log = lead_in_db.get("audit_log", [])
            if len(audit_log) > 0:
                latest_audit = audit_log[-1]
                if latest_audit.get("action") == "status_change" and latest_audit.get("new_value") == "contacted":
                    log_test("E2E-Status", "Step 3: Verify audit trail", "PASS", f"Audit entry created with reason")

                    if latest_audit.get("reason") == "E2E test: Called customer successfully":
                        log_test("E2E-Status", "Step 3: Verify audit reason", "PASS", "Reason saved correctly")
                else:
                    log_test("E2E-Status", "Step 3: Verify audit trail", "FAIL", "Wrong audit entry")
            else:
                log_test("E2E-Status", "Step 3: Verify audit trail", "FAIL", "No audit log found")
        else:
            log_test("E2E-Status", "Step 2: Verify status in DB", "FAIL", "Lead not found")
    except Exception as e:
        log_test("E2E-Status", "Step 2-3: Verify updates and audit", "FAIL", str(e))

# ============================================================================
# TEST 5: EDGE CASES
# ============================================================================

def test_edge_cases(token):
    """Test edge cases and error handling"""
    print("\n" + "="*80)
    print("EDGE CASE TESTING")
    print("="*80)

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Edge Case 1: Invalid phone number
    try:
        lead_data = {
            "gym_id": 1,
            "gym_name": "Test Gym",
            "partner_name": "Cult",
            "full_name": "Test User",
            "email": "test@example.com",
            "phone": "1234567890",  # Invalid: starts with 1
            "preferred_plan": "3-month",
            "billing_address": "Test Address",
            "user_latitude": 19.1350,
            "user_longitude": 72.8352,
            "user_city": "Mumbai"
        }
        response = requests.post(f"{BASE_URL}/api/subscription/request", json=lead_data)
        if response.status_code == 422 or response.status_code == 400:
            log_test("Edge Cases", "Invalid phone number (starts with 1)", "PASS", "Correctly rejected", edge_case=True)
        else:
            log_test("Edge Cases", "Invalid phone number (starts with 1)", "FAIL", f"Should reject, got: {response.status_code}", edge_case=True)
    except Exception as e:
        log_test("Edge Cases", "Invalid phone number", "FAIL", str(e), edge_case=True)

    # Edge Case 2: Invalid email
    try:
        lead_data = {
            "gym_id": 1,
            "gym_name": "Test Gym",
            "partner_name": "Cult",
            "full_name": "Test User",
            "email": "not-an-email",  # Invalid email
            "phone": "9876543210",
            "preferred_plan": "3-month",
            "billing_address": "Test Address",
            "user_latitude": 19.1350,
            "user_longitude": 72.8352,
            "user_city": "Mumbai"
        }
        response = requests.post(f"{BASE_URL}/api/subscription/request", json=lead_data)
        if response.status_code == 422:
            log_test("Edge Cases", "Invalid email format", "PASS", "Correctly rejected", edge_case=True)
        else:
            log_test("Edge Cases", "Invalid email format", "FAIL", f"Should reject, got: {response.status_code}", edge_case=True)
    except Exception as e:
        log_test("Edge Cases", "Invalid email format", "FAIL", str(e), edge_case=True)

    # Edge Case 3: Accessing admin endpoint without auth
    try:
        response = requests.get(f"{BASE_URL}/api/admin/leads")
        if response.status_code == 401 or response.status_code == 403:
            log_test("Edge Cases", "Admin endpoint without auth", "PASS", "Correctly blocked", edge_case=True)
        else:
            log_test("Edge Cases", "Admin endpoint without auth", "FAIL", f"Should block, got: {response.status_code}", edge_case=True)
    except Exception as e:
        log_test("Edge Cases", "Admin endpoint without auth", "FAIL", str(e), edge_case=True)

    # Edge Case 4: Delete non-existent gym
    try:
        response = requests.delete(f"{BASE_URL}/api/admin/gyms/999999", headers=headers)
        if response.status_code == 404 or (response.status_code == 200 and not response.json().get("success")):
            log_test("Edge Cases", "Delete non-existent gym", "PASS", "Handled gracefully", edge_case=True)
        else:
            log_test("Edge Cases", "Delete non-existent gym", "FAIL", f"Status: {response.status_code}", edge_case=True)
    except Exception as e:
        log_test("Edge Cases", "Delete non-existent gym", "FAIL", str(e), edge_case=True)

    # Edge Case 5: Search with invalid coordinates
    try:
        response = requests.get(f"{BASE_URL}/api/gyms/nearby?lat=200&lon=200&limit=10")
        # Should either return empty or handle gracefully
        if response.status_code in [200, 400, 422]:
            log_test("Edge Cases", "Search with invalid coordinates", "PASS", "Handled gracefully", edge_case=True)
        else:
            log_test("Edge Cases", "Search with invalid coordinates", "FAIL", f"Status: {response.status_code}", edge_case=True)
    except Exception as e:
        log_test("Edge Cases", "Search with invalid coordinates", "FAIL", str(e), edge_case=True)

    # Edge Case 6: Very long name (boundary testing)
    try:
        long_name = "A" * 200  # 200 characters
        lead_data = {
            "gym_id": 1,
            "gym_name": "Test Gym",
            "partner_name": "Cult",
            "full_name": long_name,
            "email": "test@example.com",
            "phone": "9876543210",
            "preferred_plan": "3-month",
            "billing_address": "Test Address",
            "user_latitude": 19.1350,
            "user_longitude": 72.8352,
            "user_city": "Mumbai"
        }
        response = requests.post(f"{BASE_URL}/api/subscription/request", json=lead_data)
        if response.status_code == 422:
            log_test("Edge Cases", "Name too long (>100 chars)", "PASS", "Correctly rejected", edge_case=True)
        else:
            log_test("Edge Cases", "Name too long (>100 chars)", "FAIL", f"Should reject, got: {response.status_code}", edge_case=True)
    except Exception as e:
        log_test("Edge Cases", "Name too long", "FAIL", str(e), edge_case=True)

# ============================================================================
# TEST 6: GYM DELETE FLOW
# ============================================================================

def test_gym_delete_flow(token, gym_id):
    """E2E Test: Delete gym → Verify soft delete → Check frontend"""
    print("\n" + "="*80)
    print("E2E TEST 6: GYM DELETE FLOW (Admin → DB → Frontend)")
    print("="*80)

    if not gym_id:
        log_test("E2E-Delete", "Delete flow", "SKIP", "No gym ID provided")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: Delete gym
    try:
        response = requests.delete(f"{BASE_URL}/api/admin/gyms/{gym_id}", headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                log_test("E2E-Delete", "Step 1: Admin deletes gym", "PASS", f"Deleted gym {gym_id}")
            else:
                log_test("E2E-Delete", "Step 1: Admin deletes gym", "FAIL", "Success flag false")
                return
        else:
            log_test("E2E-Delete", "Step 1: Admin deletes gym", "FAIL", f"Status: {response.status_code}")
            return
    except Exception as e:
        log_test("E2E-Delete", "Step 1: Admin deletes gym", "FAIL", str(e))
        return

    time.sleep(1)

    # Step 2: Verify soft delete in DB (is_active = false)
    try:
        gym_in_db = db.gyms.find_one({"gym_id": gym_id})
        if gym_in_db:
            if gym_in_db.get("is_active") == False:
                log_test("E2E-Delete", "Step 2: Verify soft delete in DB", "PASS", "is_active = False")
            else:
                log_test("E2E-Delete", "Step 2: Verify soft delete in DB", "FAIL", f"is_active = {gym_in_db.get('is_active')}")
        else:
            log_test("E2E-Delete", "Step 2: Verify soft delete in DB", "FAIL", "Gym completely deleted (should be soft delete)")
    except Exception as e:
        log_test("E2E-Delete", "Step 2: Verify soft delete in DB", "FAIL", str(e))

    # Step 3: Verify gym does NOT appear on frontend
    try:
        response = requests.get(f"{BASE_URL}/api/gyms")
        if response.status_code == 200:
            data = response.json()
            gyms = data.get("gyms", [])
            deleted_gym = next((g for g in gyms if g.get("id") == gym_id or g.get("gym_id") == gym_id), None)

            if deleted_gym is None:
                log_test("E2E-Delete", "Step 3: Deleted gym hidden from frontend", "PASS", "Not in public list")
            else:
                log_test("E2E-Delete", "Step 3: Deleted gym hidden from frontend", "FAIL", "Still appears in public list")
        else:
            log_test("E2E-Delete", "Step 3: Check frontend", "FAIL", f"Status: {response.status_code}")
    except Exception as e:
        log_test("E2E-Delete", "Step 3: Check frontend", "FAIL", str(e))

# ============================================================================
# GENERATE REPORT
# ============================================================================

def generate_report():
    """Generate comprehensive test report"""
    test_results["end_time"] = datetime.now().isoformat()

    print("\n" + "="*80)
    print("COMPREHENSIVE E2E TEST REPORT")
    print("="*80)
    print(f"\nStart Time: {test_results['start_time']}")
    print(f"End Time: {test_results['end_time']}")
    print(f"\nTotal Tests: {test_results['total']}")
    print(f"{Colors.GREEN}Passed: {test_results['passed']} ✓{Colors.RESET}")
    print(f"{Colors.RED}Failed: {test_results['failed']} ✗{Colors.RESET}")

    if test_results['total'] > 0:
        pass_rate = (test_results['passed'] / test_results['total']) * 100
        print(f"\nPass Rate: {pass_rate:.1f}%")

    # Edge cases summary
    print(f"\nEdge Cases Tested: {len(test_results['edge_cases'])}")
    edge_pass = sum(1 for e in test_results['edge_cases'] if e['status'] == 'PASS')
    print(f"Edge Cases Passed: {edge_pass}/{len(test_results['edge_cases'])}")

    # Module breakdown
    print("\n" + "="*80)
    print("MODULE BREAKDOWN")
    print("="*80)

    modules = {}
    for test in test_results["tests"]:
        module = test["module"]
        if module not in modules:
            modules[module] = {"total": 0, "passed": 0, "failed": 0}
        modules[module]["total"] += 1
        if test["status"] == "PASS":
            modules[module]["passed"] += 1
        else:
            modules[module]["failed"] += 1

    for module, stats in sorted(modules.items()):
        pass_rate = (stats["passed"] / stats["total"]) * 100 if stats["total"] > 0 else 0
        status = f"{Colors.GREEN}✓ PASS{Colors.RESET}" if pass_rate == 100 else f"{Colors.YELLOW}⚠ PARTIAL{Colors.RESET}" if pass_rate >= 50 else f"{Colors.RED}✗ FAIL{Colors.RESET}"
        print(f"\n{module}:")
        print(f"  Tests: {stats['total']} | Passed: {stats['passed']} | Failed: {stats['failed']} | Rate: {pass_rate:.1f}% | {status}")

    # Failed tests details
    failed_tests = [t for t in test_results["tests"] if t["status"] == "FAIL"]
    if failed_tests:
        print("\n" + "="*80)
        print("FAILED TESTS DETAILS")
        print("="*80)
        for test in failed_tests:
            print(f"\n{Colors.RED}✗ [{test['module']}] {test['test']}{Colors.RESET}")
            print(f"  Reason: {test['message']}")

    # Sign-off
    print("\n" + "="*80)
    print("SIGN-OFF RECOMMENDATION")
    print("="*80)

    if test_results['failed'] == 0:
        print(f"\n{Colors.GREEN}✓✓✓ ALL TESTS PASSED ✓✓✓{Colors.RESET}")
        print("All E2E flows working correctly")
        print("Admin → DB → Frontend consistency verified")
        print("Sign-off: APPROVED")
    elif pass_rate >= 90:
        print(f"\n{Colors.YELLOW}⚠ MINOR ISSUES DETECTED{Colors.RESET}")
        print("System is mostly functional")
        print("Sign-off: CONDITIONAL")
    else:
        print(f"\n{Colors.RED}✗ ISSUES DETECTED{Colors.RESET}")
        print("Please review failed tests")
        print("Sign-off: NOT RECOMMENDED")

    print("\n" + "="*80)

    # Save to file
    with open("C:\\Users\\hp\\gym_habit\\test_e2e_report.json", "w") as f:
        json.dump(test_results, f, indent=2)
    print("\nDetailed report saved to: test_e2e_report.json")

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run all E2E tests"""
    print("\n" + "="*80)
    print("GYM HABIT - COMPREHENSIVE END-TO-END TEST SUITE")
    print("Testing: Admin Panel → Database → Frontend Consistency")
    print("="*80)

    # Setup
    if not setup_database():
        print("Failed to connect to MongoDB. Exiting.")
        return

    # Cleanup old test data
    cleanup_test_data()

    # Get auth token
    token = get_auth_token()
    if not token:
        print("Failed to authenticate. Exiting.")
        return

    # Run E2E tests
    test_gym_id = test_gym_create_flow(token)
    test_gym_edit_flow(token, test_gym_id)
    test_lead_id = test_lead_submission_flow(token)
    test_lead_status_update_flow(token, test_lead_id)
    test_edge_cases(token)
    test_gym_delete_flow(token, test_gym_id)

    # Cleanup test data
    cleanup_test_data()

    # Generate report
    generate_report()

    # Close MongoDB connection
    if mongo_client:
        mongo_client.close()

if __name__ == "__main__":
    main()
