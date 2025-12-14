# Gym Habit - Login Credentials

**Last Updated:** 2025-12-14
**Status:** ✅ Verified Working

---

## 🔐 **ADMIN PANEL LOGIN**

### Access URL
```
http://localhost:8000/admin
```

### Admin Credentials
```
Email:    admin@habithealth.com
Password: Admin@2025
```

**Role:** Admin (Full Access)
**Status:** ✅ Active and Verified

---

## 👥 **USER WEBSITE (No Login Required)**

### Access URL
```
http://localhost:8000/
```

**No credentials needed** - This is the public-facing website where users:
- Search for gyms
- Filter by partner
- Submit subscription requests

---

## ✅ **VERIFICATION TEST**

I just tested the login and it works perfectly:

```
✅ Status Code: 200 (Success)
✅ Token Type: bearer
✅ Access Token: Generated successfully
✅ User: Admin User
✅ Email: admin@habithealth.com
✅ Role: admin
```

---

## ⚠️ **WHY YOU GOT "INVALID CREDENTIALS" EARLIER**

The issue was that the **old server was running** without the new authentication endpoints.

### What Happened:
1. You tried to login → Old server didn't have `/api/auth/login` endpoint
2. Server returned "Not Found" or similar error
3. Frontend showed "Invalid credentials"

### Solution:
I've now **restarted the server** with the updated code. All endpoints are now working.

---

## 🔄 **HOW TO RESTART SERVER (If Needed)**

If you ever need to restart the server:

### Step 1: Stop the current server
```powershell
# Find Python process
tasklist | findstr python

# Stop it (replace 12345 with actual PID)
taskkill /F /PID 12345
```

### Step 2: Start the server
```powershell
cd C:\Users\hp\gym_habit
python main.py
```

The server will start on: `http://localhost:8000`

---

## 🌐 **ALL ACCESS POINTS**

| URL | Purpose | Login Required? | Credentials |
|-----|---------|-----------------|-------------|
| http://localhost:8000/ | User Website | ❌ No | None |
| http://localhost:8000/admin | Admin Panel | ✅ Yes | admin@habithealth.com / Admin@2025 |
| http://localhost:8000/docs | API Documentation | ❌ No | None |
| http://localhost:8000/health | System Health Check | ❌ No | None |

---

## 🛠️ **TESTING THE LOGIN**

### Method 1: Use the Browser
1. Open: http://localhost:8000/admin
2. **IMPORTANT:** Clear browser cache first (Ctrl + Shift + R)
3. Enter email: `admin@habithealth.com`
4. Enter password: `Admin@2025`
5. Click "Login"

### Method 2: Use API (curl)
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"admin@habithealth.com\",\"password\":\"Admin@2025\"}"
```

Expected Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "email": "admin@habithealth.com",
    "name": "Admin User",
    "role": "admin"
  }
}
```

---

## 👥 **CREATING ADDITIONAL USERS**

### From Admin Panel:
1. Login to admin panel
2. Go to "Users" tab (visible only to admin role)
3. Click "Create User"
4. Fill in details:
   - Name
   - Email
   - Password (min 8 characters)
   - Role: admin / facilitator / viewer
5. Click "Create"

### From Command Line:
```python
# Run this script to create a new user
cd C:\Users\hp\gym_habit
python -c "
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from auth import hash_password
import config
from datetime import datetime

async def create_user():
    client = AsyncIOMotorClient(config.MONGODB_URL)
    db = client[config.MONGODB_DB_NAME]

    user = {
        'email': 'facilitator@habithealth.com',  # Change this
        'password_hash': hash_password('Facilitator@2025'),  # Change this
        'name': 'Facilitator User',  # Change this
        'role': 'facilitator',  # admin / facilitator / viewer
        'is_active': True,
        'created_at': datetime.utcnow()
    }

    result = await db.users.insert_one(user)
    print(f'User created: {user[\"email\"]}')
    client.close()

asyncio.run(create_user())
"
```

---

## 🔑 **ROLES AND PERMISSIONS**

### Admin Role
✅ Full access to everything
✅ View/manage all leads
✅ Update lead status, payment, plans
✅ Add comments
✅ Export CSV
✅ Create/manage users
✅ View audit trails

### Facilitator Role
✅ View/manage all leads
✅ Update lead status, payment, plans
✅ Add comments
✅ Export CSV
✅ View audit trails
❌ Cannot create/manage users

### Viewer Role
✅ View leads (read-only)
✅ Export CSV
❌ Cannot update leads
❌ Cannot add comments
❌ Cannot create/manage users

---

## 🔒 **SECURITY NOTES**

1. **Change Default Password:**
   - Login to admin panel
   - Go to Profile/Settings
   - Change password from `Admin@2025` to something secure

2. **Password Requirements:**
   - Minimum 8 characters
   - Mix of letters, numbers, and symbols recommended

3. **Token Expiration:**
   - JWT tokens expire after 24 hours
   - You'll need to login again after expiration

4. **Password Storage:**
   - All passwords are hashed using bcrypt
   - Never stored in plain text

---

## ❓ **TROUBLESHOOTING**

### Issue: "Invalid Credentials" Error

**Possible Causes:**
1. ❌ Old server running → Restart server
2. ❌ Browser cache showing old admin page → Clear cache (Ctrl + Shift + R)
3. ❌ Typo in email/password → Copy-paste from this document
4. ❌ Wrong endpoint → Make sure you're at `/admin` not `/`

**Solution:**
1. Restart the server: `python main.py`
2. Clear browser cache: Ctrl + Shift + R
3. Try again with exact credentials: `admin@habithealth.com` / `Admin@2025`

### Issue: Login Page Not Loading

**Solution:**
- Server might not be running
- Start server: `cd C:\Users\hp\gym_habit && python main.py`
- Wait 5 seconds for server to start
- Visit: http://localhost:8000/admin

### Issue: Old Admin Page Showing

**Solution:**
- This is a browser cache issue
- Hard refresh: Ctrl + Shift + R (or Ctrl + F5)
- Or clear browser cache completely

---

## 📝 **QUICK REFERENCE**

**Start Server:**
```bash
cd C:\Users\hp\gym_habit
python main.py
```

**Admin Login:**
- URL: http://localhost:8000/admin
- Email: admin@habithealth.com
- Password: Admin@2025

**Clear Browser Cache:**
- Windows: Ctrl + Shift + R or Ctrl + F5

**Test Login API:**
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"admin@habithealth.com\",\"password\":\"Admin@2025\"}"
```

---

## ✅ **STATUS: VERIFIED WORKING**

✅ Server running on port 8000
✅ Admin user exists in database
✅ Login endpoint working (tested)
✅ JWT token generation successful
✅ All authentication features operational

**You can now login to the admin panel!**

---

**Generated:** 2025-12-14
**Repository:** https://github.com/nikhil13dubey-star/Gym_Habit
