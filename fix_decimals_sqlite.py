import sqlite3

conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

fields = ['cost_per_sack', 'total_cost', 'amount_paid', 'amount_change']
for field in fields:
    cursor.execute(f"""
        UPDATE webapp_customerorder
        SET {field} = 0.00
        WHERE {field} IS NULL OR TRIM({field}) = '';
    """)
    print(f"Fixed empty values in {field}")

conn.commit()
conn.close()
print("Done fixing decimal fields.")
