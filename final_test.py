"""
FINAL COMPREHENSIVE TEST - GYM HABIT CUSTOM PLANS
Tests all functionality end-to-end
"""
from playwright.sync_api import sync_playwright
import time
import json

results = []

def test(name, passed, details=""):
    results.append({"test": name, "status": "PASS" if passed else "FAIL", "details": details})
    print(f"{'[PASS]' if passed else '[FAIL]'} {name}")
    if details:
        print(f"       {details}")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=200)
        page = browser.new_page()

        try:
            print("\n" + "="*80)
            print(" "*20 + "GYM HABIT - FINAL COMPREHENSIVE TEST")
            print("="*80 + "\n")

            # TEST 1: Login
            page.goto('http://localhost:8000/admin')
            page.wait_for_load_state('networkidle')
            page.fill('#loginEmail', 'admin@habithealth.com')
            page.fill('#loginPassword', 'Admin@2025')
            page.click('button:has-text("Sign In")')
            page.wait_for_timeout(4000)

            logged_in = page.locator('.sidebar').is_visible() or page.locator('text=Dashboard').is_visible()
            test("1. Admin Login", logged_in)
            page.screenshot(path='C:/Users/hp/gym_habit/final_1_login.png')

            if not logged_in:
                return

            # TEST 2: Navigate to Gyms
            page.click('text=Gyms')
            page.wait_for_timeout(2000)
            gyms_tab_active = page.locator('#tabGyms').is_visible()
            test("2. Navigate to Gyms Tab", gyms_tab_active)

            # TEST 3: Add Gym Modal Opens
            page.click('#addGymBtn')
            page.wait_for_timeout(1000)
            modal_visible = page.locator('#addGymModal').is_visible()
            test("3. Add Gym Modal Opens", modal_visible)
            page.screenshot(path='C:/Users/hp/gym_habit/final_2_modal.png')

            # TEST 4: Custom Plans Toggle Exists
            toggle_exists = page.locator('#customPlansToggle').is_visible()
            test("4. Custom Plans Toggle Exists", toggle_exists)

            # TEST 5: Custom Plans Section Initially Hidden
            section_hidden = not page.locator('#customPlansSection').is_visible()
            test("5. Custom Plans Section Hidden by Default", section_hidden)

            # TEST 6: Toggle Shows Custom Plans Section
            page.check('#customPlansToggle')
            page.wait_for_timeout(500)
            section_visible = page.locator('#customPlansSection').is_visible()
            test("6. Toggle Shows Custom Plans Section", section_visible)
            page.screenshot(path='C:/Users/hp/gym_habit/final_3_toggle.png')

            # TEST 7: All 4 Plan Input Fields Exist
            has_1m = page.locator('#plan1Month').is_visible()
            has_3m = page.locator('#plan3Months').is_visible()
            has_6m = page.locator('#plan6Months').is_visible()
            has_12m = page.locator('#plan12Months').is_visible()
            all_fields = has_1m and has_3m and has_6m and has_12m
            test("7. All 4 Custom Plan Input Fields Present", all_fields, "1M, 3M, 6M, 12M")

            # TEST 8: Fill and Submit Gym with Custom Plans
            # Wait for form fields to be ready
            page.wait_for_selector('#gymName', state='visible', timeout=5000)
            page.fill('#gymName', 'Final Test Custom Gym')
            page.select_option('#gymPartner', 'Cult')
            page.fill('#gymAddress', '999 Final Test St')
            page.fill('#gymCity', 'Mumbai')
            page.fill('#gymState', 'Maharashtra')
            page.fill('#gymPincode', '400099')
            page.fill('#gymLatitude', '19.10')
            page.fill('#gymLongitude', '72.90')
            page.fill('#gymAmenities', 'Test, Gym')
            page.fill('#gymSubscriptionAmount', '5000')
            page.fill('#plan1Month', '5000')
            page.fill('#plan3Months', '14000')
            page.fill('#plan6Months', '26000')
            page.fill('#plan12Months', '50000')

            page.screenshot(path='C:/Users/hp/gym_habit/final_4_filled.png')

            # Submit via JavaScript
            page.evaluate("document.querySelector('#addGymModal .modal-footer .btn-primary').click()")
            page.wait_for_timeout(4000)

            # Check if gym was added
            page.reload()
            page.wait_for_timeout(2000)
            page.click('text=Gyms')
            page.wait_for_timeout(2000)

            gym_added = page.locator('text=Final Test Custom Gym').first.is_visible()
            test("8. Gym with Custom Plans Added Successfully", gym_added)
            page.screenshot(path='C:/Users/hp/gym_habit/final_5_added.png')

            # TEST 9: API - Verify Custom Plans in Response
            response = page.request.get('http://localhost:8000/api/gyms')
            api_works = response.ok
            test("9. API /api/gyms Responds", api_works, f"Status: {response.status}")

            # API returns {"gyms": [...], "total": ...}
            response_data = response.json() if api_works else {}
            gyms = response_data.get('gyms', []) if isinstance(response_data, dict) else []

            custom_gym = next((g for g in gyms if g.get('gym_name') == 'Final Test Custom Gym'), None)

            if custom_gym:
                has_custom_plans = 'custom_plans' in custom_gym
                test("10. Gym Has custom_plans Field in API", has_custom_plans)

                if has_custom_plans:
                    cp = custom_gym['custom_plans']
                    correct_values = (
                        cp.get('1_month') == 5000 and
                        cp.get('3_months') == 14000 and
                        cp.get('6_months') == 26000 and
                        cp.get('12_months') == 50000
                    )
                    test("11. Custom Plan Values Correct in API", correct_values,
                         f"1M:{cp.get('1_month')}, 3M:{cp.get('3_months')}, 6M:{cp.get('6_months')}, 12M:{cp.get('12_months')}")
                else:
                    test("11. Custom Plan Values Correct in API", False, "custom_plans field missing")
            else:
                test("10. Gym Has custom_plans Field in API", False, "Gym not found in API response")
                test("11. Custom Plan Values Correct in API", False, "Gym not found")

            # TEST 12: Frontend - Open Gym Modal
            frontend = browser.new_page()
            frontend.goto('http://localhost:8000')
            frontend.wait_for_load_state('networkidle')

            has_gyms = frontend.locator('.gym-card').count() > 0
            test("12. Frontend Loads with Gym Cards", has_gyms)

            if has_gyms:
                frontend.locator('.gym-card').first.click()
                frontend.wait_for_timeout(2000)

                modal_open = frontend.locator('.modal-body').is_visible()
                test("13. Gym Modal Opens on Frontend", modal_open)

                has_plans = frontend.locator('.plans-grid').is_visible()
                test("14. Subscription Plans Section Visible", has_plans)

                plan_count = frontend.locator('.plan-card').count()
                test("15. All 4 Plan Cards Displayed", plan_count == 4, f"Count: {plan_count}")

                frontend.screenshot(path='C:/Users/hp/gym_habit/final_6_frontend.png')

            frontend.close()

            # TEST 16: Edit Modal - Load Existing Custom Plans
            found = False
            rows = page.locator('tbody tr')
            for i in range(rows.count()):
                row = rows.nth(i)
                if 'Final Test Custom Gym' in row.text_content():
                    # Use JavaScript to click to avoid interception
                    page.evaluate(f"""
                        const rows = document.querySelectorAll('tbody tr');
                        const targetRow = Array.from(rows).find(r => r.textContent.includes('Final Test Custom Gym'));
                        if (targetRow) {{
                            const editBtn = targetRow.querySelector('button.btn-edit, button[onclick*="editGym"]');
                            if (editBtn) editBtn.click();
                        }}
                    """)
                    found = True
                    break

            test("16. Find and Click Edit on Custom Gym", found)

            if found:
                page.wait_for_timeout(3000)
                edit_modal_open = page.locator('#editGymModal').is_visible()
                test("17. Edit Modal Opens", edit_modal_open)

                if edit_modal_open:
                    toggle_checked = page.locator('#editCustomPlansToggle').is_checked()
                    test("18. Edit Modal - Custom Plans Toggle Pre-checked", toggle_checked)

                    section_visible = page.locator('#editCustomPlansSection').is_visible()
                    test("19. Edit Modal - Custom Plans Section Visible", section_visible)

                    val_1m = page.locator('#editPlan1Month').input_value()
                    val_3m = page.locator('#editPlan3Months').input_value()

                    values_correct = val_1m == "5000" and val_3m == "14000"
                    test("20. Edit Modal - Values Pre-filled Correctly", values_correct,
                         f"1M:{val_1m}, 3M:{val_3m}")

                    page.screenshot(path='C:/Users/hp/gym_habit/final_7_edit.png')

                    # Close modal
                    page.locator('#editGymModal .close-btn').click()
                    page.wait_for_timeout(1000)

            # TEST 21: CSV Upload Format Updated
            page.click('#uploadGymsBtn')
            page.wait_for_timeout(1000)

            csv_modal = page.locator('#uploadGymsModal').is_visible()
            test("21. CSV Upload Modal Opens", csv_modal)

            if csv_modal:
                has_plan_columns = 'plan_1m' in page.locator('#uploadGymsModal').text_content()
                test("22. CSV Format Includes Custom Plan Columns", has_plan_columns, "plan_1m, plan_3m, plan_6m, plan_12m")

                page.screenshot(path='C:/Users/hp/gym_habit/final_8_csv.png')

            time.sleep(2)

        except Exception as e:
            test("TEST EXECUTION", False, str(e)[:100])
            import traceback
            print(traceback.format_exc())

        finally:
            page.screenshot(path='C:/Users/hp/gym_habit/final_9_complete.png')
            browser.close()

def print_table():
    print("\n" + "="*100)
    print(" "*30 + "FINAL TEST RESULTS SUMMARY")
    print("="*100)
    print(f"{'#':<5} {'Test Name':<55} {'Status':<10} {'Details':<30}")
    print("-"*100)

    for i, r in enumerate(results, 1):
        status = "PASS" if r['status'] == 'PASS' else "FAIL"
        details = r['details'][:27] + "..." if len(r['details']) > 30 else r['details']
        print(f"{i:<5} {r['test']:<55} {status:<10} {details:<30}")

    print("="*100)

    passed = sum(1 for r in results if r['status'] == 'PASS')
    failed = sum(1 for r in results if r['status'] == 'FAIL')
    total = len(results)

    print(f"\nTOTAL TESTS: {total}")
    print(f"PASSED: {passed}")
    print(f"FAILED: {failed}")
    print(f"SUCCESS RATE: {(passed/total*100):.1f}%\n")

    # Save JSON
    with open('C:/Users/hp/gym_habit/final_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print("Detailed results: final_results.json")
    print("Screenshots: final_*.png")
    print("="*100)

if __name__ == '__main__':
    print("\nWaiting for server...")
    time.sleep(5)
    main()
    print_table()
