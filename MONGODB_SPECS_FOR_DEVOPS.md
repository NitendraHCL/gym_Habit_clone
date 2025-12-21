# MongoDB Specifications for Dev Environment
**Gym Habit Application**

## 1. MongoDB Instance Specifications

### Recommended Setup: MongoDB Atlas (Cloud)

**Instance Type**: M0 (Free Tier) or M10 (Development)

| Specification | M0 (Free Tier) | M10 (Recommended for Dev) |
|--------------|----------------|---------------------------|
| **RAM** | 512 MB | 2 GB |
| **Storage** | 512 MB | 10 GB |
| **vCPUs** | Shared | 1 |
| **Cost** | Free | ~₹4,500/month (~$60/month) |
| **Backup** | No automatic backups | Automated backups |
| **Recommended For** | Testing/POC | Development |

**Recommendation**: Use **M10** for dev environment (M0 is too limited for development)

### Alternative: Self-Hosted MongoDB on AWS EC2

If not using Atlas:

| Specification | Value |
|--------------|-------|
| **Instance Type** | t3.small or t3.medium |
| **RAM** | 2-4 GB |
| **Storage** | 20 GB SSD (gp3) |
| **MongoDB Version** | 6.0+ or 7.0+ |
| **OS** | Ubuntu 22.04 LTS |

---

## 2. Database Configuration

### Database Details

```javascript
Database Name: gym_habit
Character Set: UTF-8
```

### Collections to Create

**Total Collections**: 4

1. **gyms** - Gym/partner location data
2. **leads** - User subscription requests
3. **partners** - Partner metadata
4. **users** - Admin/facilitator accounts

**Note**: Collections will be auto-created by the application on first run, but **indexes must be created manually**.

---

## 3. Required Indexes (CRITICAL - Must Create)

### Run these commands after database is created:

```javascript
// Connect to MongoDB
use gym_habit;

// ========================================
// GYMS COLLECTION INDEXES (5 indexes)
// ========================================

// 1. Geospatial index for nearby searches (MOST IMPORTANT)
db.gyms.createIndex({ "location": "2dsphere" });

// 2. Unique gym ID
db.gyms.createIndex({ "gym_id": 1 }, { unique: true });

// 3. Pincode search
db.gyms.createIndex({ "pincode": 1 });

// 4. City search
db.gyms.createIndex({ "city": 1 });

// 5. Active gyms filter
db.gyms.createIndex({ "is_active": 1 });


// ========================================
// LEADS COLLECTION INDEXES (4 indexes)
// ========================================

// 1. Unique lead ID
db.leads.createIndex({ "lead_id": 1 }, { unique: true });

// 2. Sort by creation date (descending)
db.leads.createIndex({ "created_at": -1 });

// 3. Filter by status
db.leads.createIndex({ "status": 1 });

// 4. Filter by payment status
db.leads.createIndex({ "payment.status": 1 });


// ========================================
// PARTNERS COLLECTION INDEXES (1 index)
// ========================================

// 1. Unique partner name
db.partners.createIndex({ "name": 1 }, { unique: true });


// ========================================
// USERS COLLECTION INDEXES (2 indexes)
// ========================================

// 1. Unique email for login
db.users.createIndex({ "email": 1 }, { unique: true });

// 2. Active users filter
db.users.createIndex({ "is_active": 1 });
```

**Total Indexes**: 14 (including MongoDB's default _id indexes)

---

## 4. Network & Security Configuration

### MongoDB Atlas Setup

1. **Network Access (IP Whitelist)**:
   ```
   Add the application server IP address
   OR
   Add: 0.0.0.0/0 (Allow from anywhere - dev only)
   ```

2. **Database User**:
   ```
   Username: gym_habit_dev
   Password: <Generate strong password>
   Role: Atlas admin OR "Read and write to any database"
   ```

3. **Connection String Format**:
   ```
   mongodb+srv://gym_habit_dev:<password>@cluster-name.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```

### Self-Hosted MongoDB Setup

1. **Port**: 27017 (default)
2. **Security Group**: Allow port 27017 from application server IP only
3. **Authentication**: Enable authentication
4. **SSL/TLS**: Enable TLS encryption

---

## 5. Environment Variables for Application

Provide these to the application server:

```bash
# MongoDB Connection
MONGODB_URL=mongodb+srv://gym_habit_dev:<password>@cluster-name.xxxxx.mongodb.net/?retryWrites=true&w=majority

# For self-hosted MongoDB:
# MONGODB_URL=mongodb://gym_habit_dev:<password>@mongodb-host:27017/gym_habit

# JWT Secret (Generate random 32+ character string)
JWT_SECRET_KEY=<GENERATE_STRONG_RANDOM_STRING_MIN_32_CHARS>

# Google Geocoding API Key
GOOGLE_GEOCODING_API_KEY=<YOUR_API_KEY>

# Environment
ENVIRONMENT=development

# Default Admin Credentials (for first-time setup)
DEFAULT_ADMIN_EMAIL=admin@hclhealthcare.in
DEFAULT_ADMIN_PASSWORD=Admin@2025
DEFAULT_ADMIN_NAME=Admin User
```

### How to Generate JWT_SECRET_KEY:

**Linux/Mac**:
```bash
openssl rand -hex 32
```

**Windows PowerShell**:
```powershell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Minimum 0 -Maximum 256 }))
```

**Online** (if needed): https://randomkeygen.com/ (use "CodeIgniter Encryption Keys")

---

## 6. Initial Data Setup

### Default Admin User

The application will **automatically create** the default admin user on first startup using the environment variables:

- Email: `admin@hclhealthcare.in` (from `DEFAULT_ADMIN_EMAIL`)
- Password: `Admin@2025` (from `DEFAULT_ADMIN_PASSWORD`)
- Role: `admin`

**IMPORTANT**: Change this password immediately after first login via the admin panel.

### Sample Gym Data (Optional)

If you want to pre-populate with sample gyms for testing:

```javascript
// Sample gym insert
db.gyms.insertOne({
  "gym_id": 1,
  "gym_name": "Cult Andheri West",
  "partner_name": "Cult",
  "address": "Plot 123, Veera Desai Road, Andheri West, Mumbai",
  "city": "Mumbai",
  "state": "Maharashtra",
  "pincode": "400053",
  "latitude": 19.1136,
  "longitude": 72.8697,
  "location": {
    "type": "Point",
    "coordinates": [72.8697, 19.1136]  // [longitude, latitude]
  },
  "amenities": ["AC", "Parking", "Showers", "Lockers", "WiFi"],
  "subscription_amount": 1499,
  "custom_plans": {
    "1_month": 1499,
    "3_months": 4200,
    "6_months": 7900,
    "12_months": 14900
  },
  "icon": "🏋️",
  "is_active": true,
  "created_at": new Date()
});

// Sample partner insert
db.partners.insertOne({
  "name": "Cult",
  "description": "India's largest fitness chain",
  "icon": "🏋️",
  "created_at": new Date()
});
```

**Note**: You can add actual gym data later via the admin panel or CSV upload.

---

## 7. Verification Steps

After MongoDB is set up, verify:

### Step 1: Connect to MongoDB
```bash
# For Atlas
mongosh "mongodb+srv://gym_habit_dev:<password>@cluster-name.xxxxx.mongodb.net/"

# For self-hosted
mongosh "mongodb://gym_habit_dev:<password>@mongodb-host:27017/gym_habit"
```

### Step 2: Verify Database Created
```javascript
show dbs;
use gym_habit;
```

### Step 3: Verify Indexes Created
```javascript
db.gyms.getIndexes();      // Should show 6 indexes (including _id)
db.leads.getIndexes();     // Should show 5 indexes
db.partners.getIndexes();  // Should show 2 indexes
db.users.getIndexes();     // Should show 3 indexes
```

### Step 4: Test Application Connection
Once application is deployed:
```bash
# Health check endpoint
curl https://gym.hclhealthcare.in/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "mongodb",
  "gyms_loaded": 0,
  "partners": 0
}
```

---

## 8. Backup Configuration

### MongoDB Atlas (Automated)
- **Frequency**: Continuous (with M10+)
- **Retention**: 2 days (free), up to 35 days (paid)
- **Point-in-Time Recovery**: Available with M10+

### Self-Hosted (Manual Setup Required)

**Daily Backup Script**:
```bash
#!/bin/bash
DATE=$(date +%Y%m%d)
mongodump --uri="mongodb://gym_habit_dev:<password>@mongodb-host:27017/gym_habit" --out=/backup/gym_habit_$DATE
# Retention: Delete backups older than 7 days
find /backup -name "gym_habit_*" -mtime +7 -exec rm -rf {} \;
```

**Cron Job** (daily at 2 AM):
```bash
0 2 * * * /path/to/backup-script.sh
```

---

## 9. Monitoring & Alerts

### MongoDB Atlas (Built-in)
- CPU usage alerts
- Disk usage alerts
- Connection count monitoring
- Query performance insights

### Self-Hosted (Setup Required)
Install MongoDB monitoring tools:
- MongoDB Ops Manager
- Prometheus + Grafana
- CloudWatch (if on AWS)

### Key Metrics to Monitor:
- **Disk Usage**: Alert at 80%
- **Memory Usage**: Alert at 85%
- **Connection Count**: Alert at 80% of max
- **Query Performance**: Slow queries (>100ms)

---

## 10. Estimated Storage Requirements

### Dev Environment Estimates:

| Data | Volume | Storage |
|------|--------|---------|
| **Gyms** | 1,000 gyms | ~10 MB |
| **Leads** | 5,000 leads | ~25 MB |
| **Partners** | 10 partners | ~10 KB |
| **Users** | 5 users | ~5 KB |
| **Indexes** | All collections | ~5 MB |
| **Total** | - | **~40 MB** |

**Recommendation**: Provision **10 GB storage** for dev environment (250x headroom).

---

## 11. Performance Expectations

### Response Times (with proper indexes):

| Query Type | Expected Time |
|------------|---------------|
| Nearby gyms search | <50ms |
| Pincode search | <10ms |
| City search | <20ms |
| Lead listing (paginated) | <100ms |
| Admin login | <200ms |

### Concurrent Users:
- **M0 (Free)**: ~10 concurrent users
- **M10**: ~100 concurrent users
- **M30+**: 500+ concurrent users

---

## 12. Migration from Dev to Production

When moving to production:

1. **Export Data**:
   ```bash
   mongodump --uri="mongodb+srv://dev-cluster..." --out=/backup/dev_export
   ```

2. **Import to Production**:
   ```bash
   mongorestore --uri="mongodb+srv://prod-cluster..." /backup/dev_export
   ```

3. **Re-create Indexes** (important - indexes don't transfer perfectly)
   - Run all index creation commands again on production DB

4. **Update Environment Variables**:
   - New `MONGODB_URL` for production
   - New `JWT_SECRET_KEY` (don't reuse dev key)
   - Change `ENVIRONMENT=production`

---

## 13. Troubleshooting

### Issue: Cannot Connect to MongoDB

**Check**:
1. Network access/IP whitelist includes application server IP
2. Username/password are correct
3. Connection string format is correct
4. Firewall allows port 27017 (if self-hosted)

**Test Connection**:
```bash
mongosh "YOUR_CONNECTION_STRING"
```

### Issue: Slow Queries

**Check**:
1. All 14 indexes are created (run `db.collection.getIndexes()`)
2. MongoDB has sufficient RAM
3. No long-running operations blocking queries

### Issue: Application Won't Start

**Check**:
1. `MONGODB_URL` environment variable is set correctly
2. MongoDB is accessible from application server
3. Database user has correct permissions
4. Application logs: `sudo journalctl -u gym-habit -n 100`

---

## 14. Security Checklist

- [ ] MongoDB authentication enabled
- [ ] Network access restricted to application server IP only
- [ ] Strong password for database user (min 16 characters)
- [ ] TLS/SSL encryption enabled
- [ ] JWT_SECRET_KEY is strong and random (32+ characters)
- [ ] Default admin password changed after first login
- [ ] No sensitive data in application logs
- [ ] Regular backups configured and tested

---

## 15. Contact for MongoDB Issues

**If you encounter issues during setup**:

1. **MongoDB Atlas Support**: Available in Atlas dashboard
2. **Application Logs**: Check application health endpoint (`/health`)
3. **Connection Test**: Use `mongosh` to test connection string
4. **Documentation**: See `DATABASE_SCHEMA.md` for full schema details

---

## Summary Checklist for DevOps Team

- [ ] **Create MongoDB instance** (M10 on Atlas OR t3.small EC2)
- [ ] **Create database** `gym_habit`
- [ ] **Create database user** `gym_habit_dev` with admin privileges
- [ ] **Whitelist application server IP** in network access
- [ ] **Run all 14 index creation commands** (see Section 3)
- [ ] **Generate JWT_SECRET_KEY** (32+ characters)
- [ ] **Provide connection string** to application team
- [ ] **Provide environment variables** (see Section 5)
- [ ] **Configure automated backups** (if M10+)
- [ ] **Set up monitoring alerts** (disk, memory, connections)
- [ ] **Test connection** using mongosh
- [ ] **Verify health endpoint** after app deployment

---

## Questions?

If you have questions during setup, refer to:
- `DATABASE_SCHEMA.md` - Complete database structure
- `DEPLOYMENT_GUIDE_DEVOPS.md` - Full deployment guide
- `TECH_STACK.md` - Technology overview

**End of MongoDB Specifications Document**
