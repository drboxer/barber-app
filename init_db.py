import sqlite3

conn = sqlite3.connect("barber.db")

c = conn.cursor()

c.execute("""
CREATE TABLE appointments (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    name TEXT,

    phone TEXT,

    date TEXT,

    start_time TEXT,

    duration INTEGER,

    service TEXT
)
""")

conn.commit()

conn.close()

print("Database created successfully.")