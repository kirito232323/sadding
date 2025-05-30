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

if __name__ == "__main__":
    list_all_tables()
    inspect_webapp_customerorder_table()
