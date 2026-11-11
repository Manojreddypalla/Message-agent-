# database.py
from datetime import datetime

# Today: In-memory dictionary.
# Tomorrow: Replace the queries below with MongoDB or PostgreSQL queries!
MEMBERS_TABLE = {
    "919876543210": {
        "name": "Manoj Reddy",
        "plan": "Gold Annual",
        "expiry": "2026-12-31",
        "fee_due": 0,
        "trainer": "Coach Vikram",
        "goal": "Muscle Hypertrophy",
    }
}

def get_member_by_phone(phone: str) -> dict:
    """Finds a member by phone. In the future: return db.members.find_one({'phone': phone})"""
    clean_phone = phone.replace("+", "").replace("whatsapp:", "").strip()
    return MEMBERS_TABLE.get(clean_phone)

def record_gym_visit(phone: str):
    """Updates last visit date. In the future: db.members.update_one(...)"""
    clean_phone = phone.replace("+", "").replace("whatsapp:", "").strip()
    if clean_phone in MEMBERS_TABLE:
        MEMBERS_TABLE[clean_phone]["last_visit"] = datetime.now().strftime("%Y-%m-%d")