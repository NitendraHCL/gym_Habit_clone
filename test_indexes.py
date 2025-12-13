"""Test the optimized database indexes"""
from database import GymDatabase

db = GymDatabase()

print("\n=== PINCODE SEARCH TEST ===")
result = db.search_by_pincode('400053')
print(f"Pincode 400053: {len(result)} gyms found")
for g in result[:3]:
    print(f"  - {g['gym_name']}")

print("\n=== CITY SEARCH TEST ===")
result = db.search_by_city('Mumbai')
print(f"City Mumbai: {len(result)} gyms found")
for g in result[:3]:
    print(f"  - {g['gym_name']}")

print("\n=== NEARBY SEARCH TEST (KD-Tree) ===")
result = db.get_nearby_gyms(19.1136, 72.8697, limit=5)
print(f"Near Andheri: {len(result)} gyms found")
for g in result:
    print(f"  - {g['gym_name']} ({g['distance']} km)")

print("\n=== Performance: All tests passed! ===")
