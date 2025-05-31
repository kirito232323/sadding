import sqlite3
from decimal import Decimal, InvalidOperation

DB_PATH = 'db.sqlite3'
TABLE = 'webapp_customerorder'
FIELDS = ['cost_per_sack', 'total_cost', 'amount_paid', 'amount_change']

def is_valid_decimal(val):
    try:
        Decimal(str(val))
        return True
    except (InvalidOperation, TypeError, ValueError):
        return False

def is_valid_and_in_range(val, max_digits=10, decimal_places=2):
    try:
        d = Decimal(str(val))
        # max allowed value for max_digits=10, decimal_places=2 is 99999999.99
        max_val = Decimal('9' * (max_digits - decimal_places)) + Decimal('0.' + '9' * decimal_places)
        min_val = -max_val
        if d > max_val or d < min_val:
            return False
        # check decimal places
        if abs(d.as_tuple().exponent) > decimal_places:
            return False
        return True
    except (InvalidOperation, TypeError, ValueError):
        return False

def fix_invalid_decimals():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    total_fixed = 0
    # Field configs: (field, max_digits, decimal_places)
    field_configs = [
        ('cost_per_sack', 10, 2),
        ('total_cost', 10, 2),
        ('amount_paid', 10, 2),
        ('amount_change', 10, 2),
        ('discount', 5, 2),
    ]
    for field, max_digits, decimal_places in field_configs:
        c.execute(f"SELECT order_id, {field} FROM {TABLE}")
        rows = c.fetchall()
        for row_id, value in rows:
            if not is_valid_and_in_range(value, max_digits, decimal_places):
                print(f"Order id {row_id}: {field} is invalid or out of range ({value}). Setting to 0.00")
                c.execute(f"UPDATE {TABLE} SET {field} = ? WHERE order_id = ?", ("0.00", row_id))
                total_fixed += 1
    conn.commit()
    conn.close()
    print(f"Fixed {total_fixed} invalid or out-of-range decimal values.")

if __name__ == "__main__":
    fix_invalid_decimals()
