import sqlite3

# Connect to (or create) the database



def create_stock_changes_table():
    conn = sqlite3.connect('my_inventory.db')
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_changes (
            change_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            product_name TEXT,
            action TEXT,
            change_detail TEXT,
            change_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# Call this function at the start of app
create_stock_changes_table()
