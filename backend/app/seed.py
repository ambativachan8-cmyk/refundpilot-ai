"""Mock CRM + order data for RefundPilot AI.

15 customer profiles, each mapped to one of the 15 required refund scenarios.
CUST-001 has a second (cheap) order so the demo can showcase keyword-based
order disambiguation (the visible "warning" path in the admin logs).
"""
from __future__ import annotations

# --- Customers -------------------------------------------------------------
# tier: standard | plus | premium
CUSTOMERS = [
    {"customer_id": "CUST-001", "name": "Aarav Sharma", "email": "aarav.sharma@example.com",
     "tier": "plus", "refund_count_90d": 0, "risk_flag": False,
     "notes": "Loyal customer, clean history."},
    {"customer_id": "CUST-002", "name": "Meera Iyer", "email": "meera.iyer@example.com",
     "tier": "standard", "refund_count_90d": 1, "risk_flag": False,
     "notes": "Electronics buyer."},
    {"customer_id": "CUST-003", "name": "Rohan Verma", "email": "rohan.verma@example.com",
     "tier": "standard", "refund_count_90d": 0, "risk_flag": False,
     "notes": "Occasional shopper."},
    {"customer_id": "CUST-004", "name": "Priya Nair", "email": "priya.nair@example.com",
     "tier": "plus", "refund_count_90d": 1, "risk_flag": False,
     "notes": "Apparel buyer."},
    {"customer_id": "CUST-005", "name": "Karan Mehta", "email": "karan.mehta@example.com",
     "tier": "standard", "refund_count_90d": 0, "risk_flag": False,
     "notes": "Reported damaged delivery with photos."},
    {"customer_id": "CUST-006", "name": "Ananya Reddy", "email": "ananya.reddy@example.com",
     "tier": "standard", "refund_count_90d": 0, "risk_flag": False,
     "notes": "Reported damage, no photos provided yet."},
    {"customer_id": "CUST-007", "name": "Vikram Singh", "email": "vikram.singh@example.com",
     "tier": "standard", "refund_count_90d": 0, "risk_flag": False,
     "notes": "Bought a clearance final-sale item."},
    {"customer_id": "CUST-008", "name": "Sneha Kapoor", "email": "sneha.kapoor@example.com",
     "tier": "premium", "refund_count_90d": 0, "risk_flag": False,
     "notes": "High-value electronics purchase."},
    {"customer_id": "CUST-009", "name": "Arjun Desai", "email": "arjun.desai@example.com",
     "tier": "standard", "refund_count_90d": 5, "risk_flag": True,
     "notes": "Frequent refunder — flagged for review."},
    {"customer_id": "CUST-010", "name": "Isha Joshi", "email": "isha.joshi@example.com",
     "tier": "plus", "refund_count_90d": 0, "risk_flag": False,
     "notes": "Package marked delivered but not received."},
    {"customer_id": "CUST-011", "name": "Dev Patel", "email": "dev.patel@example.com",
     "tier": "standard", "refund_count_90d": 0, "risk_flag": False,
     "notes": "Received item as a gift."},
    {"customer_id": "CUST-012", "name": "Lena Fernandes", "email": "lena.fernandes@example.com",
     "tier": "plus", "refund_count_90d": 0, "risk_flag": False,
     "notes": "Shipping address outside India."},
    {"customer_id": "CUST-013", "name": "Aditya Rao", "email": "aditya.rao@example.com",
     "tier": "standard", "refund_count_90d": 0, "risk_flag": False,
     "notes": "Order was cancelled before shipping."},
    {"customer_id": "CUST-014", "name": "Nisha Gupta", "email": "nisha.gupta@example.com",
     "tier": "premium", "refund_count_90d": 0, "risk_flag": False,
     "notes": "Reports a defect long after delivery."},
    {"customer_id": "CUST-015", "name": "Farhan Khan", "email": "farhan.khan@example.com",
     "tier": "plus", "refund_count_90d": 1, "risk_flag": False,
     "notes": "Multi-item order, only part to be returned."},
]

# --- Orders ----------------------------------------------------------------
# condition_claimed: unused | used | damaged | partial | missing
# status: delivered | cancelled | in_transit
ORDERS = [
    # 1. Normal eligible refund (CUST-001) — within 30d, unused
    {"order_id": "ORD-1001", "customer_id": "CUST-001", "product_name": "Wireless Headphones",
     "category": "electronics", "price": 4999, "delivered_days_ago": 5, "status": "delivered",
     "condition_claimed": "unused", "final_sale": False, "damaged_claim": False,
     "photo_proof_available": False, "payment_method": "card", "country": "India"},
    # extra order for CUST-001 to demo disambiguation
    {"order_id": "ORD-1002", "customer_id": "CUST-001", "product_name": "Phone Case",
     "category": "accessories", "price": 499, "delivered_days_ago": 20, "status": "delivered",
     "condition_claimed": "unused", "final_sale": False, "damaged_claim": False,
     "photo_proof_available": False, "payment_method": "card", "country": "India"},

    # 2. Electronics outside 15-day window, used (CUST-002) — deny / warranty
    {"order_id": "ORD-1003", "customer_id": "CUST-002", "product_name": "Smartwatch",
     "category": "electronics", "price": 12999, "delivered_days_ago": 45, "status": "delivered",
     "condition_claimed": "used", "final_sale": False, "damaged_claim": False,
     "photo_proof_available": False, "payment_method": "card", "country": "India"},

    # 3. Outside refund window, non-electronics (CUST-003) — deny
    {"order_id": "ORD-1004", "customer_id": "CUST-003", "product_name": "Cookware Set",
     "category": "home", "price": 3499, "delivered_days_ago": 40, "status": "delivered",
     "condition_claimed": "unused", "final_sale": False, "damaged_claim": False,
     "photo_proof_available": False, "payment_method": "upi", "country": "India"},

    # 4. Used product within window (CUST-004) — deny
    {"order_id": "ORD-1005", "customer_id": "CUST-004", "product_name": "Running Shoes",
     "category": "apparel", "price": 2799, "delivered_days_ago": 10, "status": "delivered",
     "condition_claimed": "used", "final_sale": False, "damaged_claim": False,
     "photo_proof_available": False, "payment_method": "card", "country": "India"},

    # 5. Damaged on arrival WITH photo proof (CUST-005) — approve
    {"order_id": "ORD-1006", "customer_id": "CUST-005", "product_name": "Ceramic Dinner Set",
     "category": "home", "price": 3999, "delivered_days_ago": 3, "status": "delivered",
     "condition_claimed": "damaged", "final_sale": False, "damaged_claim": True,
     "photo_proof_available": True, "payment_method": "card", "country": "India"},

    # 6. Damaged on arrival WITHOUT photo proof (CUST-006) — escalate
    {"order_id": "ORD-1007", "customer_id": "CUST-006", "product_name": "Table Lamp",
     "category": "home", "price": 1899, "delivered_days_ago": 4, "status": "delivered",
     "condition_claimed": "damaged", "final_sale": False, "damaged_claim": True,
     "photo_proof_available": False, "payment_method": "upi", "country": "India"},

    # 7. Final-sale item (CUST-007) — deny
    {"order_id": "ORD-1008", "customer_id": "CUST-007", "product_name": "Clearance Jacket",
     "category": "apparel", "price": 1499, "delivered_days_ago": 6, "status": "delivered",
     "condition_claimed": "unused", "final_sale": True, "damaged_claim": False,
     "photo_proof_available": False, "payment_method": "card", "country": "India"},

    # 8. High-value order > 25000 (CUST-008) — escalate
    {"order_id": "ORD-1009", "customer_id": "CUST-008", "product_name": "Laptop",
     "category": "electronics", "price": 84999, "delivered_days_ago": 7, "status": "delivered",
     "condition_claimed": "unused", "final_sale": False, "damaged_claim": False,
     "photo_proof_available": False, "payment_method": "card", "country": "India"},

    # 9. Repeat refund abuser (CUST-009) — escalate
    {"order_id": "ORD-1010", "customer_id": "CUST-009", "product_name": "Bluetooth Speaker",
     "category": "electronics", "price": 2299, "delivered_days_ago": 4, "status": "delivered",
     "condition_claimed": "unused", "final_sale": False, "damaged_claim": False,
     "photo_proof_available": False, "payment_method": "card", "country": "India"},

    # 10. Missing package (CUST-010) — escalate
    {"order_id": "ORD-1011", "customer_id": "CUST-010", "product_name": "Backpack",
     "category": "accessories", "price": 2199, "delivered_days_ago": 2, "status": "delivered",
     "condition_claimed": "missing", "final_sale": False, "damaged_claim": False,
     "photo_proof_available": False, "payment_method": "upi", "country": "India"},

    # 11. Gift order (CUST-011) — store credit
    {"order_id": "ORD-1012", "customer_id": "CUST-011", "product_name": "Scented Candle Set",
     "category": "home", "price": 1299, "delivered_days_ago": 8, "status": "delivered",
     "condition_claimed": "unused", "final_sale": False, "damaged_claim": False,
     "photo_proof_available": False, "payment_method": "gift", "country": "India"},

    # 12. International order (CUST-012) — escalate / manual review
    {"order_id": "ORD-1013", "customer_id": "CUST-012", "product_name": "Designer Wallet",
     "category": "accessories", "price": 5499, "delivered_days_ago": 9, "status": "delivered",
     "condition_claimed": "unused", "final_sale": False, "damaged_claim": False,
     "photo_proof_available": False, "payment_method": "card", "country": "Singapore"},

    # 13. Cancelled order (CUST-013) — already_cancelled
    {"order_id": "ORD-1014", "customer_id": "CUST-013", "product_name": "Office Chair",
     "category": "home", "price": 6999, "delivered_days_ago": 0, "status": "cancelled",
     "condition_claimed": "unused", "final_sale": False, "damaged_claim": False,
     "photo_proof_available": False, "payment_method": "card", "country": "India"},

    # 14. Warranty confusion — defect after window (CUST-014) — warranty_support
    {"order_id": "ORD-1015", "customer_id": "CUST-014", "product_name": "Coffee Machine",
     "category": "electronics", "price": 9999, "delivered_days_ago": 60, "status": "delivered",
     "condition_claimed": "used", "final_sale": False, "damaged_claim": False,
     "photo_proof_available": False, "payment_method": "card", "country": "India"},

    # 15. Partial refund case (CUST-015) — approve (partial)
    {"order_id": "ORD-1016", "customer_id": "CUST-015", "product_name": "Bedsheet Combo (3 items)",
     "category": "home", "price": 2997, "delivered_days_ago": 12, "status": "delivered",
     "condition_claimed": "partial", "final_sale": False, "damaged_claim": False,
     "photo_proof_available": False, "payment_method": "card", "country": "India"},
]

# --- Scenario documentation ------------------------------------------------
# Maps each primary order to the assessment scenario it demonstrates and the
# decision the deterministic policy engine is expected to reach. These are for
# DEMO/ADMIN CLARITY ONLY — the agent never reads expected_decision; the policy
# engine always decides independently.
ORDER_SCENARIOS = {
    "ORD-1001": ("Normal valid refund (in window, unused)", "approved"),
    "ORD-1002": ("Secondary order (order disambiguation demo)", "approved"),
    "ORD-1003": ("Outside window + used electronics", "denied"),
    "ORD-1004": ("Outside refund window (non-electronics)", "denied"),
    "ORD-1005": ("Used product within window", "denied"),
    "ORD-1006": ("Damaged-on-arrival with photo proof", "approved"),
    "ORD-1007": ("Damaged-on-arrival without proof", "escalated"),
    "ORD-1008": ("Non-refundable final-sale item", "denied"),
    "ORD-1009": ("High-value order above ₹25,000", "escalated"),
    "ORD-1010": ("Repeat refund abuser (>3 in 90d)", "escalated"),
    "ORD-1011": ("Missing package — escalation required", "escalated"),
    "ORD-1012": ("Gift order — store credit", "store_credit"),
    "ORD-1013": ("International order — manual review", "escalated"),
    "ORD-1014": ("Cancelled order — no duplicate refund", "already_cancelled"),
    "ORD-1015": ("Warranty claim after refund window", "warranty_support"),
    "ORD-1016": ("Partial refund (multi-item order)", "approved"),
}

for _o in ORDERS:
    _label, _exp = ORDER_SCENARIOS.get(_o["order_id"], ("", ""))
    _o.setdefault("scenario_label", _label)
    _o.setdefault("expected_decision", _exp)
