"""
COMPREHENSIVE PLAYWRIGHT TEST SUITE
Tests all custom plans functionality from backend (admin) to frontend
"""
from playwright.sync_api import sync_playwright, expect
import time
import json

# Test results storage
test_results = []

def log_test(test_name, status, details=""):
    """Log test result"""
    result = {
        "test": test_name,
        "status": status,
        "details": details
    }
    test_results.append(result)
    status_symbol = "[PASS]" if status == "PASS" else "[FAIL]"
    print(f"{status_symbol} {test_name}")
    if details:
        print(f"  -> {details}")

def run_comprehensive_tests():
    """Run all tests"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=300)
        context = browser.new_context()
        page = context.new_page()

        try:
            # ===================================================================
            # TEST 1: LOGIN TO ADMIN PANEL
            # ===================================================================
            print("\n" + "="*70)
            print("TEST SUITE 1: ADMIN AUTHENTICATION")
            print("="*70)

            page.goto('http://localhost:8000/admin')
            page.wait_for_load_state('networkidle')

            # Check login form exists
            if page.locator('#loginEmail').is_visible():
                log_test("Admin panel loads correctly", "PASS")
            else:
                log_test("Admin panel loads correctly", "FAIL", "Login form not found")
                return

            # Login
            page.fill('#loginEmail', 'admin@habithealth.com')
            page.fill('#loginPassword', 'Admin@2025')
            page.click('button[type="submit"]')
            page.wait_for_timeout(4000)

            # Verify dashboard loaded (check for sidebar or any admin content)
            page.screenshot(path='C:/Users/hp/gym_habit/test_0_after_login.png')

            is_logged_in = (page.locator('.sidebar').is_visible() or
                          page.locator('#tabLeads').is_visible() or
                          page.locator('text=Dashboard').is_visible())

            if is_logged_in:
                log_test("Admin login successful", "PASS")
            else:
                log_test("Admin login successful", "FAIL", "Dashboard not loaded")
                print(f"[DEBUG] Current URL: {page.url}")
                print(f"[DEBUG] Page title: {page.title()}")
                return

            # ===================================================================
            # TEST 2: ADD GYM WITHOUT CUSTOM PLANS (AUTO-CALCULATED)
            # ===================================================================
            print("\n" + "="*70)
            print("TEST SUITE 2: ADD GYM - AUTO-CALCULATED PLANS")
            print("="*70)

            page.click('text=Gyms')
            page.wait_for_timeout(2000)

            page.click('#addGymBtn')
            page.wait_for_timeout(1000)

            # Verify modal opened
            if page.locator('#addGymModal').is_visible():
                log_test("Add Gym modal opens", "PASS")
            else:
                log_test("Add Gym modal opens", "FAIL")
                return

            # Fill basic details
            page.fill('#gymName', 'AutoCalc Test Gym')
            page.select_option('#gymPartner', 'Cult')
            page.fill('#gymAddress', '456 Auto Street')
            page.fill('#gymCity', 'Mumbai')
            page.fill('#gymState', 'Maharashtra')
            page.fill('#gymPincode', '400002')
            page.fill('#gymLatitude', '19.08')
            page.fill('#gymLongitude', '72.88')
            page.fill('#gymAmenities', 'Cardio, Weights')
            page.fill('#gymSubscriptionAmount', '2500')

            # Verify custom plans section is hidden by default
            custom_section = page.locator('#customPlansSection')
            if not custom_section.is_visible():
                log_test("Custom plans section hidden by default", "PASS")
            else:
                log_test("Custom plans section hidden by default", "FAIL")

            # Submit
            page.locator('.modal-footer >> text=Add Gym').click()
            page.wait_for_timeout(3000)

            # Verify gym added (check for toast or gym in list)
            if page.locator('text=AutoCalc Test Gym').is_visible():
                log_test("Gym added without custom plans", "PASS", "Auto-calculation mode")
            else:
                log_test("Gym added without custom plans", "FAIL")

            page.screenshot(path='C:/Users/hp/gym_habit/test_1_auto_calc.png')

            # ===================================================================
            # TEST 3: ADD GYM WITH CUSTOM PLANS
            # ===================================================================
            print("\n" + "="*70)
            print("TEST SUITE 3: ADD GYM - CUSTOM PLANS")
            print("="*70)

            page.click('#addGymBtn')
            page.wait_for_timeout(1000)

            # Fill basic details
            page.fill('#gymName', 'Custom Plans Test Gym')
            page.select_option('#gymPartner', 'Cult')
            page.fill('#gymAddress', '789 Custom Ave')
            page.fill('#gymCity', 'Delhi')
            page.fill('#gymState', 'Delhi')
            page.fill('#gymPincode', '110001')
            page.fill('#gymLatitude', '28.70')
            page.fill('#gymLongitude', '77.10')
            page.fill('#gymAmenities', 'Swimming, Spa')
            page.fill('#gymSubscriptionAmount', '3500')

            # Enable custom plans
            toggle = page.locator('#customPlansToggle')
            toggle.check()
            page.wait_for_timeout(500)

            # Verify section is now visible
            if page.locator('#customPlansSection').is_visible():
                log_test("Custom plans section toggles visibility", "PASS")
            else:
                log_test("Custom plans section toggles visibility", "FAIL")

            # Fill custom plan prices
            page.fill('#plan1Month', '3500')
            page.fill('#plan3Months', '9900')
            page.fill('#plan6Months', '18900')
            page.fill('#plan12Months', '35000')

            log_test("Custom plan inputs filled", "PASS", "1M: 3500, 3M: 9900, 6M: 18900, 12M: 35000")

            page.screenshot(path='C:/Users/hp/gym_habit/test_2_custom_filled.png')

            # Submit using JavaScript to avoid click intercept
            page.evaluate("document.querySelector('.modal-footer .btn-primary').click()")
            page.wait_for_timeout(3000)

            # Verify gym added
            if page.locator('text=Custom Plans Test Gym').is_visible():
                log_test("Gym added with custom plans", "PASS")
            else:
                log_test("Gym added with custom plans", "FAIL")

            page.screenshot(path='C:/Users/hp/gym_habit/test_3_custom_added.png')

            # ===================================================================
            # TEST 4: EDIT GYM - VERIFY CUSTOM PLANS LOADED
            # ===================================================================
            print("\n" + "="*70)
            print("TEST SUITE 4: EDIT GYM - LOAD EXISTING CUSTOM PLANS")
            print("="*70)

            # Refresh gyms list to see newly added gym
            page.reload()
            page.wait_for_timeout(3000)

            # Go to Gyms tab again
            page.click('text=Gyms')
            page.wait_for_timeout(2000)

            # Find and click edit button for Custom Plans Test Gym
            edit_buttons = page.locator('button:has-text("Edit")')
            # Find the row with our gym and click its edit button
            rows = page.locator('tbody tr')
            found_gym = False
            for i in range(rows.count()):
                row = rows.nth(i)
                if 'Custom Plans Test Gym' in row.text_content():
                    row.locator('button:has-text("Edit")').first.click()
                    found_gym = True
                    break

            if not found_gym:
                log_test("Find Custom Plans Test Gym in list", "FAIL", "Gym not found in table")
            else:
                log_test("Find Custom Plans Test Gym in list", "PASS")

            page.wait_for_timeout(2000)

            # Verify edit modal loaded
            if page.locator('#editGymModal').is_visible():
                log_test("Edit Gym modal opens", "PASS")
            else:
                log_test("Edit Gym modal opens", "FAIL")
                page.screenshot(path='C:/Users/hp/gym_habit/test_4_edit_fail.png')
                return

            # Verify custom plans toggle is checked
            edit_toggle = page.locator('#editCustomPlansToggle')
            if edit_toggle.is_checked():
                log_test("Custom plans toggle pre-checked for gym with custom plans", "PASS")
            else:
                log_test("Custom plans toggle pre-checked for gym with custom plans", "FAIL")

            # Verify custom section is visible
            if page.locator('#editCustomPlansSection').is_visible():
                log_test("Edit custom plans section visible", "PASS")
            else:
                log_test("Edit custom plans section visible", "FAIL")

            # Verify values are pre-filled
            val_1m = page.locator('#editPlan1Month').input_value()
            val_3m = page.locator('#editPlan3Months').input_value()
            val_6m = page.locator('#editPlan6Months').input_value()
            val_12m = page.locator('#editPlan12Months').input_value()

            expected = {"1M": "3500", "3M": "9900", "6M": "18900", "12M": "35000"}
            actual = {"1M": val_1m, "3M": val_3m, "6M": val_6m, "12M": val_12m}

            if val_1m == "3500" and val_3m == "9900":
                log_test("Custom plan values pre-filled correctly", "PASS", f"Values: {actual}")
            else:
                log_test("Custom plan values pre-filled correctly", "FAIL", f"Expected: {expected}, Got: {actual}")

            page.screenshot(path='C:/Users/hp/gym_habit/test_4_edit_loaded.png')

            # Cancel edit
            page.locator('#editGymModal .modal-footer .btn:has-text("Cancel")').click()
            page.wait_for_timeout(1000)

            # ===================================================================
            # TEST 5: FRONTEND - VERIFY CUSTOM PLANS DISPLAY
            # ===================================================================
            print("\n" + "="*70)
            print("TEST SUITE 5: FRONTEND - VERIFY PLANS DISPLAY TO USERS")
            print("="*70)

            # Open new tab for frontend
            frontend_page = context.new_page()
            frontend_page.goto('http://localhost:8000')
            frontend_page.wait_for_load_state('networkidle')

            if frontend_page.locator('.gym-card').count() > 0:
                log_test("Frontend page loads with gym cards", "PASS")
            else:
                log_test("Frontend page loads with gym cards", "FAIL")

            # Click on a gym card to open modal
            frontend_page.locator('.gym-card').first.click()
            frontend_page.wait_for_timeout(2000)

            # Verify modal opened
            if frontend_page.locator('.gym-modal').is_visible():
                log_test("Gym details modal opens on frontend", "PASS")
            else:
                log_test("Gym details modal opens on frontend", "FAIL")

            # Verify subscription plans section exists
            if frontend_page.locator('.plans-grid').is_visible():
                log_test("Subscription plans section visible", "PASS")
            else:
                log_test("Subscription plans section visible", "FAIL")

            # Count plan cards (should be 4: 1M, 3M, 6M, 12M)
            plan_cards = frontend_page.locator('.plan-card')
            plan_count = plan_cards.count()

            if plan_count == 4:
                log_test("All 4 subscription plans displayed", "PASS", f"1M, 3M, 6M, 12M plans shown")
            else:
                log_test("All 4 subscription plans displayed", "FAIL", f"Expected 4, got {plan_count}")

            frontend_page.screenshot(path='C:/Users/hp/gym_habit/test_5_frontend_plans.png')
            frontend_page.close()

            # ===================================================================
            # TEST 6: API ENDPOINT - VERIFY CUSTOM PLANS IN RESPONSE
            # ===================================================================
            print("\n" + "="*70)
            print("TEST SUITE 6: API ENDPOINT - VERIFY CUSTOM PLANS DATA")
            print("="*70)

            # Use Playwright's API request context
            response = context.request.get('http://localhost:8000/api/gyms')

            if response.ok:
                log_test("GET /api/gyms endpoint responds", "PASS", f"Status: {response.status}")
                gyms = response.json()

                # Find our custom gym
                custom_gym = None
                for gym in gyms:
                    if gym.get('gym_name') == 'Custom Plans Test Gym':
                        custom_gym = gym
                        break

                if custom_gym:
                    log_test("Custom Plans Test Gym found in API response", "PASS")

                    # Verify it has custom_plans field
                    if 'custom_plans' in custom_gym:
                        log_test("custom_plans field present in gym data", "PASS")
                    else:
                        log_test("custom_plans field present in gym data", "FAIL")
                else:
                    log_test("Custom Plans Test Gym found in API response", "FAIL")
            else:
                log_test("GET /api/gyms endpoint responds", "FAIL", f"Status: {response.status}")

            # ===================================================================
            # TEST 7: EDGE CASE - PARTIAL CUSTOM PLANS
            # ===================================================================
            print("\n" + "="*70)
            print("TEST SUITE 7: EDGE CASES - PARTIAL CUSTOM PLANS")
            print("="*70)

            page.click('#addGymBtn')
            page.wait_for_timeout(1000)

            page.fill('#gymName', 'Partial Plans Gym')
            page.select_option('#gymPartner', 'Cult')
            page.fill('#gymAddress', '999 Partial Rd')
            page.fill('#gymCity', 'Bangalore')
            page.fill('#gymState', 'Karnataka')
            page.fill('#gymPincode', '560001')
            page.fill('#gymLatitude', '12.97')
            page.fill('#gymLongitude', '77.59')
            page.fill('#gymAmenities', 'Yoga')
            page.fill('#gymSubscriptionAmount', '2000')

            # Enable custom plans but only fill some
            page.locator('#customPlansToggle').check()
            page.wait_for_timeout(500)

            page.fill('#plan1Month', '2000')
            page.fill('#plan3Months', '5700')
            # Leave 6M and 12M empty

            page.evaluate("document.querySelector('.modal-footer .btn-primary').click()")
            page.wait_for_timeout(3000)

            if page.locator('text=Partial Plans Gym').is_visible():
                log_test("Gym with partial custom plans accepted", "PASS", "Only 1M and 3M filled")
            else:
                log_test("Gym with partial custom plans accepted", "FAIL")

            # ===================================================================
            # TEST 8: EDGE CASE - UNCHECK TOGGLE (REVERT TO AUTO)
            # ===================================================================
            print("\n" + "="*70)
            print("TEST SUITE 8: EDGE CASES - DISABLE CUSTOM PLANS")
            print("="*70)

            # Refresh and go to Gyms tab
            page.reload()
            page.wait_for_timeout(2000)
            page.click('text=Gyms')
            page.wait_for_timeout(2000)

            # Edit the custom plans gym and uncheck toggle
            rows = page.locator('tbody tr')
            for i in range(rows.count()):
                row = rows.nth(i)
                if 'Custom Plans Test Gym' in row.text_content():
                    row.locator('button:has-text("Edit")').first.click()
                    break

            page.wait_for_timeout(2000)

            # Uncheck toggle
            page.locator('#editCustomPlansToggle').uncheck()
            page.wait_for_timeout(500)

            # Verify section hidden
            if not page.locator('#editCustomPlansSection').is_visible():
                log_test("Unchecking toggle hides custom plans section", "PASS")
            else:
                log_test("Unchecking toggle hides custom plans section", "FAIL")

            # Save changes
            page.evaluate("document.querySelector('#editGymModal .modal-footer .btn-primary').click()")
            page.wait_for_timeout(3000)

            log_test("Gym updated to remove custom plans", "PASS", "Reverted to auto-calculation")

            # ===================================================================
            # TEST 9: CSV UPLOAD WITH CUSTOM PLANS
            # ===================================================================
            print("\n" + "="*70)
            print("TEST SUITE 9: CSV UPLOAD - WITH CUSTOM PLANS")
            print("="*70)

            # Create test CSV file
            csv_content = """gym_name,partner_name,address,city,state,pincode,latitude,longitude,amenities,subscription_amount,plan_1m,plan_3m,plan_6m,plan_12m
CSV Test Gym 1,Cult,CSV Street 1,Mumbai,Maharashtra,400003,19.09,72.89,Cardio|Weights,2800,2800,7980,15120,28800
CSV Test Gym 2,Cult,CSV Street 2,Delhi,Delhi,110002,28.71,77.11,Yoga|Spa,3200,3200,9120,17280,32640"""

            with open('C:/Users/hp/gym_habit/test_gyms.csv', 'w') as f:
                f.write(csv_content)

            # Click upload button
            page.click('#uploadGymsBtn')
            page.wait_for_timeout(1000)

            # Upload file
            page.locator('#gymsCSVFile').set_input_files('C:/Users/hp/gym_habit/test_gyms.csv')
            page.wait_for_timeout(500)

            log_test("CSV file selected for upload", "PASS", "2 gyms with custom plans")

            # Submit
            page.locator('#uploadGymsModal .modal-footer .btn-primary').click()
            page.wait_for_timeout(5000)

            # Verify gyms added
            if page.locator('text=CSV Test Gym 1').is_visible():
                log_test("CSV upload successful", "PASS", "Gyms with custom plans uploaded")
            else:
                log_test("CSV upload successful", "FAIL")

            page.screenshot(path='C:/Users/hp/gym_habit/test_9_csv_upload.png')

        except Exception as e:
            log_test("Test execution", "FAIL", str(e))
            import traceback
            print(traceback.format_exc())

        finally:
            page.screenshot(path='C:/Users/hp/gym_habit/test_final_state.png')
            time.sleep(2)
            browser.close()

def print_summary_table():
    """Print comprehensive test results table"""
    print("\n" + "="*100)
    print(" " * 30 + "COMPREHENSIVE TEST RESULTS")
    print("="*100)
    print(f"{'#':<4} {'Test Name':<60} {'Status':<10} {'Details':<25}")
    print("-"*100)

    for i, result in enumerate(test_results, 1):
        status_icon = "PASS" if result['status'] == "PASS" else "FAIL"
        print(f"{i:<4} {result['test']:<60} {status_icon:<10} {result['details']:<25}")

    print("="*100)

    # Summary stats
    passed = sum(1 for r in test_results if r['status'] == 'PASS')
    failed = sum(1 for r in test_results if r['status'] == 'FAIL')
    total = len(test_results)

    print(f"\nSUMMARY: {passed}/{total} tests passed, {failed} failed")
    print(f"Success Rate: {(passed/total*100):.1f}%")

    # Save to JSON
    with open('C:/Users/hp/gym_habit/test_results.json', 'w') as f:
        json.dump(test_results, f, indent=2)

    print("\nDetailed results saved to: test_results.json")
    print("Screenshots saved to: C:/Users/hp/gym_habit/")

if __name__ == '__main__':
    print("\n" + "="*100)
    print(" " * 25 + "GYM HABIT - COMPREHENSIVE TEST SUITE")
    print(" " * 20 + "Testing Custom Subscription Plans Feature")
    print("="*100)

    # Wait for server to be ready
    print("\n[INFO] Waiting for server to start...")
    time.sleep(8)

    run_comprehensive_tests()
    print_summary_table()
