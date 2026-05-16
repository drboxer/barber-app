from flask import Flask, render_template, request, redirect
import sqlite3
from flask import jsonify
from datetime import date
import os



app = Flask(__name__)

if not os.path.exists("barber.db"):
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

def to_minutes(time_str):

    h, m = map(int, time_str.split(":"))

    return h * 60 + m

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

    today = date.today().isoformat()

    conn = sqlite3.connect("barber.db")

    c = conn.cursor()

    c.execute("""
        SELECT *
        FROM appointments
        WHERE date=?
        ORDER BY start_time
    """, (today,))

    appointments = c.fetchall()
    c.execute("SELECT COUNT(*) FROM customers")

    customer_count = c.fetchone()[0]



    estimated = len(appointments) * 15
    # next appointment
    c.execute("""
            SELECT name, date, start_time, service
            FROM appointments
            ORDER BY date ASC, start_time ASC
            LIMIT 1
        """)

    next_appointment = c.fetchone()
    conn.close()

    return render_template(
        "index.html",
        appointments=appointments,
        estimated=estimated,
        next_appointment=next_appointment,
        customer_count=customer_count
    )

# ---------------- ADD ----------------
@app.route("/add", methods=["GET", "POST"])
def add():

    conn = sqlite3.connect("barber.db")
    c = conn.cursor()

    if request.method == "POST":

        name = request.form["name"]
        phone = request.form["phone"]

        date = request.form["date"]

        start_time = request.form["start_time"]

        duration = int(request.form["duration"])

        service = request.form["service"]

        # conflict check
        c.execute("""
                    SELECT start_time, duration
                    FROM appointments
                    WHERE date=?
                """, (date,))

        existing = c.fetchall()

        new_start = to_minutes(start_time)
        new_end = new_start + duration

        for appt in existing:

            existing_start = to_minutes(appt[0])
            existing_end = existing_start + appt[1]

            overlap = (
                    new_start < existing_end and
                    new_end > existing_start
            )

            if overlap:
                conn.close()

                return render_template(
                    "conflict.html",
                    start_time=start_time,
                    date=date
                )

        # check if customer exists

        c.execute(
            "SELECT id FROM customers WHERE phone=?",
            (phone,)
        )

        customer = c.fetchone()

        if not customer:
            c.execute(
                """
                INSERT INTO customers
                (name, phone, notes, created_at)
                VALUES (?, ?, ?, datetime('now'))
                """,
                (
                    name,
                    phone,
                    ""
                )
            )

            conn.commit()

        c.execute("""
            INSERT INTO appointments
            (name, phone, date, start_time, duration, service)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            name,
            phone,
            date,
            start_time,
            duration,
            service
        ))

        conn.commit()
        conn.close()

        return redirect("/calendar")

    conn.close()
    selected_time = request.args.get("time", "")
    selected_date = request.args.get("date", "")

    return render_template(
        "add.html",
        selected_time=selected_time,
        selected_date=selected_date
    )


@app.route("/calendar")
def calendar():

    conn = sqlite3.connect("barber.db")
    c = conn.cursor()

    c.execute("""
        SELECT id, name, phone, date, start_time, duration, service
        FROM appointments
        ORDER BY start_time
    """)

    appointments = c.fetchall()

    conn.close()


    def add_minutes(time_str, duration):

        h, m = map(int, time_str.split(":"))

        total = h * 60 + m + duration

        return f"{total // 60:02d}:{total % 60:02d}"


    events = []

    for a in appointments:

        end_time = add_minutes(a[4], a[5])

        color = "#3788d8"

        if a[6] == "Fade":
            color = "#ff4d4d"

        elif a[6] == "Ξύρισμα":
            color = "#222222"

        elif a[6] == "Παιδικό":
            color = "#4CAF50"

        start_datetime = f"{a[3]}T{a[4]}"
        end_datetime = f"{a[3]}T{end_time}"

        events.append({

            "id": a[0],

            "title": f"{a[1]} - {a[6]}",

            "start": start_datetime,

            "end": end_datetime,

            "backgroundColor": color,

            "borderColor": color

        })

    return render_template(
        "calendar.html",
        events=events
    )

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):

    conn = sqlite3.connect("barber.db")
    c = conn.cursor()

    if request.method == "POST":

        name = request.form["name"]
        phone = request.form["phone"]
        date = request.form["date"]
        start_time = request.form["start_time"]
        duration = int(request.form["duration"])
        service = request.form["service"]

        c.execute("""
            UPDATE appointments
            SET name=?, phone=?, date=?, start_time=?, duration=?, service=?
            WHERE id=?
        """, (name, phone, date, start_time, duration, service, id))

        conn.commit()
        conn.close()

        return redirect("/calendar")

    c.execute("""
        SELECT id, name, phone, date, start_time, duration, service
        FROM appointments
        WHERE id=?
    """, (id,))

    appointment = c.fetchone()

    conn.close()

    return render_template("edit.html", appointment=appointment)

@app.route("/delete/<int:id>")
def delete(id):

    conn = sqlite3.connect("barber.db")
    c = conn.cursor()

    c.execute("DELETE FROM appointments WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect("/calendar")

@app.route("/move_appointment", methods=["POST"])
def move_appointment():

    data = request.get_json()

    appointment_id = data["id"]
    new_time = data["start_time"]

    conn = sqlite3.connect("barber.db")
    c = conn.cursor()

    c.execute("""
        UPDATE appointments
        SET start_time=?
        WHERE id=?
    """, (new_time, appointment_id))

    conn.commit()
    conn.close()

    return jsonify({"success": True})

@app.route("/resize_appointment", methods=["POST"])
def resize_appointment():

    data = request.get_json()

    appointment_id = data["id"]
    duration = int(data["duration"])

    conn = sqlite3.connect("barber.db")
    c = conn.cursor()

    c.execute("""
        UPDATE appointments
        SET duration=?
        WHERE id=?
    """, (duration, appointment_id))

    conn.commit()
    conn.close()

    return jsonify({"success": True})


@app.route("/customers")
def customers():

    conn = sqlite3.connect("barber.db")

    c = conn.cursor()

    c.execute("""
        SELECT *
        FROM customers
        ORDER BY name
    """)

    customers = c.fetchall()

    conn.close()

    return render_template(
        "customers.html",
        customers=customers
    )

@app.route("/customer/<int:id>")
def customer(id):

    conn = sqlite3.connect("barber.db")

    c = conn.cursor()

    c.execute(
        "SELECT * FROM customers WHERE id=?",
        (id,)
    )

    customer = c.fetchone()

    c.execute(
        """
        SELECT *
        FROM appointments
        WHERE phone=?
        ORDER BY date DESC, start_time DESC
        """,
        (customer[2],)
    )

    appointments = c.fetchall()

    conn.close()

    return render_template(
        "customer.html",
        customer=customer,
        appointments=appointments
    )

@app.route("/update_customer/<int:id>", methods=["POST"])
def update_customer(id):

    notes = request.form["notes"]

    conn = sqlite3.connect("barber.db")

    c = conn.cursor()

    c.execute(
        "UPDATE customers SET notes=? WHERE id=?",
        (notes, id)
    )

    conn.commit()
    conn.close()

    return redirect(f"/customer/{id}")

@app.route("/delete_customer/<int:id>")
def delete_customer(id):

    conn = sqlite3.connect("barber.db")

    c = conn.cursor()

    c.execute(
        "DELETE FROM customers WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/customers")

@app.route("/search_customer")
def search_customer():

    phone = request.args.get("phone")

    conn = sqlite3.connect("barber.db")

    c = conn.cursor()

    c.execute(
        """
        SELECT name, phone
        FROM customers
        WHERE phone LIKE ?
        LIMIT 1
        """,
        (phone + "%",)
    )

    customer = c.fetchone()

    conn.close()

    if customer:

        return {
            "name": customer[0],
            "phone": customer[1]
        }

    return jsonify({})

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)