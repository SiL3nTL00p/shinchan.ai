"""
generate_dataset.py - Synthetic Transaction Dataset Generator

Generates a realistic 250k-row digital payment transaction dataset
for InsightX development and testing.

Usage: python generate_dataset.py
"""

import csv
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Tuple

# Seed for reproducibility
random.seed(42)

# ─────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────
NUM_ROWS = 250_000
OUTPUT_FILE = "250k_transactions.csv"

TRANSACTION_TYPES = ["P2P", "P2M", "Bill Payment", "Recharge"]
TRANSACTION_TYPE_WEIGHTS = [0.35, 0.30, 0.20, 0.15]

MERCHANT_CATEGORIES = [
    "Food Delivery", "Grocery", "Electronics", "Fashion", "Pharmacy",
    "Fuel", "Entertainment", "Travel", "Education", "Utility",
    "Restaurant", "Shopping Mall",
]

AGE_GROUPS = ["18-25", "26-35", "36-45", "46-55", "56+"]
AGE_GROUP_WEIGHTS = [0.25, 0.35, 0.20, 0.12, 0.08]

STATES = [
    "Maharashtra", "Karnataka", "Delhi", "Tamil Nadu", "Uttar Pradesh",
    "Gujarat", "Rajasthan", "West Bengal", "Telangana", "Kerala",
    "Madhya Pradesh", "Andhra Pradesh", "Bihar", "Punjab", "Haryana",
]

BANKS = [
    "SBI", "HDFC Bank", "ICICI Bank", "Axis Bank", "Kotak Mahindra",
    "Punjab National Bank", "Bank of Baroda", "Canara Bank",
    "Union Bank", "IndusInd Bank", "Yes Bank", "IDFC First Bank",
]

DEVICE_TYPES = ["Android", "iOS", "Web"]
DEVICE_WEIGHTS = [0.65, 0.25, 0.10]

NETWORK_TYPES = ["4G", "WiFi", "5G", "3G"]
NETWORK_WEIGHTS = [0.45, 0.25, 0.20, 0.10]

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# ─────────────────────────────────────────────────────────
# Failure Rate Configuration (by type & conditions)
# ─────────────────────────────────────────────────────────
BASE_FAILURE_RATES = {
    "P2P": 0.025,           # 2.5% base
    "P2M": 0.035,           # 3.5% base
    "Bill Payment": 0.080,  # 8.0% base (external dependency)
    "Recharge": 0.060,      # 6.0% base (external dependency)
}

# Failure rate multipliers
NETWORK_FAILURE_MULTIPLIER = {
    "3G": 2.5,    # Much higher failures on 3G
    "4G": 1.0,
    "5G": 0.8,
    "WiFi": 0.7,
}

WEEKEND_FAILURE_MULTIPLIER = 1.8  # Weekend maintenance effect
PEAK_HOUR_FAILURE_MULTIPLIER = 1.5  # Peak hours: 18-21


def generate_timestamp() -> Tuple[datetime, int, str, int]:
    """Generate a random timestamp within the last 90 days."""
    base_date = datetime(2025, 12, 1)
    offset_seconds = random.randint(0, 90 * 24 * 3600)
    ts = base_date + timedelta(seconds=offset_seconds)

    hour = ts.hour
    day_name = DAYS_OF_WEEK[ts.weekday()]
    is_weekend = 1 if ts.weekday() >= 5 else 0

    return ts, hour, day_name, is_weekend


def calculate_failure(
    txn_type: str, network: str, hour: int, is_weekend: int
) -> str:
    """Determine if transaction fails based on contextual factors."""
    rate = BASE_FAILURE_RATES[txn_type]

    # Network effect
    rate *= NETWORK_FAILURE_MULTIPLIER.get(network, 1.0)

    # Weekend maintenance window effect
    if is_weekend:
        rate *= WEEKEND_FAILURE_MULTIPLIER
        # Extra spike during 2-6 AM (maintenance windows)
        if 2 <= hour <= 6:
            rate *= 1.5

    # Peak hour effect (18-21)
    if 18 <= hour <= 21:
        rate *= PEAK_HOUR_FAILURE_MULTIPLIER

    return "FAILED" if random.random() < rate else "SUCCESS"


def generate_amount(txn_type: str) -> float:
    """Generate realistic transaction amount based on type."""
    if txn_type == "P2P":
        # P2P: wide range, skewed toward smaller amounts
        return round(random.lognormvariate(6.5, 1.2), 2)  # median ~665
    elif txn_type == "P2M":
        # Merchant: typical retail amounts
        return round(random.lognormvariate(5.8, 1.0), 2)  # median ~330
    elif txn_type == "Bill Payment":
        # Bills: utility-sized amounts
        return round(random.lognormvariate(6.8, 0.8), 2)  # median ~898
    else:  # Recharge
        # Recharges: specific denominations
        denominations = [49, 99, 149, 199, 249, 299, 399, 499, 599, 699, 799, 999, 1299, 1999, 2999]
        return float(random.choice(denominations))


def generate_fraud_flag(amount: float, txn_type: str, status: str) -> int:
    """
    Generate fraud flag (flagged for review, NOT confirmed fraud).
    Higher-value transactions and failed ones are more likely to be flagged.
    """
    base_rate = 0.02  # 2% base flag rate

    # Higher amounts get flagged more
    if amount > 5000:
        base_rate *= 2.0
    if amount > 10000:
        base_rate *= 2.5
    if amount > 50000:
        base_rate *= 3.0

    # Failed transactions have slightly higher flag rate
    if status == "FAILED":
        base_rate *= 1.3

    # P2P has slightly higher review rate
    if txn_type == "P2P":
        base_rate *= 1.2

    return 1 if random.random() < base_rate else 0


def generate_row(row_num: int) -> dict:
    """Generate a single transaction row."""
    # Transaction type
    txn_type = random.choices(TRANSACTION_TYPES, weights=TRANSACTION_TYPE_WEIGHTS)[0]

    # Timestamp
    ts, hour, day_name, is_weekend = generate_timestamp()

    # Demographics
    sender_age = random.choices(AGE_GROUPS, weights=AGE_GROUP_WEIGHTS)[0]
    sender_state = random.choice(STATES)
    sender_bank = random.choice(BANKS)
    receiver_bank = random.choice(BANKS)

    # Device & Network
    device = random.choices(DEVICE_TYPES, weights=DEVICE_WEIGHTS)[0]
    network = random.choices(NETWORK_TYPES, weights=NETWORK_WEIGHTS)[0]

    # Merchant category (NULL for P2P)
    merchant_cat = None if txn_type == "P2P" else random.choice(MERCHANT_CATEGORIES)

    # Receiver age group (only for P2P)
    receiver_age = random.choices(AGE_GROUPS, weights=AGE_GROUP_WEIGHTS)[0] if txn_type == "P2P" else None

    # Amount
    amount = generate_amount(txn_type)

    # Status (context-aware failure)
    status = calculate_failure(txn_type, network, hour, is_weekend)

    # Fraud flag
    fraud = generate_fraud_flag(amount, txn_type, status)

    return {
        "transaction_id": f"TXN{row_num:08d}",
        "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "transaction_type": txn_type,
        "merchant_category": merchant_cat or "",
        "amount_inr": amount,
        "transaction_status": status,
        "sender_age_group": sender_age,
        "receiver_age_group": receiver_age or "",
        "sender_state": sender_state,
        "sender_bank": sender_bank,
        "receiver_bank": receiver_bank,
        "device_type": device,
        "network_type": network,
        "fraud_flag": fraud,
        "hour_of_day": hour,
        "day_of_week": day_name,
        "is_weekend": is_weekend,
    }


def main():
    """Generate the full dataset."""
    print(f"Generating {NUM_ROWS:,} synthetic transactions...")

    fieldnames = [
        "transaction_id", "timestamp", "transaction_type", "merchant_category",
        "amount_inr", "transaction_status", "sender_age_group", "receiver_age_group",
        "sender_state", "sender_bank", "receiver_bank", "device_type",
        "network_type", "fraud_flag", "hour_of_day", "day_of_week", "is_weekend",
    ]

    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i in range(1, NUM_ROWS + 1):
            row = generate_row(i)
            writer.writerow(row)

            if i % 50000 == 0:
                print(f"  Generated {i:,} / {NUM_ROWS:,} rows...")

    print(f"\nDataset saved to: {OUTPUT_FILE}")

    # Print summary statistics
    print("\n── Summary ──")
    print(f"Total rows: {NUM_ROWS:,}")

    # Quick validation
    import pandas as pd
    df = pd.read_csv(OUTPUT_FILE)
    print(f"File size: {os.path.getsize(OUTPUT_FILE) / 1024 / 1024:.1f} MB")
    print(f"\nTransaction types:\n{df['transaction_type'].value_counts().to_string()}")
    print(f"\nStatus breakdown:\n{df['transaction_status'].value_counts().to_string()}")
    print(f"\nOverall failure rate: {(df['transaction_status'] == 'FAILED').mean() * 100:.1f}%")
    print(f"Fraud flag rate: {df['fraud_flag'].mean() * 100:.1f}%")
    print(f"\nDevice types:\n{df['device_type'].value_counts().to_string()}")
    print(f"\nNetwork types:\n{df['network_type'].value_counts().to_string()}")
    print(f"\nAmount stats:\n{df['amount_inr'].describe().to_string()}")
    print(f"\nNull merchant_category (should be ~P2P count): {df['merchant_category'].isna().sum() + (df['merchant_category'] == '').sum()}")


import os

if __name__ == "__main__":
    main()
