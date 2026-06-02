"""
Namibia EXPRESS ATM System - Database Module
Handles account storage, retrieval, and persistence using JSON. 
"""

import json
import os
import hashlib
import uuid
from datetime import datetime
from typing import Optional, Dict, List

DB_FILE = "atm_data.json"


def hash_pin(pin: str) -> str:
    """Securely hash a PIN using SHA-256."""
    return hashlib.sha256(pin.encode()).hexdigest()


def load_database() -> Dict:
    """Load the database from file, or create a fresh one."""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {"accounts": {}, "cards": {}}


def save_database(db: Dict) -> None:
    """Persist the database to file."""
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=4)


def generate_account_number() -> str:
    """Generate a unique 10-digit account number."""
    return str(uuid.uuid4().int)[:10]


def generate_card_number() -> str:
    """Generate a unique 16-digit card number."""
    return str(uuid.uuid4().int)[:16]


def seed_demo_accounts() -> None:
    """Seed the database with demo accounts for testing."""
    db = load_database()
    if db["accounts"]:
        return  # Already seeded

    demo_accounts = [
        {
            "name": "Josua Uuyuni",
            "card_number": "1234567890123456",
            "pin": "1234",
            "balance": 5000.00,
        },
        {
            "name": "Lydia Uuyuni",
            "card_number": "9876543210987654",
            "pin": "5678",
            "balance": 12500.50,
        },
        {
            "name": "Eva Uuyuni",
            "card_number": "1111222233334444",
            "pin": "9999",
            "balance": 250.00,
        },
        {
            "name": "Pendu Uuyuni",
            "card_number": "5555666677778888",
            "pin": "4321",
            "balance": 8750.00,
        },
        {
            "name": "Betuel Uuyuni",
            "card_number": "9999000011112222",
            "pin": "7777",
            "balance": 3200.00,
        },
    ]

    for acc in demo_accounts:
        account_number = generate_account_number()
        card_num = acc["card_number"]
        db["accounts"][account_number] = {
            "account_number": account_number,
            "name": acc["name"],
            "card_number": card_num,
            "pin_hash": hash_pin(acc["pin"]),
            "balance": acc["balance"],
            "transactions": [
                {
                    "id": str(uuid.uuid4()),
                    "type": "Account Opened",
                    "amount": acc["balance"],
                    "balance_after": acc["balance"],
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "description": "Initial deposit",
                }
            ],
            "is_locked": False,
            "failed_attempts": 0,
        }
        db["cards"][card_num] = account_number

    save_database(db)
    print("  ✅ Demo accounts seeded successfully.")


# ─── Account Operations ────────────────────────────────────────────────────────

def create_account(name: str, pin: str, initial_deposit: float = 0.0) -> Dict:
    """Create a new bank account."""
    db = load_database()
    account_number = generate_account_number()
    card_number = generate_card_number()

    account = {
        "account_number": account_number,
        "name": name,
        "card_number": card_number,
        "pin_hash": hash_pin(pin),
        "balance": initial_deposit,
        "transactions": [],
        "is_locked": False,
        "failed_attempts": 0,
    }

    if initial_deposit > 0:
        account["transactions"].append({
            "id": str(uuid.uuid4()),
            "type": "Deposit",
            "amount": initial_deposit,
            "balance_after": initial_deposit,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "description": "Initial deposit",
        })

    db["accounts"][account_number] = account
    db["cards"][card_number] = account_number
    save_database(db)
    return account


def get_account_by_card(card_number: str) -> Optional[Dict]:
    """Fetch account details using a card number."""
    db = load_database()
    account_number = db["cards"].get(card_number)
    if account_number:
        return db["accounts"].get(account_number)
    return None


def get_account(account_number: str) -> Optional[Dict]:
    """Fetch account details using an account number."""
    db = load_database()
    return db["accounts"].get(account_number)


def verify_pin(card_number: str, pin: str) -> Optional[Dict]:
    """Verify PIN and return account if correct, handling lockout logic."""
    db = load_database()
    account_number = db["cards"].get(card_number)
    if not account_number:
        return None

    account = db["accounts"][account_number]

    if account["is_locked"]:
        return "LOCKED"

    if account["pin_hash"] == hash_pin(pin):
        account["failed_attempts"] = 0
        db["accounts"][account_number] = account
        save_database(db)
        return account
    else:
        account["failed_attempts"] += 1
        if account["failed_attempts"] >= 3:
            account["is_locked"] = True
        db["accounts"][account_number] = account
        save_database(db)
        remaining = max(0, 3 - account["failed_attempts"])
        return {"error": "wrong_pin", "remaining": remaining}


def deposit(account_number: str, amount: float, description: str = "ATM Deposit") -> Dict:
    """Deposit funds into an account."""
    db = load_database()
    account = db["accounts"][account_number]
    account["balance"] += amount
    txn = {
        "id": str(uuid.uuid4()),
        "type": "Deposit",
        "amount": amount,
        "balance_after": account["balance"],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "description": description,
    }
    account["transactions"].append(txn)
    db["accounts"][account_number] = account
    save_database(db)
    return {"success": True, "balance": account["balance"], "transaction": txn}


def withdraw(account_number: str, amount: float, description: str = "ATM Withdrawal") -> Dict:
    """Withdraw funds from an account."""
    db = load_database()
    account = db["accounts"][account_number]

    if amount > account["balance"]:
        return {"success": False, "error": "Insufficient funds"}
    if amount <= 0:
        return {"success": False, "error": "Invalid amount"}

    account["balance"] -= amount
    txn = {
        "id": str(uuid.uuid4()),
        "type": "Withdrawal",
        "amount": amount,
        "balance_after": account["balance"],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "description": description,
    }
    account["transactions"].append(txn)
    db["accounts"][account_number] = account
    save_database(db)
    return {"success": True, "balance": account["balance"], "transaction": txn}


def transfer(from_account_number: str, to_card_number: str, amount: float) -> Dict:
    """Transfer funds between two accounts."""
    db = load_database()
    from_account = db["accounts"].get(from_account_number)

    to_account_number = db["cards"].get(to_card_number)
    if not to_account_number:
        return {"success": False, "error": "Recipient card not found"}

    to_account = db["accounts"].get(to_account_number)
    if not to_account:
        return {"success": False, "error": "Recipient account not found"}
    if from_account_number == to_account_number:
        return {"success": False, "error": "Cannot transfer to your own account"}
    if amount > from_account["balance"]:
        return {"success": False, "error": "Insufficient funds"}
    if amount <= 0:
        return {"success": False, "error": "Invalid amount"}

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    txn_id = str(uuid.uuid4())

    from_account["balance"] -= amount
    from_account["transactions"].append({
        "id": txn_id,
        "type": "Transfer Out",
        "amount": amount,
        "balance_after": from_account["balance"],
        "timestamp": timestamp,
        "description": f"Transfer to {to_account['name']}",
    })

    to_account["balance"] += amount
    to_account["transactions"].append({
        "id": txn_id,
        "type": "Transfer In",
        "amount": amount,
        "balance_after": to_account["balance"],
        "timestamp": timestamp,
        "description": f"Transfer from {from_account['name']}",
    })

    db["accounts"][from_account_number] = from_account
    db["accounts"][to_account_number] = to_account
    save_database(db)
    return {
        "success": True,
        "balance": from_account["balance"],
        "recipient_name": to_account["name"],
    }


def change_pin(account_number: str, new_pin: str) -> bool:
    """Change the PIN for an account."""
    db = load_database()
    account = db["accounts"].get(account_number)
    if not account:
        return False
    account["pin_hash"] = hash_pin(new_pin)
    db["accounts"][account_number] = account
    save_database(db)
    return True


def get_transactions(account_number: str, limit: int = 10) -> List[Dict]:
    """Return the last N transactions for an account."""
    db = load_database()
    account = db["accounts"].get(account_number)
    if not account:
        return []
    return list(reversed(account["transactions"]))[:limit]


def unlock_account(account_number: str) -> bool:
    """Admin unlock a locked account."""
    db = load_database()
    account = db["accounts"].get(account_number)
    if not account:
        return False
    account["is_locked"] = False
    account["failed_attempts"] = 0
    db["accounts"][account_number] = account
    save_database(db)
    return True
