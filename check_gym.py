import asyncio
from mongo_database import MongoGymDatabase

async def check_gym():
    db = MongoGymDatabase()
    await db.initialize()

    # Get latest gym from MongoDB directly
    gym_doc = await db.db.gyms.find_one({"gym_id": 37})
    print("Gym 37 from MongoDB:")
    if gym_doc:
        print(f"  gym_name: {gym_doc.get('gym_name')}")
        print(f"  custom_plans: {gym_doc.get('custom_plans')}")
        print(f"  All fields: {list(gym_doc.keys())}")
    else:
        print("  Not found")

    # Get via API method
    gym_api = await db.get_gym_by_id(37)
    print("\nGym 37 via get_gym_by_id:")
    if gym_api:
        print(f"  gym_name: {gym_api.get('gym_name')}")
        print(f"  custom_plans: {gym_api.get('custom_plans')}")
        print(f"  All fields: {list(gym_api.keys())}")
    else:
        print("  Not found")

    # Get via get_all_gyms
    all_gyms = await db.get_all_gyms()
    gym_37_from_all = [g for g in all_gyms if g.get('id') == 37]
    print("\nGym 37 via get_all_gyms:")
    if gym_37_from_all:
        gym = gym_37_from_all[0]
        print(f"  gym_name: {gym.get('gym_name')}")
        print(f"  custom_plans: {gym.get('custom_plans')}")
        print(f"  All fields: {list(gym.keys())}")
    else:
        print("  Not found in get_all_gyms()")

asyncio.run(check_gym())
