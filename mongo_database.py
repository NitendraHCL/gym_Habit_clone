"""
Gym Habit - MongoDB Database Layer
Handles MongoDB operations for gyms and leads
"""

import math
from datetime import datetime
from typing import List, Dict, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
import config
from mongodb import MongoDB


class MongoGymDatabase:
    """Manages gym data from MongoDB"""

    def __init__(self):
        self.db: Optional[AsyncIOMotorDatabase] = None

    async def initialize(self):
        """Initialize MongoDB connection"""
        await MongoDB.connect_db()
        self.db = MongoDB.db

    async def get_all_partners(self) -> List[Dict[str, any]]:
        """
        Get unique list of partners from partners collection merged with gym-derived partners
        Returns: [{"name": "Cult", "count": 10, "description": "...", "icon": "..."}, ...]
        """
        # Get partners from partners collection
        partners_cursor = self.db.partners.find({})
        partners_docs = await partners_cursor.to_list(None)

        # Create a dict with partner info from partners collection
        partners_dict = {}
        for p in partners_docs:
            partners_dict[p['name']] = {
                'name': p['name'],
                'description': p.get('description', ''),
                'icon': p.get('icon'),
                'count': 0  # Will be updated from gyms
            }

        # Get gym counts by partner
        pipeline = [
            {"$match": {"is_active": True}},
            {
                "$group": {
                    "_id": "$partner_name",
                    "count": {"$sum": 1}
                }
            }
        ]

        gym_counts = await self.db.gyms.aggregate(pipeline).to_list(None)

        # Merge gym counts with partner info
        for gc in gym_counts:
            partner_name = gc['_id']
            if partner_name in partners_dict:
                partners_dict[partner_name]['count'] = gc['count']
            else:
                # Partner exists in gyms but not in partners collection
                partners_dict[partner_name] = {
                    'name': partner_name,
                    'description': '',
                    'icon': None,
                    'count': gc['count']
                }

        # Convert to list and sort
        partners_list = list(partners_dict.values())
        partners_list.sort(key=lambda x: x['name'])

        return partners_list

    async def get_gyms_by_partner(self, partner: str) -> List[Dict]:
        """
        Filter gyms by partner name
        Args:
            partner: Partner name (e.g., "Cult")
        Returns: List of gym dictionaries
        """
        if not partner:
            cursor = self.db.gyms.find({"is_active": True})
            gyms = await cursor.to_list(None)
            return [self._format_gym(g) for g in gyms]

        cursor = self.db.gyms.find({
            "partner_name": {"$regex": f"^{partner}$", "$options": "i"},
            "is_active": True
        })
        gyms = await cursor.to_list(None)
        return [self._format_gym(g) for g in gyms]

    async def get_all_gyms(self) -> List[Dict]:
        """Get all active gyms"""
        cursor = self.db.gyms.find({"is_active": True})
        gyms = await cursor.to_list(None)
        return [self._format_gym(g) for g in gyms]

    async def get_gym_by_id(self, gym_id: int) -> Optional[Dict]:
        """
        Get single gym by ID
        Args:
            gym_id: Gym ID
        Returns: Gym dictionary or None
        """
        gym = await self.db.gyms.find_one({"gym_id": gym_id, "is_active": True})
        if gym:
            return self._format_gym(gym)
        return None

    async def search_by_pincode(self, pincode: str, limit: int = 10) -> List[Dict]:
        """
        Search gyms by pincode (instant, no distance calculation)
        Args:
            pincode: 6-digit pincode
            limit: Max results
        Returns: List of gyms in that pincode
        """
        # Exact pincode match
        cursor = self.db.gyms.find({
            "pincode": pincode,
            "is_active": True
        }).limit(limit)

        exact_matches = await cursor.to_list(limit)

        if exact_matches:
            return [self._format_gym(g) for g in exact_matches]

        # Try nearby pincodes (same first 3 digits)
        prefix = pincode[:3]
        cursor = self.db.gyms.find({
            "pincode": {"$regex": f"^{prefix}"},
            "is_active": True
        }).limit(limit)

        nearby_gyms = await cursor.to_list(limit)
        return [self._format_gym(g) for g in nearby_gyms]

    async def search_by_city(self, city: str, limit: int = 100) -> List[Dict]:
        """
        Get gyms in a specific city
        Args:
            city: City name
            limit: Max results
        Returns: List of gyms in that city
        """
        cursor = self.db.gyms.find({
            "city": {"$regex": f"^{city}$", "$options": "i"},
            "is_active": True
        }).limit(limit)

        gyms = await cursor.to_list(limit)
        return [self._format_gym(g) for g in gyms]

    async def get_nearby_gyms(
        self,
        user_lat: float,
        user_lon: float,
        partner: Optional[str] = None,
        city: Optional[str] = None,
        limit: int = 10,
        max_distance_km: int = 50
    ) -> List[Dict]:
        """
        Find nearest gyms using MongoDB geospatial query
        Args:
            user_lat: User's latitude
            user_lon: User's longitude
            partner: Optional partner filter
            city: Optional city filter (speeds up search)
            limit: Max number of results (default: 10)
            max_distance_km: Maximum distance in kilometers (default: 50)
        Returns: List of gyms sorted by distance
        """
        # Build query
        query = {
            "is_active": True,
            "location": {
                "$near": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [user_lon, user_lat]  # GeoJSON uses [lon, lat]
                    },
                    "$maxDistance": max_distance_km * 1000  # Convert to meters
                }
            }
        }

        # Add partner filter if provided
        if partner:
            query["partner_name"] = {"$regex": f"^{partner}$", "$options": "i"}

        # Add city filter if provided
        if city:
            query["city"] = {"$regex": f"^{city}$", "$options": "i"}

        # Execute query
        cursor = self.db.gyms.find(query).limit(limit)
        gyms = await cursor.to_list(limit)

        # Calculate distances and format
        results = []
        for gym in gyms:
            formatted = self._format_gym(gym)
            # Calculate haversine distance for accurate km
            formatted['distance'] = haversine_distance(
                user_lat, user_lon,
                formatted['latitude'], formatted['longitude']
            )
            results.append(formatted)

        return results

    async def create_gym(
        self,
        gym_name: str,
        partner_name: str,
        address: str,
        city: str,
        state: str,
        pincode: str,
        latitude: float,
        longitude: float,
        amenities: List[str],
        subscription_amount: int = 1499,
        icon: str = None
    ) -> int:
        """
        Create a new gym entry
        Args:
            gym_name: Name of the gym
            partner_name: Partner name (e.g., "Cult", "Gold's Gym")
            address: Full address
            city: City name
            state: State name
            pincode: 6-digit pincode
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            amenities: List of amenities
            subscription_amount: Monthly subscription amount (default: 1499)
        Returns: New gym_id
        """
        # Generate new gym_id
        max_gym = await self.db.gyms.find_one(sort=[("gym_id", -1)])
        new_gym_id = (max_gym['gym_id'] + 1) if max_gym else 1

        # Create gym document
        new_gym = {
            'gym_id': new_gym_id,
            'gym_name': gym_name,
            'partner_name': partner_name,
            'address': address,
            'city': city,
            'state': state,
            'pincode': pincode,
            'latitude': latitude,
            'longitude': longitude,
            'location': {
                'type': 'Point',
                'coordinates': [longitude, latitude]  # GeoJSON format [lon, lat]
            },
            'amenities': amenities,
            'subscription_amount': subscription_amount,
            'is_active': True,
            'icon': icon,
            'created_at': datetime.utcnow()
        }

        # Insert into MongoDB
        await self.db.gyms.insert_one(new_gym)
        print(f"[CREATED] Gym created: {gym_name} (ID: {new_gym_id})")

        return new_gym_id


    async def update_gym(
        self,
        gym_id: int,
        gym_name: str,
        partner_name: str,
        address: str,
        city: str,
        state: str,
        pincode: str,
        latitude: float,
        longitude: float,
        amenities: List[str],
        subscription_amount: int = 1499,
        icon: str = None
    ) -> bool:
        """
        Update an existing gym
        Returns: True if updated, False if gym not found
        """
        update_data = {
            'gym_name': gym_name,
            'partner_name': partner_name,
            'address': address,
            'city': city,
            'state': state,
            'pincode': pincode,
            'latitude': latitude,
            'longitude': longitude,
            'location': {
                'type': 'Point',
                'coordinates': [longitude, latitude]
            },
            'amenities': amenities,
            'subscription_amount': subscription_amount,
            'icon': icon,
            'updated_at': datetime.utcnow()
        }

        result = await self.db.gyms.update_one(
            {'gym_id': gym_id, 'is_active': True},
            {'$set': update_data}
        )

        return result.matched_count > 0

    async def update_partner(
        self,
        old_name: str,
        new_name: str,
        description: str = "",
        icon: str = None
    ) -> bool:
        """
        Update an existing partner (or create if doesn't exist in partners collection)
        If name changes, also update all associated gyms
        Returns: True if updated
        """
        update_data = {
            'name': new_name,
            'description': description,
            'icon': icon,
            'updated_at': datetime.utcnow()
        }

        # Use upsert to create if doesn't exist
        # This handles partners that exist in gyms but not in partners collection
        result = await self.db.partners.update_one(
            {'name': old_name},
            {
                '$set': update_data,
                '$setOnInsert': {'created_at': datetime.utcnow()}
            },
            upsert=True  # Insert if doesn't exist
        )

        # If partner name changed, update all gyms with this partner
        if old_name != new_name:
            await self.db.gyms.update_many(
                {'partner_name': old_name},
                {'$set': {'partner_name': new_name}}
            )

        print(f"[UPDATED] Partner '{old_name}' -> '{new_name}' (upserted={result.upserted_id is not None})")
        return True  # Always return True since upsert guarantees success

    async def delete_gym(self, gym_id: int) -> bool:
        """
        Soft delete a gym (mark as inactive)
        Args:
            gym_id: Gym ID to delete
        Returns: True if deleted, False if not found
        """
        result = await self.db.gyms.update_one(
            {"gym_id": gym_id},
            {
                "$set": {
                    "is_active": False,
                    "deleted_at": datetime.utcnow()
                }
            }
        )

        if result.modified_count > 0:
            print(f"[DELETED] Gym deleted: ID {gym_id}")
            return True
        return False

    async def delete_partner(self, partner_name: str) -> int:
        """
        Delete partner from partners collection and soft delete all gyms
        Args:
            partner_name: Partner name to delete
        Returns: Number of gyms deleted
        """
        # Soft delete all gyms of this partner
        gym_result = await self.db.gyms.update_many(
            {"partner_name": {"$regex": f"^{partner_name}$", "$options": "i"}},
            {
                "$set": {
                    "is_active": False,
                    "deleted_at": datetime.utcnow()
                }
            }
        )

        # Delete partner from partners collection
        await self.db.partners.delete_one({"name": partner_name})

        print(f"[DELETED] Partner deleted: {partner_name} ({gym_result.modified_count} gyms)")
        return gym_result.modified_count

    async def create_partner_entry(self, partner_name: str, description: str = "", icon: str = None) -> bool:
        """
        Create a partner entry in partners collection
        Args:
            partner_name: Partner name
            description: Partner description
            icon: Partner icon (emoji or base64 image)
        Returns: True if created, False if already exists
        """
        # Check if partner already exists in partners collection
        existing = await self.db.partners.find_one({"name": partner_name})

        if existing:
            return False  # Partner already exists

        # Create partner document
        partner_doc = {
            'name': partner_name,
            'description': description,
            'icon': icon,
            'created_at': datetime.utcnow()
        }

        await self.db.partners.insert_one(partner_doc)
        print(f"[INFO] Partner '{partner_name}' created in partners collection")
        return True

    def _format_gym(self, gym: Dict) -> Dict:
        """
        Convert MongoDB gym document to API format
        Args:
            gym: MongoDB document
        Returns: Formatted gym dictionary
        """
        return {
            'id': gym['gym_id'],
            'partner_name': gym['partner_name'],
            'gym_name': gym['gym_name'],
            'address': gym['address'],
            'pincode': gym['pincode'],
            'city': gym['city'],
            'state': gym['state'],
            'latitude': gym['latitude'],
            'longitude': gym['longitude'],
            'subscription_amount': gym['subscription_amount'],
            'amenities': ', '.join(gym['amenities']) if isinstance(gym['amenities'], list) else gym['amenities']
        }


class MongoLeadManager:
    """Manages subscription/lead requests in MongoDB"""

    def __init__(self):
        self.db: Optional[AsyncIOMotorDatabase] = None

    async def initialize(self):
        """Initialize MongoDB connection"""
        await MongoDB.connect_db()
        self.db = MongoDB.db

    async def save_lead(self, lead_data: Dict) -> str:
        """
        Save subscription request/lead
        Args:
            lead_data: Dictionary with user info and gym details
        Returns: Lead ID
        """
        # Generate lead ID
        date_str = datetime.now().strftime('%Y%m%d')

        # Count existing leads for today
        count = await self.db.leads.count_documents({
            "lead_id": {"$regex": f"^{config.LEAD_ID_PREFIX}_{date_str}"}
        })

        lead_id = f"{config.LEAD_ID_PREFIX}_{date_str}_{(count + 1):04d}"

        # Create lead document
        new_lead = {
            'lead_id': lead_id,
            'created_at': datetime.utcnow(),
            'gym_id': lead_data['gym_id'],
            'gym_name': lead_data['gym_name'],
            'partner_name': lead_data['partner_name'],
            'full_name': lead_data['full_name'],
            'email': lead_data.get('email', ''),
            'phone': lead_data['phone'],
            'preferred_plan': lead_data['preferred_plan'],
            'billing_address': lead_data.get('billing_address', ''),
            'message': lead_data.get('message', ''),
            'user_location': {
                'latitude': lead_data.get('user_latitude'),
                'longitude': lead_data.get('user_longitude'),
                'city': lead_data.get('user_city')
            },
            'status': 'new',  # new, contacted, interested, not_interested, closed
            'payment': {
                'status': 'pending',  # pending, link_shared, paid, failed
                'amount': None,
                'payment_link': None,
                'updated_at': None
            },
            'comments': [],
            'audit_log': []
        }

        # Insert into MongoDB
        result = await self.db.leads.insert_one(new_lead)
        print(f"[SAVED] Lead saved: {lead_id}")

        return lead_id

    async def get_all_leads(
        self,
        skip: int = 0,
        limit: int = 20,
        status_filter: Optional[str] = None,
        payment_status_filter: Optional[str] = None,
        city_filter: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict:
        """
        Get all leads with filters and pagination
        Args:
            skip: Number of records to skip (for pagination)
            limit: Max records to return
            status_filter: Filter by lead status
            payment_status_filter: Filter by payment status
            city_filter: Filter by city
            date_from: Filter by start date
            date_to: Filter by end date
        Returns: {"leads": [...], "total": 100, "page": 1, "pages": 5}
        """
        # Build query
        query = {}

        if status_filter:
            query['status'] = status_filter

        if payment_status_filter:
            query['payment.status'] = payment_status_filter

        if city_filter:
            query['user_location.city'] = {"$regex": f"^{city_filter}$", "$options": "i"}

        if date_from or date_to:
            query['created_at'] = {}
            if date_from:
                query['created_at']['$gte'] = date_from
            if date_to:
                query['created_at']['$lte'] = date_to

        # Get total count
        total = await self.db.leads.count_documents(query)

        # Get leads
        cursor = self.db.leads.find(query).sort("created_at", -1).skip(skip).limit(limit)
        leads = await cursor.to_list(limit)

        # Format leads
        formatted_leads = [self._format_lead(lead) for lead in leads]

        return {
            "leads": formatted_leads,
            "total": total,
            "page": (skip // limit) + 1,
            "pages": (total + limit - 1) // limit,  # Ceiling division
            "per_page": limit
        }

    async def assign_lead(self, lead_id: str, assigned_to_email: str, assigned_to_name: str) -> bool:
        """
        Assign a lead to a user (tracks who is working on the lead)
        """
        result = await self.db.leads.update_one(
            {'lead_id': lead_id},
            {
                '$set': {
                    'assigned_to': assigned_to_email,
                    'assigned_to_name': assigned_to_name,
                    'assigned_at': datetime.utcnow()
                }
            }
        )
        return result.matched_count > 0

    async def get_lead_by_id(self, lead_id: str) -> Optional[Dict]:
        """
        Get a single lead by ID
        Args:
            lead_id: Lead ID (e.g., GYM_20251214_0001)
        Returns: Lead document or None
        """
        lead = await self.db.leads.find_one({"lead_id": lead_id})
        if lead:
            return self._format_lead(lead)
        return None

    async def update_lead_status(
        self,
        lead_id: str,
        new_status: str,
        updated_by: str,
        reason: Optional[str] = None
    ) -> bool:
        """
        Update lead status with audit logging
        Args:
            lead_id: Lead ID
            new_status: New status (new, contacted, interested, not_interested, closed)
            updated_by: User email who made the change
            reason: Optional reason for status change
        Returns: True if updated, False if lead not found
        """
        # Get current lead
        lead = await self.db.leads.find_one({"lead_id": lead_id})
        if not lead:
            return False

        old_status = lead.get('status', 'new')

        # Create audit entry
        audit_entry = {
            "timestamp": datetime.utcnow(),
            "action": "status_change",
            "user": updated_by,
            "old_value": old_status,
            "new_value": new_status,
            "reason": reason
        }

        # Update lead
        result = await self.db.leads.update_one(
            {"lead_id": lead_id},
            {
                "$set": {
                    "status": new_status,
                    "updated_at": datetime.utcnow()
                },
                "$push": {"audit_log": audit_entry}
            }
        )

        return result.modified_count > 0

    async def add_comment(
        self,
        lead_id: str,
        comment_text: str,
        added_by: str
    ) -> bool:
        """
        Add a comment to a lead
        Args:
            lead_id: Lead ID
            comment_text: Comment content
            added_by: User email who added the comment
        Returns: True if added, False if lead not found
        """
        comment = {
            "timestamp": datetime.utcnow(),
            "user": added_by,
            "text": comment_text
        }

        # Create audit entry
        audit_entry = {
            "timestamp": datetime.utcnow(),
            "action": "comment_added",
            "user": added_by,
            "comment": comment_text
        }

        result = await self.db.leads.update_one(
            {"lead_id": lead_id},
            {
                "$set": {"updated_at": datetime.utcnow()},
                "$push": {
                    "comments": comment,
                    "audit_log": audit_entry
                }
            }
        )

        return result.modified_count > 0

    async def update_payment(
        self,
        lead_id: str,
        payment_status: str,
        updated_by: str,
        payment_link: Optional[str] = None,
        amount: Optional[int] = None
    ) -> bool:
        """
        Update payment information for a lead
        Args:
            lead_id: Lead ID
            payment_status: Payment status (pending, link_shared, paid, failed)
            updated_by: User email who made the change
            payment_link: Payment link URL
            amount: Payment amount
        Returns: True if updated, False if lead not found
        """
        # Get current lead
        lead = await self.db.leads.find_one({"lead_id": lead_id})
        if not lead:
            return False

        old_payment = lead.get('payment', {})

        # Prepare update
        update_data = {
            "payment.status": payment_status,
            "payment.updated_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        if payment_link is not None:
            update_data["payment.payment_link"] = payment_link

        if amount is not None:
            update_data["payment.amount"] = amount

        # Create audit entry
        audit_entry = {
            "timestamp": datetime.utcnow(),
            "action": "payment_update",
            "user": updated_by,
            "old_status": old_payment.get('status', 'pending'),
            "new_status": payment_status,
            "amount": amount,
            "payment_link": payment_link
        }

        # Update lead
        result = await self.db.leads.update_one(
            {"lead_id": lead_id},
            {
                "$set": update_data,
                "$push": {"audit_log": audit_entry}
            }
        )

        return result.modified_count > 0

    async def update_plan(
        self,
        lead_id: str,
        new_plan: str,
        updated_by: str,
        reason: Optional[str] = None
    ) -> bool:
        """
        Update the membership plan for a lead
        Args:
            lead_id: Lead ID
            new_plan: New plan (e.g., "1 Month", "3 Months", "6 Months", "12 Months")
            updated_by: User email who made the change
            reason: Optional reason for plan change
        Returns: True if updated, False if lead not found
        """
        # Get current lead
        lead = await self.db.leads.find_one({"lead_id": lead_id})
        if not lead:
            return False

        old_plan = lead.get('preferred_plan', '')

        # Create audit entry
        audit_entry = {
            "timestamp": datetime.utcnow(),
            "action": "plan_change",
            "user": updated_by,
            "old_value": old_plan,
            "new_value": new_plan,
            "reason": reason
        }

        # Update lead
        result = await self.db.leads.update_one(
            {"lead_id": lead_id},
            {
                "$set": {
                    "preferred_plan": new_plan,
                    "updated_at": datetime.utcnow()
                },
                "$push": {"audit_log": audit_entry}
            }
        )

        return result.modified_count > 0

    async def get_audit_trail(self, lead_id: str) -> Optional[List[Dict]]:
        """
        Get audit trail for a lead
        Args:
            lead_id: Lead ID
        Returns: List of audit entries or None if lead not found
        """
        lead = await self.db.leads.find_one({"lead_id": lead_id})
        if not lead:
            return None

        return lead.get('audit_log', [])

    def _format_lead(self, lead: Dict) -> Dict:
        """Format lead for API response"""
        formatted = lead.copy()
        formatted.pop('_id', None)
        return formatted


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two points using Haversine formula

    Args:
        lat1, lon1: First point coordinates (degrees)
        lat2, lon2: Second point coordinates (degrees)

    Returns:
        Distance in kilometers (rounded to 2 decimals)
    """
    # Earth's radius in kilometers
    R = 6371.0

    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Differences
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    # Haversine formula
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))

    # Distance
    distance = R * c

    return round(distance, 2)


def calculate_subscription_plans(base_monthly: int) -> Dict[str, Dict[str, int]]:
    """
    Calculate subscription plans with discounts

    Args:
        base_monthly: Base monthly price

    Returns:
        Dictionary with plan details
    """
    plans = {
        '1-month': {
            'duration': '1 month',
            'total': base_monthly,
            'monthly': base_monthly,
            'savings': 0
        },
        '3-month': {
            'duration': '3 months',
            'total': int(base_monthly * 3 * 0.93),  # 7% discount
            'monthly': int(base_monthly * 0.93),
            'savings': int(base_monthly * 3 * 0.07)
        },
        '12-month': {
            'duration': '12 months',
            'total': int(base_monthly * 12 * 0.83),  # 17% discount
            'monthly': int(base_monthly * 0.83),
            'savings': int(base_monthly * 12 * 0.17)
        }
    }
    return plans
