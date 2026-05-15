from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

# ---------------- DB ----------------
def init_db():
    conn = sqlite3.connect("barber.db")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            phone TEXT,
            start_time TEXT,
            duration INTEGER,
            service TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- HOME ----------------
@app.route("/")
def index():
    conn = sqlite3.connect("barber.db")
    c = conn.cursor()

    c.execute("""
        SELECT id, name, phone, start_time, duration, service
        FROM appointments
        ORDER BY start_time
    """)

    appointments = c.fetchall()
    conn.close()

    return render_template("index.html", appointments=appointments)


# ---------------- ADD ----------------
@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        name = request.form["name"]
        phone = request.form["phone"]
        start_time = request.form["start_time"]
        duration = int(request.form["duration"])
        service = request.form["service"]

        conn = sqlite3.connect("barber.db")
        c = conn.cursor()

        # ⛔ conflict check (overlap)
        c.execute("SELECT start_time, duration FROM appointments")
        existing = c.fetchall()

        def to_minutes(t):
            h, m = map(int, t.split(":"))
            return h * 60 + m

        new_start = to_minutes(start_time)
        new_end = new_start + duration

        for s, d in existing:
            ex_start = to_minutes(s)
            ex_end = ex_start + d

            if not (new_end <= ex_start or new_start >= ex_end):
                conn.close()
                return "❌ Αυτή η ώρα είναι κλεισμένη"

        c.execute("""
            INSERT INTO appointments (name, phone, start_time, duration, service)
            VALUES (?, ?, ?, ?, ?)
        """, (name, phone, start_time, duration, service))

        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("add.html")


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)