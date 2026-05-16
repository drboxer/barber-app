import sqlite3

conn = sqlite3.connect("barber.db")

c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS customers (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    name TEXT,

    phone TEXT UNIQUE,

    notes TEXT,

    created_at TEXT
)
""")

conn.commit()
conn.close()

print("Customers table created.")