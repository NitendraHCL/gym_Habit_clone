"""
Comprehensive Test Suite for Gym Habit Application
Tests all modules and provides sign-off report
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
ADMIN_EMAIL = "admin@habithealth.com"
ADMIN_PASSWORD = "Admin@2025"

# Test Results
test_results = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "tests": []
}

def log_test(module, test_name, status, message=""):
    """Log test result"""
    test_results["total"] += 1
    if status == "PASS":
        test_results["passed"] += 1
        symbol = "✓"
        color = "GREEN"
    else:
        test_results["failed"] += 1
        symbol = "✗"
        color = "RED"

    result = {
        "module": module,
        "test": test_name,
        "status": status,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    test_results["tests"].append(result)

    print(f"{symbol} [{module}] {test_name}: {status}")
    if message:
        print(f"  → {message}")

def test_authentication():
    """Test Module: Authentication and Login"""
    print("\n" + "="*80)
    print("MODULE: AUTHENTICATION AND LOGIN")
    print("="*80)

    # Test 1: Login with valid credentials
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })

        if response.status_code == 200:
            data = response.json()
            if "access_token" in data:
                log_test("Authentication", "Login with valid credentials", "PASS", f"Token received: {data['access_token'][:20]}...")
                return data["access_token"]
            else:
                log_test("Authentication", "Login with valid credentials", "FAIL", "No access token in response")
                return None
        else:
            log_test("Authentication", "Login with valid credentials", "FAIL", f"Status: {response.status_code}")
            return None
    except Exception as e:
        log_test("Authentication", "Login with valid credentials", "FAIL", str(e))
        return None

    # Test 2: Login with invalid credentials
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpassword"
        })

        if response.status_code in [401, 403]:
            log_test("Authentication", "Login with invalid credentials (should fail)", "PASS", "Correctly rejected")
        else:
            log_test("Authentication", "Login with invalid credentials (should fail)", "FAIL", f"Unexpected status: {response.status_code}")
    except Exception as e:
        log_test("Authentication", "Login with invalid credentials", "FAIL", str(e))

def test_user_facing_website(token):
    """Test Module: User-Facing Website"""
    print("\n" + "="*80)
    print("MODULE: USER-FACING WEBSITE")
    print("="*80)

    # Test 1: Get partners
    try:
        response = requests.get(f"{BASE_URL}/api/partners")
        if response.status_code == 200:
            data = response.json()
            if "partners" in data and len(data["partners"]) > 0:
                log_test("User Website", "Get partners list", "PASS", f"Found {len(data['partners'])} partners")
            else:
                log_test("User Website", "Get partners list", "FAIL", "No partners found")
        else:
            log_test("User Website", "Get partners list", "FAIL", f"Status: {response.status_code}")
    except Exception as e:
        log_test("User Website", "Get partners list", "FAIL", str(e))

    # Test 2: Get all gyms
    try:
        response = requests.get(f"{BASE_URL}/api/gyms")
        if response.status_code == 200:
            data = response.json()
            if "gyms" in data and len(data["gyms"]) > 0:
                log_test("User Website", "Get all gyms", "PASS", f"Found {len(data['gyms'])} gyms")
            else:
                log_test("User Website", "Get all gyms", "FAIL", "No gyms found")
        else:
            log_test("User Website", "Get all gyms", "FAIL", f"Status: {response.status_code}")
    except Exception as e:
        log_test("User Website", "Get all gyms", "FAIL", str(e))

    # Test 3: Search nearby gyms
    try:
        response = requests.get(f"{BASE_URL}/api/gyms/nearby?lat=28.6139&lon=77.2090&limit=10")
        if response.status_code == 200:
            data = response.json()
            if "gyms" in data:
                log_test("User Website", "Search nearby gyms (geolocation)", "PASS", f"Found {len(data['gyms'])} nearby gyms")
            else:
                log_test("User Website", "Search nearby gyms (geolocation)", "FAIL", "No gyms found")
        else:
            log_test("User Website", "Search nearby gyms (geolocation)", "FAIL", f"Status: {response.status_code}")
    except Exception as e:
        log_test("User Website", "Search nearby gyms (geolocation)", "FAIL", str(e))

    # Test 4: Search by location (city)
    try:
        response = requests.get(f"{BASE_URL}/api/gyms/search-by-location?location=Mumbai&limit=10")
        if response.status_code == 200:
            data = response.json()
            if "gyms" in data:
                log_test("User Website", "Search by location (Mumbai)", "PASS", f"Found {len(data['gyms'])} gyms")
            else:
                log_test("User Website", "Search by location (Mumbai)", "FAIL", "No gyms found")
        else:
            log_test("User Website", "Search by location (Mumbai)", "FAIL", f"Status: {response.status_code}")
    except Exception as e:
        log_test("User Website", "Search by location (Mumbai)", "FAIL", str(e))

    # Test 5: Get gym details
    try:
        response = requests.get(f"{BASE_URL}/api/gyms/1")
        if response.status_code == 200:
            data = response.json()
            if "gym_name" in data and "subscription_plans" in data:
                log_test("User Website", "Get gym details with plans", "PASS", f"Gym: {data.get('gym_name', 'N/A')}")
            else:
                log_test("User Website", "Get gym details with plans", "FAIL", "Missing data")
        else:
            log_test("User Website", "Get gym details with plans", "FAIL", f"Status: {response.status_code}")
    except Exception as e:
        log_test("User Website", "Get gym details with plans", "FAIL", str(e))

def test_lead_management(token):
    """Test Module: Lead Management"""
    print("\n" + "="*80)
    print("MODULE: LEAD MANAGEMENT")
    print("="*80)

    headers = {"Authorization": f"Bearer {token}"}

    # Test 1: Get dashboard stats
    try:
        response = requests.get(f"{BASE_URL}/api/admin/stats", headers=headers)
        if response.status_code == 200:
            data = response.json()
            if "total_leads" in data:
                log_test("Lead Management", "Get dashboard statistics", "PASS", f"Total leads: {data['total_leads']}")
            else:
                log_test("Lead Management", "Get dashboard statistics", "FAIL", "Missing stats")
        else:
            log_test("Lead Management", "Get dashboard statistics", "FAIL", f"Status: {response.status_code}")
    except Exception as e:
        log_test("Lead Management", "Get dashboard statistics", "FAIL", str(e))

    # Test 2: Get all leads
    try:
        response = requests.get(f"{BASE_URL}/api/admin/leads?page=1&limit=20", headers=headers)
        if response.status_code == 200:
            data = response.json()
            if "leads" in data:
                log_test("Lead Management", "Get paginated leads list", "PASS", f"Found {data.get('total', 0)} leads")
            else:
                log_test("Lead Management", "Get paginated leads list", "FAIL", "No leads data")
        else:
            log_test("Lead Management", "Get paginated leads list", "FAIL", f"Status: {response.status_code}")
    except Exception as e:
        log_test("Lead Management", "Get paginated leads list", "FAIL", str(e))

    # Test 3: Submit subscription request (create lead)
    try:
        lead_data = {
            "gym_id": 1,
            "gym_name": "Test Gym",
            "partner_name": "Cult",
            "full_name": "Test User",
            "email": "test@example.com",
            "phone": "9876543210",
            "preferred_plan": "3-month",
            "billing_address": "Test Address, Mumbai - 400001",
            "message": "Test subscription",
            "user_latitude": 19.0760,
            "user_longitude": 72.8777,
            "user_city": "Mumbai"
        }
        response = requests.post(f"{BASE_URL}/api/subscription/request", json=lead_data)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                log_test("Lead Management", "Submit subscription request", "PASS", f"Lead ID: {data.get('lead_id', 'N/A')}")
            else:
                log_test("Lead Management", "Submit subscription request", "FAIL", "Success flag false")
        else:
            log_test("Lead Management", "Submit subscription request", "FAIL", f"Status: {response.status_code}")
    except Exception as e:
        log_test("Lead Management", "Submit subscription request", "FAIL", str(e))

def test_gym_management(token):
    """Test Module: Gym Management"""
    print("\n" + "="*80)
    print("MODULE: GYM MANAGEMENT")
    print("="*80)

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Test 1: Get all gyms (admin view)
    try:
        response = requests.get(f"{BASE_URL}/api/gyms", headers=headers)
        if response.status_code == 200:
            data = response.json()
            if "gyms" in data:
                log_test("Gym Management", "View all gyms", "PASS", f"Found {len(data['gyms'])} gyms")
            else:
                log_test("Gym Management", "View all gyms", "FAIL", "No gyms data")
        else:
            log_test("Gym Management", "View all gyms", "FAIL", f"Status: {response.status_code}")
    except Exception as e:
        log_test("Gym Management", "View all gyms", "FAIL", str(e))

    # Test 2: Add new gym
    test_gym_id = None
    try:
        gym_data = {
            "gym_name": "Test Gym For Testing",
            "partner_name": "Cult",
            "address": "Test Address Mumbai",
            "city": "Mumbai",
            "state": "Maharashtra",
            "pincode": "400001",
            "latitude": 19.0760,
            "longitude": 72.8777,
            "amenities": ["Cardio", "Weights", "Yoga"],
            "subscription_amount": 2499
        }
        response = requests.post(f"{BASE_URL}/api/admin/gyms", headers=headers, json=gym_data)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                test_gym_id = data.get("gym_id")
                log_test("Gym Management", "Add new gym", "PASS", f"Gym ID: {test_gym_id}")
            else:
                log_test("Gym Management", "Add new gym", "FAIL", "Success flag false")
        else:
            log_test("Gym Management", "Add new gym", "FAIL", f"Status: {response.status_code}")
    except Exception as e:
        log_test("Gym Management", "Add new gym", "FAIL", str(e))

    # Test 3: Edit gym
    if test_gym_id:
        try:
            update_data = {
                "gym_name": "Test Gym UPDATED",
                "partner_name": "Cult",
                "address": "Updated Test Address Mumbai",
                "city": "Mumbai",
                "state": "Maharashtra",
                "pincode": "400001",
                "latitude": 19.0760,
                "longitude": 72.8777,
                "amenities": ["Cardio", "Weights", "Yoga", "Swimming"],
                "subscription_amount": 2999
            }
            response = requests.put(f"{BASE_URL}/api/admin/gyms/{test_gym_id}", headers=headers, json=update_data)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    log_test("Gym Management", "Edit gym", "PASS", f"Updated gym {test_gym_id}")
                else:
                    log_test("Gym Management", "Edit gym", "FAIL", "Success flag false")
            else:
                log_test("Gym Management", "Edit gym", "FAIL", f"Status: {response.status_code}")
        except Exception as e:
            log_test("Gym Management", "Edit gym", "FAIL", str(e))
    else:
        log_test("Gym Management", "Edit gym", "SKIP", "No gym created to edit")

    # Test 4: Delete gym
    if test_gym_id:
        try:
            response = requests.delete(f"{BASE_URL}/api/admin/gyms/{test_gym_id}", headers=headers)
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    log_test("Gym Management", "Delete gym (soft delete)", "PASS", f"Deleted gym {test_gym_id}")
                else:
                    log_test("Gym Management", "Delete gym (soft delete)", "FAIL", "Success flag false")
            else:
                log_test("Gym Management", "Delete gym (soft delete)", "FAIL", f"Status: {response.status_code}")
        except Exception as e:
            log_test("Gym Management", "Delete gym (soft delete)", "FAIL", str(e))
    else:
        log_test("Gym Management", "Delete gym", "SKIP", "No gym created to delete")

def test_csv_export(token):
    """Test Module: CSV Export"""
    print("\n" + "="*80)
    print("MODULE: CSV EXPORT")
    print("="*80)

    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(f"{BASE_URL}/api/admin/reports/leads.csv", headers=headers)
        if response.status_code == 200:
            if "text/csv" in response.headers.get("Content-Type", ""):
                log_test("CSV Export", "Export leads to CSV", "PASS", f"CSV size: {len(response.content)} bytes")
            else:
                log_test("CSV Export", "Export leads to CSV", "FAIL", "Not CSV format")
        else:
            log_test("CSV Export", "Export leads to CSV", "FAIL", f"Status: {response.status_code}")
    except Exception as e:
        log_test("CSV Export", "Export leads to CSV", "FAIL", str(e))

def generate_report():
    """Generate comprehensive test report"""
    print("\n" + "="*80)
    print("COMPREHENSIVE TEST REPORT")
    print("="*80)
    print(f"\nTest Execution Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nTotal Tests: {test_results['total']}")
    print(f"Passed: {test_results['passed']} ✓")
    print(f"Failed: {test_results['failed']} ✗")

    if test_results['total'] > 0:
        pass_rate = (test_results['passed'] / test_results['total']) * 100
        print(f"Pass Rate: {pass_rate:.1f}%")

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

    for module, stats in modules.items():
        pass_rate = (stats["passed"] / stats["total"]) * 100 if stats["total"] > 0 else 0
        status = "✓ PASS" if pass_rate == 100 else "⚠ PARTIAL" if pass_rate >= 50 else "✗ FAIL"
        print(f"\n{module}:")
        print(f"  Tests: {stats['total']} | Passed: {stats['passed']} | Failed: {stats['failed']} | Rate: {pass_rate:.1f}% | {status}")

    print("\n" + "="*80)
    print("SIGN-OFF RECOMMENDATION")
    print("="*80)

    if test_results['failed'] == 0:
        print("\n✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("System is READY FOR PRODUCTION")
        print("Sign-off: APPROVED")
    elif pass_rate >= 90:
        print("\n⚠ MINOR ISSUES DETECTED")
        print("System is MOSTLY FUNCTIONAL with minor issues")
        print("Sign-off: CONDITIONAL APPROVAL (fix minor issues)")
    elif pass_rate >= 70:
        print("\n⚠⚠ MODERATE ISSUES DETECTED")
        print("System has moderate issues that should be addressed")
        print("Sign-off: NOT RECOMMENDED (fix issues first)")
    else:
        print("\n✗✗✗ CRITICAL ISSUES DETECTED ✗✗✗")
        print("System has critical issues")
        print("Sign-off: REJECTED (major fixes required)")

    print("\n" + "="*80)

    # Save report to file
    with open("C:\\Users\\hp\\gym_habit\\test_report.json", "w") as f:
        json.dump(test_results, f, indent=2)
    print("\nDetailed report saved to: test_report.json")

def main():
    """Main test execution"""
    print("\n" + "="*80)
    print("GYM HABIT - COMPREHENSIVE TEST SUITE")
    print("="*80)
    print(f"Testing against: {BASE_URL}")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Run tests
    token = test_authentication()

    if token:
        test_user_facing_website(token)
        test_lead_management(token)
        test_gym_management(token)
        test_csv_export(token)
    else:
        print("\n⚠ Authentication failed - skipping authenticated tests")

    # Generate report
    generate_report()

if __name__ == "__main__":
    main()
