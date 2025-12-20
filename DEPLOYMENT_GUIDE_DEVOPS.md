# Gym Habit - DevOps Deployment Guide
**Habit Health by HCL Healthcare**

## Project Overview
Gym Habit is a gym membership lead generation platform that helps users find partner gyms near their location and submit subscription requests. The platform includes a public-facing frontend and an admin panel for managing leads.

---

## Tech Stack Summary

### Backend
- **Framework**: FastAPI 0.100+
- **Runtime**: Python 3.10+
- **ASGI Server**: Uvicorn
- **Database**: MongoDB (Motor async driver)
- **Authentication**: JWT (PyJWT)
- **Password Hashing**: Bcrypt (Passlib)
- **API Documentation**: Auto-generated Swagger/OpenAPI

### Frontend
- **Type**: Vanilla JavaScript (no framework - no npm/node required)
- **Files**: Static HTML/CSS/JS served by FastAPI
- **Location**: `/frontend` directory

### External Services
- **Google Geocoding API**: For location-to-coordinates conversion (requires API key)

### Key Python Dependencies
```txt
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
motor>=3.3.0              # Async MongoDB driver
pymongo>=4.5.0
pydantic>=2.0.0
pydantic[email]
python-jose[cryptography]  # JWT tokens
passlib[bcrypt]           # Password hashing
python-dotenv             # Environment variables
requests                  # HTTP client for Google API
```

---

## ⚠️ CRITICAL: S3 is NOT Sufficient for This Application

**Amazon S3** can only host static files (HTML/CSS/JS). This project requires:
- **Backend runtime**: Python/FastAPI server
- **Database**: MongoDB instance
- **Compute**: EC2, ECS, or Lambda

You **cannot** deploy this on S3 alone.

---

## AWS Deployment Architecture Options

### Option 1: EC2 + MongoDB Atlas (Recommended for Simplicity)

```
┌──────────────────┐
│   Route 53       │ (Optional DNS)
│   (DNS)          │
└────────┬─────────┘
         │
┌────────▼─────────┐
│  CloudFront      │ (Optional CDN)
└────────┬─────────┘
         │
┌────────▼─────────┐
│  Application     │
│  Load Balancer   │ (ALB - for HTTPS/SSL)
└────────┬─────────┘
         │
┌────────▼─────────┐
│  EC2 Instance    │ (t3.small or t3.medium)
│  - Ubuntu 22.04  │
│  - Python 3.10   │
│  - FastAPI       │
│  - Uvicorn       │
└────────┬─────────┘
         │
┌────────▼─────────┐
│  MongoDB Atlas   │ (External SaaS - free tier M0 available)
│  (Cloud Database)│
└──────────────────┘
```

**Pros:**
- Simplest setup
- MongoDB Atlas has free tier (M0 - 512MB storage)
- Easy to scale
- Automatic backups (Atlas)

**Cons:**
- Database hosted outside AWS (but fast peering available)

**Monthly Cost:**
- EC2 t3.small: ~$15
- MongoDB Atlas M0: $0 (free tier) or M10: ~$60
- ALB: ~$20
- **Total: ~$35/month (with free MongoDB) or ~$95/month (paid MongoDB)**

---

### Option 2: ECS Fargate + DocumentDB (Production-Grade)

```
┌──────────────────┐
│   Route 53       │
└────────┬─────────┘
         │
┌────────▼─────────┐
│  Application     │
│  Load Balancer   │ (ALB)
└────────┬─────────┘
         │
┌────────▼─────────┐
│  ECS Fargate     │ (Serverless containers)
│  - Docker Image  │
│  - Auto-scaling  │
└────────┬─────────┘
         │
         ├──────────────────┐
         │                  │
┌────────▼─────────┐ ┌─────▼────────┐
│  DocumentDB      │ │  Secrets     │
│  (AWS MongoDB)   │ │  Manager     │
└──────────────────┘ └──────────────┘
```

**Pros:**
- Fully serverless (no server management)
- Auto-scaling
- AWS-native (all within VPC)
- High availability

**Cons:**
- More complex setup
- Higher cost
- DocumentDB minimum cost ~$200/month

**Monthly Cost:**
- ECS Fargate (0.25 vCPU, 0.5GB): ~$10
- DocumentDB (db.t3.medium): ~$200
- ALB: ~$20
- **Total: ~$230/month**

---

### Option 3: Lambda + API Gateway (Cost-Optimized)

```
┌──────────────────┐
│   Route 53       │
└────────┬─────────┘
         │
┌────────▼─────────┐
│  API Gateway     │ (REST API)
└────────┬─────────┘
         │
┌────────▼─────────┐
│  Lambda Function │ (Python 3.10)
│  - Mangum adapter│ (FastAPI → Lambda)
│  - Cold starts   │
└────────┬─────────┘
         │
┌────────▼─────────┐
│  MongoDB Atlas   │ (External)
└──────────────────┘
```

**Pros:**
- Pay-per-request (very low cost for low traffic)
- Auto-scaling
- No server management

**Cons:**
- Cold starts (500ms-2s delay)
- 15-minute timeout limit
- Requires Mangum adapter for FastAPI

**Monthly Cost:**
- Lambda: ~$5 (1M requests)
- API Gateway: ~$3.50
- MongoDB Atlas M0: $0
- **Total: ~$10/month (low traffic)**

---

## **Recommended: Option 1 (EC2 + MongoDB Atlas)**

For your organization, I recommend **Option 1** because:
1. Simple deployment and debugging
2. Free MongoDB tier available
3. Easy for DevOps team to manage
4. Can upgrade to Option 2 later

---

## MongoDB Database Structure

### Database Name: `gym_habit`

### Collections (4):

#### 1. `gyms` Collection
Stores gym/partner location data.

**Sample Document:**
```javascript
{
  "_id": ObjectId("..."),
  "gym_id": 1,              // Auto-increment integer
  "gym_name": "Cult Andheri West",
  "partner_name": "Cult",
  "address": "Plot 123, Andheri West, Mumbai",
  "city": "Mumbai",
  "state": "Maharashtra",
  "pincode": "400053",
  "latitude": 19.1136,
  "longitude": 72.8697,
  "location": {             // GeoJSON for geospatial queries
    "type": "Point",
    "coordinates": [72.8697, 19.1136]  // [longitude, latitude]
  },
  "amenities": ["AC", "Parking", "Showers", "Lockers"],
  "subscription_amount": 1499,  // Base monthly price
  "custom_plans": {         // Optional custom pricing
    "1_month": 1499,
    "3_months": 4200,
    "6_months": 7900,
    "12_months": 14900
  },
  "icon": "🏋️",             // Emoji or base64 image
  "is_active": true,        // Soft delete flag
  "created_at": ISODate("2024-01-01T00:00:00Z"),
  "updated_at": ISODate("2024-01-15T10:30:00Z")
}
```

**Required Indexes:**
```javascript
db.gyms.createIndex({ "location": "2dsphere" });  // For nearby searches
db.gyms.createIndex({ "gym_id": 1 }, { unique: true });
db.gyms.createIndex({ "pincode": 1 });
db.gyms.createIndex({ "city": 1 });
db.gyms.createIndex({ "is_active": 1 });
```

---

#### 2. `leads` Collection
Stores user subscription requests/leads.

**Sample Document:**
```javascript
{
  "_id": ObjectId("..."),
  "lead_id": "GYM_20251220_0001",  // Format: GYM_YYYYMMDD_XXXX
  "created_at": ISODate("2024-12-20T10:30:00Z"),
  "updated_at": ISODate("2024-12-20T12:00:00Z"),

  // Gym Info
  "gym_id": 1,
  "gym_name": "Cult Andheri West",
  "partner_name": "Cult",

  // User Info
  "full_name": "John Doe",
  "email": "john@example.com",
  "phone": "9876543210",
  "billing_address": "Mumbai, Maharashtra",
  "message": "Interested in evening batch",

  // User Location (where they searched from)
  "user_location": {
    "latitude": 19.1136,
    "longitude": 72.8697,
    "city": "Mumbai"
  },

  // Lead Tracking
  "status": "new",  // new | contacted | interested | not_interested | closed
  "preferred_plan": "3-month",

  // Assignment
  "assigned_to": "admin@habithealth.com",
  "assigned_to_name": "Admin User",
  "assigned_at": ISODate("2024-12-20T11:00:00Z"),

  // Payment Tracking
  "payment": {
    "status": "pending",  // pending | link_shared | paid | failed
    "amount": 4200,
    "payment_link": "https://razorpay.me/...",
    "updated_at": ISODate("2024-12-20T12:00:00Z")
  },

  // Comments/Notes
  "comments": [
    {
      "timestamp": ISODate("2024-12-20T11:30:00Z"),
      "user": "admin@habithealth.com",
      "text": "Called customer, interested in 3-month plan"
    }
  ],

  // Full Audit Trail
  "audit_log": [
    {
      "timestamp": ISODate("2024-12-20T11:00:00Z"),
      "action": "status_change",
      "user": "admin@habithealth.com",
      "old_value": "new",
      "new_value": "contacted",
      "reason": "First contact made"
    },
    {
      "timestamp": ISODate("2024-12-20T12:00:00Z"),
      "action": "payment_update",
      "user": "admin@habithealth.com",
      "old_status": "pending",
      "new_status": "link_shared",
      "amount": 4200,
      "payment_link": "https://..."
    }
  ]
}
```

**Required Indexes:**
```javascript
db.leads.createIndex({ "lead_id": 1 }, { unique: true });
db.leads.createIndex({ "created_at": -1 });  // For sorting by date
db.leads.createIndex({ "status": 1 });       // For filtering
db.leads.createIndex({ "payment.status": 1 });
```

---

#### 3. `partners` Collection
Stores partner metadata (optional, for additional info).

**Sample Document:**
```javascript
{
  "_id": ObjectId("..."),
  "name": "Cult",
  "description": "India's largest fitness chain with 100+ centers",
  "icon": "🏋️",
  "created_at": ISODate("2024-01-01T00:00:00Z"),
  "updated_at": ISODate("2024-01-01T00:00:00Z")
}
```

**Required Indexes:**
```javascript
db.partners.createIndex({ "name": 1 }, { unique: true });
```

---

#### 4. `users` Collection
Stores admin/facilitator accounts.

**Sample Document:**
```javascript
{
  "_id": ObjectId("..."),
  "email": "admin@habithealth.com",
  "name": "Admin User",
  "password_hash": "$2b$12$abcdef...",  // Bcrypt hash
  "role": "admin",  // admin | facilitator | viewer
  "is_active": true,
  "created_at": ISODate("2024-01-01T00:00:00Z"),
  "created_by": "system",
  "last_login": ISODate("2024-12-20T10:00:00Z"),
  "login_count": 45,
  "updated_at": ISODate("2024-12-20T10:00:00Z"),
  "password_updated_at": ISODate("2024-11-01T00:00:00Z")
}
```

**Required Indexes:**
```javascript
db.users.createIndex({ "email": 1 }, { unique: true });
db.users.createIndex({ "is_active": 1 });
```

---

## Environment Variables Required

Create a `.env` file (or use AWS Secrets Manager/Parameter Store):

```bash
# ===== MongoDB Configuration =====
MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
# OR for DocumentDB:
# MONGODB_URL=mongodb://username:password@docdb-cluster.region.docdb.amazonaws.com:27017/?tls=true&tlsCAFile=rds-combined-ca-bundle.pem

# ===== JWT Secret (Generate a secure random string) =====
JWT_SECRET_KEY=your-super-secret-jwt-key-min-32-characters-long-random-string-here

# ===== Google Geocoding API Key =====
GOOGLE_GEOCODING_API_KEY=AIzaSy...

# ===== Environment =====
ENVIRONMENT=production

# ===== Default Admin (for first-time setup only) =====
DEFAULT_ADMIN_EMAIL=admin@habithealth.com
DEFAULT_ADMIN_PASSWORD=Admin@2025
DEFAULT_ADMIN_NAME=Admin User
```

### ⚠️ Security Notes:
1. **JWT_SECRET_KEY**: Generate using: `openssl rand -hex 32`
2. **Never commit `.env` to Git** (already in `.gitignore`)
3. Use **AWS Secrets Manager** in production
4. Change `DEFAULT_ADMIN_PASSWORD` immediately after first login

---

## MongoDB Setup Instructions

### Option A: MongoDB Atlas (Recommended)

1. **Create Account**
   - Go to https://cloud.mongodb.com
   - Sign up for free account

2. **Create Cluster**
   - Click "Build a Database"
   - Choose **M0 Free** tier (512MB storage, free forever)
   - Select AWS as cloud provider
   - Choose region closest to your EC2 (e.g., `us-east-1`)
   - Cluster name: `gym-habit-cluster`

3. **Create Database User**
   - Go to "Database Access"
   - Add new user
   - Username: `gym_habit_user`
   - Password: Generate strong password
   - Role: "Atlas admin" or "Read and write to any database"

4. **Network Access**
   - Go to "Network Access"
   - Click "Add IP Address"
   - For development: Click "Allow Access from Anywhere" (0.0.0.0/0)
   - For production: Add EC2 instance IP or use VPC peering

5. **Get Connection String**
   - Go to "Database" → "Connect"
   - Choose "Connect your application"
   - Driver: Python, Version: 3.12 or later
   - Copy connection string:
     ```
     mongodb+srv://gym_habit_user:<password>@gym-habit-cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority
     ```
   - Replace `<password>` with actual password
   - Add to `.env` as `MONGODB_URL`

6. **Create Database and Collections**
   - Database will be created automatically on first app run
   - Collections will be created automatically
   - **BUT indexes must be created manually** (see below)

7. **Create Indexes** (IMPORTANT!)
   ```javascript
   // Connect via MongoDB Compass or Atlas UI
   use gym_habit;

   // Gyms indexes
   db.gyms.createIndex({ "location": "2dsphere" });
   db.gyms.createIndex({ "gym_id": 1 }, { unique: true });
   db.gyms.createIndex({ "pincode": 1 });
   db.gyms.createIndex({ "city": 1 });
   db.gyms.createIndex({ "is_active": 1 });

   // Leads indexes
   db.leads.createIndex({ "lead_id": 1 }, { unique: true });
   db.leads.createIndex({ "created_at": -1 });
   db.leads.createIndex({ "status": 1 });
   db.leads.createIndex({ "payment.status": 1 });

   // Partners indexes
   db.partners.createIndex({ "name": 1 }, { unique: true });

   // Users indexes
   db.users.createIndex({ "email": 1 }, { unique: true });
   db.users.createIndex({ "is_active": 1 });
   ```

---

### Option B: AWS DocumentDB

1. **Create DocumentDB Cluster**
   - Console: RDS → Amazon DocumentDB
   - Instance class: db.t3.medium (minimum)
   - Number of instances: 1 (or 3 for HA)
   - VPC: Same as EC2
   - Security group: Allow 27017 from EC2 security group

2. **Download TLS Certificate**
   ```bash
   wget https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem
   ```

3. **Connection String**
   ```
   mongodb://username:password@docdb-cluster.region.docdb.amazonaws.com:27017/?tls=true&tlsCAFile=global-bundle.pem&replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false
   ```

4. **Create Indexes** (same as Atlas above)

**Cost: ~$200/month minimum (db.t3.medium)**

---

## EC2 Deployment Steps

### 1. Launch EC2 Instance

**Instance Details:**
- **AMI**: Ubuntu Server 22.04 LTS
- **Instance Type**: t3.small (2GB RAM) or t3.medium (4GB RAM)
- **Storage**: 20GB gp3
- **Security Group**:
  - Port 22 (SSH): Your IP only
  - Port 80 (HTTP): 0.0.0.0/0
  - Port 443 (HTTPS): 0.0.0.0/0
  - Port 8000 (FastAPI): 0.0.0.0/0 (only if testing without ALB)

### 2. Connect to EC2

```bash
ssh -i keypair.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

### 3. Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.10
sudo apt install python3.10 python3.10-venv python3-pip -y

# Install Git
sudo apt install git -y

# Install Nginx (optional, for reverse proxy)
sudo apt install nginx -y
```

### 4. Clone Repository from GitLab

```bash
cd /home/ubuntu

# Clone from GitLab
git clone https://gitlab.com/YOUR_ORG/gym-habit.git
cd gym-habit
```

### 5. Setup Python Environment

```bash
# Create virtual environment
python3.10 -m venv venv

# Activate
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### 6. Configure Environment Variables

```bash
# Create .env file
nano .env
```

Paste environment variables (see section above), then save (Ctrl+X, Y, Enter).

### 7. Create Default Admin User

The app will automatically create the default admin user on first startup using the credentials from `.env`:
- Email: `admin@habithealth.com`
- Password: `Admin@2025` (from `.env`)

**⚠️ IMPORTANT: Change this password immediately after first login via the admin panel!**

### 8. Test Application

```bash
# Run FastAPI (foreground test)
python main.py
```

You should see:
```
============================================================
GYM HABIT - Habit Health Partner Gym Finder (MongoDB)
============================================================
[OK] MongoDB connection initialized
```

Test in browser: `http://YOUR_EC2_IP:8000`

Press Ctrl+C to stop.

### 9. Create Systemd Service (Run 24/7)

```bash
sudo nano /etc/systemd/system/gym-habit.service
```

Paste:
```ini
[Unit]
Description=Gym Habit FastAPI Application
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/gym-habit
Environment="PATH=/home/ubuntu/gym-habit/venv/bin"
EnvironmentFile=/home/ubuntu/gym-habit/.env
ExecStart=/home/ubuntu/gym-habit/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable gym-habit
sudo systemctl start gym-habit
sudo systemctl status gym-habit
```

### 10. Configure Nginx (Optional but Recommended)

```bash
sudo nano /etc/nginx/sites-available/gym-habit
```

Paste:
```nginx
server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }
}
```

Enable:
```bash
sudo ln -s /etc/nginx/sites-available/gym-habit /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Application Health Check

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "database": "mongodb",
  "gyms_loaded": 150,
  "partners": 5
}
```

Use for ALB health checks or monitoring.

---

## Application URLs

After deployment:

- **Main App**: `http://YOUR_DOMAIN/`
- **Admin Panel**: `http://YOUR_DOMAIN/admin`
- **API Docs**: `http://YOUR_DOMAIN/docs` (Swagger UI)
- **Health Check**: `http://YOUR_DOMAIN/health`

---

## Default Admin Login

**First Login:**
- URL: `http://YOUR_DOMAIN/admin`
- Email: `admin@habithealth.com`
- Password: `Admin@2025` (from `.env`)

**⚠️ IMMEDIATELY CHANGE PASSWORD AFTER FIRST LOGIN**

---

## Monitoring & Logging

### Application Logs

```bash
# View live logs
sudo journalctl -u gym-habit -f

# View last 100 lines
sudo journalctl -u gym-habit -n 100

# View logs since 1 hour ago
sudo journalctl -u gym-habit --since "1 hour ago"
```

### Nginx Logs

```bash
# Access logs
sudo tail -f /var/log/nginx/access.log

# Error logs
sudo tail -f /var/log/nginx/error.log
```

### CloudWatch Integration (Optional)

Install CloudWatch agent to send logs and metrics to AWS CloudWatch.

---

## Backup Strategy

### MongoDB Backup

**Atlas:** Automatic continuous backups (free tier has limited backups, paid tiers have point-in-time recovery)

**DocumentDB:** Automated daily snapshots (configure retention period)

### Application Code

Code is in GitLab - already backed up.

---

## Security Checklist

- [ ] MongoDB connection uses TLS/SSL
- [ ] MongoDB authentication enabled
- [ ] JWT_SECRET_KEY is strong (32+ chars, random)
- [ ] Environment variables in AWS Secrets Manager (not in code)
- [ ] Default admin password changed after first login
- [ ] EC2 security group restricts SSH to your IP only
- [ ] HTTPS enabled (SSL certificate via ACM or Let's Encrypt)
- [ ] CORS configured for production domain only
- [ ] MongoDB network access restricted to EC2 IP
- [ ] Regular security updates applied: `sudo apt update && sudo apt upgrade`

---

## Scaling Recommendations

### Current Capacity (t3.small + MongoDB Atlas M0):
- **Gyms**: Up to 10,000
- **Concurrent Users**: ~100
- **Leads**: Up to 50,000

### When to Scale:

**Vertical Scaling (Upgrade EC2):**
- t3.medium: 10,000 users/month
- t3.large: 50,000 users/month

**Horizontal Scaling:**
- Add ALB
- Multiple EC2 instances
- Auto-scaling group

**Database Scaling:**
- MongoDB Atlas M10: Up to 100k gyms
- MongoDB Atlas M30+: Unlimited (with sharding)

---

## Cost Estimation

### Development/Staging:
- EC2 t3.small: $15/month
- MongoDB Atlas M0: $0 (free)
- **Total: ~$15/month**

### Production (Small):
- EC2 t3.small: $15/month
- MongoDB Atlas M10: $60/month
- ALB: $20/month
- **Total: ~$95/month**

### Production (Medium):
- EC2 t3.medium: $30/month
- MongoDB Atlas M30: $150/month
- ALB: $20/month
- CloudWatch: $10/month
- **Total: ~$210/month**

---

## GitLab CI/CD Pipeline (Optional)

Create `.gitlab-ci.yml` in repository:

```yaml
stages:
  - test
  - deploy

test:
  stage: test
  image: python:3.10
  script:
    - pip install -r requirements.txt
    - echo "Tests would run here"
  only:
    - main
    - develop

deploy_production:
  stage: deploy
  image: ubuntu:22.04
  before_script:
    - apt-get update && apt-get install -y openssh-client
    - eval $(ssh-agent -s)
    - echo "$SSH_PRIVATE_KEY" | tr -d '\r' | ssh-add -
    - mkdir -p ~/.ssh
    - chmod 700 ~/.ssh
  script:
    - ssh -o StrictHostKeyChecking=no ubuntu@$EC2_HOST "cd /home/ubuntu/gym-habit && git pull origin main && sudo systemctl restart gym-habit"
  only:
    - main
  when: manual
```

**GitLab Variables to set:**
- `SSH_PRIVATE_KEY`: EC2 private key
- `EC2_HOST`: EC2 public IP or domain

---

## Troubleshooting

### Issue: Can't connect to MongoDB

**Symptoms:** App crashes on startup with "Connection refused"

**Solutions:**
1. Check MongoDB URL in `.env` is correct
2. Verify MongoDB Atlas network access allows EC2 IP
3. Test connection: `mongosh "YOUR_MONGODB_URL"`

### Issue: 502 Bad Gateway

**Cause:** FastAPI not running

**Solution:**
```bash
sudo systemctl status gym-habit
sudo systemctl restart gym-habit
sudo journalctl -u gym-habit -n 50
```

### Issue: Admin login not working

**Cause:** Admin user not created

**Solution:**
Check logs for admin creation message:
```bash
sudo journalctl -u gym-habit | grep "admin"
```

If not created, check `.env` has correct `DEFAULT_ADMIN_EMAIL` and `DEFAULT_ADMIN_PASSWORD`.

---

## Migration from GitHub to GitLab

```bash
# Clone from GitHub
git clone https://github.com/YOUR_USERNAME/gym-habit.git
cd gym-habit

# Add GitLab remote
git remote add gitlab https://gitlab.com/YOUR_ORG/gym-habit.git

# Push to GitLab
git push gitlab main

# Update origin
git remote remove origin
git remote rename gitlab origin
```

---

## Questions for DevOps Team

Before deployment, please clarify:

1. **AWS Account Details:**
   - Which AWS account/region?
   - Do you have an existing VPC?

2. **MongoDB Preference:**
   - MongoDB Atlas (external, free tier available)?
   - AWS DocumentDB (AWS-native, $200+/month)?

3. **Domain & SSL:**
   - What domain will this use?
   - Do you have SSL certificate or need ACM?

4. **Deployment Method:**
   - EC2 (simple)?
   - ECS Fargate (containerized)?
   - Lambda (serverless)?

5. **Budget:**
   - Monthly budget for this application?

6. **Environment:**
   - Need separate dev/staging/production environments?

7. **Monitoring:**
   - CloudWatch sufficient or need external monitoring?

---

## Support Contacts

- **Application Developer**: [Your contact]
- **GitLab Repository**: [To be provided after migration]
- **API Documentation**: Available at `/docs` after deployment
- **Health Check**: Available at `/health` after deployment

---

**End of DevOps Deployment Guide**
