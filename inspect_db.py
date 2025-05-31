import sqlite3

# Connect to the SQLite database
def inspect_customerorder_table():
    try:
        conn = sqlite3.connect('db.sqlite3')
        cursor = conn.cursor()

        # Check the schema of the CustomerOrder table
        cursor.execute("PRAGMA table_info('CustomerOrder')")
        columns = cursor.fetchall()

        if columns:
            print("CustomerOrder table schema:")
            for column in columns:
                print(column)
        else:
            print("CustomerOrder table does not exist.")

        conn.close()
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")

def inspect_webapp_customerorder_table():
    try:
        conn = sqlite3.connect('db.sqlite3')
        cursor = conn.cursor()

        # Check the schema of the webapp_customerorder table
        cursor.execute("PRAGMA table_info('webapp_customerorder')")
        columns = cursor.fetchall()

        if columns:
            print("webapp_customerorder table schema:")
            for column in columns:
                print(column)
        else:
            print("webapp_customerorder table does not exist.")

        conn.close()
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")

def list_all_tables():
    try:
        conn = sqlite3.connect('db.sqlite3')
        cursor = conn.cursor()

        # List all tables in the database
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        if tables:
            print("Tables in the database:")
            for table in tables:
                print(table[0])
        else:
            print("No tables found in the database.")

        conn.close()
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")

def find_invalid_decimals():
    conn = sqlite3.connect('db.sqlite3')
    c = conn.cursor()
    FIELDS = ['cost_per_sack', 'total_cost', 'amount_paid', 'amount_change', 'discount']
    print('\n--- Checking for invalid decimal values in webapp_customerorder ---')
    for field in FIELDS:
        print(f'Checking field: {field}')
        c.execute(f"SELECT order_id, {field} FROM webapp_customerorder")
        for row_id, value in c.fetchall():
            try:
                if value is None or value == '' or str(value).strip() == '':
                    print(f'  order_id={row_id}: EMPTY')
                else:
                    float(value)
            except Exception:
                print(f'  order_id={row_id}: INVALID VALUE: {value!r}')
            else:
                print(f'  order_id={row_id}: {value!r}')
    conn.close()

if __name__ == "__main__":
    list_all_tables()
    inspect_webapp_customerorder_table()
    find_invalid_decimals()
