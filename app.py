from flask import Flask, render_template, request, redirect
import sqlite3
from flask import jsonify
from datetime import date
import os
from flask import flash
from flask import session
import csv
from flask import Response
from datetime import datetime
import io

today = datetime.now().strftime("%Y-%m-%d")
current_time = datetime.now().strftime("%H:%M")
SERVICE_PRICES = {

    "Fade": 18,

    "Ξύρισμα": 10,

    "Παιδικό": 12,

    "Κούρεμα" : 10
}



app = Flask(__name__)

app.secret_key = "supersecretkey"

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
    CREATE TABLE IF NOT EXISTS customers (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        name TEXT,

        phone TEXT UNIQUE,

        notes TEXT,

        created_at TEXT

    )
    """)

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

    try:

        c.execute("""
        ALTER TABLE appointments
        ADD COLUMN status TEXT
        DEFAULT 'scheduled'
        """)

    except sqlite3.OperationalError:

        pass

    try:

        c.execute("""
        ALTER TABLE appointments
        ADD COLUMN price INTEGER
        """)

    except sqlite3.OperationalError:
        pass

    conn.commit()

    conn.close()


init_db()


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if (
            username == "admin" and
            password == "1234"
        ):

            session["logged_in"] = True

            return redirect("/")

    return render_template("login.html")

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")

# ---------------- HOME ----------------
@app.route("/")
def index():
    # if not session.get("logged_in"):
    #     return redirect("/login")

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


    # next appointment
    c.execute("""

    SELECT name, date, start_time, service

    FROM appointments

    WHERE status='scheduled'

    AND (
        date > ?
        OR (date = ? AND start_time >= ?)
    )

    ORDER BY date ASC, start_time ASC

    LIMIT 1

    """, (today, today, current_time))

    next_appointment = c.fetchone()

    c.execute("""
        SELECT start_time, name, service
        FROM appointments
        WHERE date = ?
        AND start_time >= ?
        ORDER BY start_time ASC
    """, (today, current_time))

    today_timeline = c.fetchall()


    # conn = sqlite3.connect("barber.db")
    # c = conn.cursor()
    c.execute("""
    SELECT COUNT(*)

    FROM appointments

    WHERE status='completed'
    AND date=?
    """, (today,))

    completed_today = c.fetchone()[0]

    c.execute("""
    SELECT SUM(price)

    FROM appointments

    WHERE status='completed'
    AND date=?
    """, (today,))

    today_revenue = c.fetchone()[0] or 0

    c.execute("""
    SELECT SUM(price)

    FROM appointments

    WHERE status='completed'
    AND strftime('%Y-%m', date)=strftime('%Y-%m','now')
    """)

    month_revenue = c.fetchone()[0] or 0

    c.execute("""
    SELECT COUNT(*)
    FROM appointments
    WHERE status='scheduled'
    """)

    upcoming = c.fetchone()[0]
    c.execute("""
    SELECT COUNT(*)
    FROM appointments
    WHERE status='cancelled'
    """)

    cancelled = c.fetchone()[0]


    conn.close()


    return render_template(
        "index.html",
        appointments=appointments,
        next_appointment=next_appointment,
        customer_count=customer_count,
        today_timeline=today_timeline,
        upcoming=upcoming,
        cancelled=cancelled,
        today_revenue=today_revenue,
        completed_today=completed_today,
        month_revenue=month_revenue
    )

# ---------------- ADD ----------------
@app.route("/add", methods=["GET", "POST"])
def add():
    # if not session.get("logged_in"):
    #     return redirect("/login")

    conn = sqlite3.connect("barber.db")
    c = conn.cursor()

    if request.method == "POST":

        name = request.form["name"]
        phone = request.form["phone"]

        date = request.form["date"]

        start_time = request.form["start_time"]

        duration = int(request.form["duration"])

        service = request.form["service"]

        price = SERVICE_PRICES.get(service, 0)


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


        else:

            c.execute("""
                SELECT notes
                FROM customers
                WHERE phone=?
            """, (phone,))

            notes = c.fetchone()[0]



        c.execute("""
            INSERT INTO appointments
            (name, phone, date, start_time, duration, service, price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            phone,
            date,
            start_time,
            duration,
            service,
            price
        ))

        # c.execute("""
        # SELECT SUM(price)
        # FROM appointments
        # WHERE status='completed'
        # """)
        #
        # revenue = c.fetchone()[0] or 0
        # print(revenue)

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
    # if not session.get("logged_in"):
    #     return redirect("/login")

    conn = sqlite3.connect("barber.db")
    c = conn.cursor()

    c.execute("""
        SELECT id, name, phone, date, start_time, duration, service, status, price
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

        status = a[7]

        if status == "completed":
            color = "#2ecc71"

        elif status == "cancelled":
            color = "#e74c3c"

        elif status == "no_show":
            color = "#95a5a6"

        else:
            color = "#3788d8"

        start_datetime = f"{a[3]}T{a[4]}"
        end_datetime = f"{a[3]}T{end_time}"

        events.append({
            "id": a[0],
            "title": f"{a[1]} • {a[6]} • €{a[8]}",
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
    # if not session.get("logged_in"):
    #     return redirect("/login")

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
    # if not session.get("logged_in"):
    #     return redirect("/login")

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
    # if not session.get("logged_in"):
    #     return redirect("/login")

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

@app.route(
"/customer/<int:id>",
methods=["GET","POST"]
)
def customer_profile(id):

    conn = sqlite3.connect("barber.db")
    c = conn.cursor()

    if request.method == "POST":

        notes = request.form["notes"]

        c.execute("""
        UPDATE customers
        SET notes=?
        WHERE id=?
        """, (notes, id))

        conn.commit()

    c.execute("""
    SELECT *
    FROM customers
    WHERE id=?
    """, (id,))

    customer = c.fetchone()

    phone = customer[2]

    c.execute("""
    SELECT
        date,
        start_time,
        service,
        status

    FROM appointments

    WHERE phone=?

    ORDER BY date DESC
    """, (phone,))

    appointments = c.fetchall()

    c.execute("""
    SELECT
    COUNT(*),
    MAX(date)

    FROM appointments

    WHERE phone=?
    AND status='completed'
    """, (phone,))

    stats = c.fetchone()
    visits = stats[0]
    last_visit = stats[1]

    c.execute("""
    SELECT service

    FROM appointments

    WHERE phone=?

    GROUP BY service

    ORDER BY COUNT(*) DESC

    LIMIT 1
    """, (phone,))
    fav = c.fetchone()

    favorite = fav[0] if fav else "-"

    c.execute("""
    SELECT
    date,
    start_time,
    service

    FROM appointments

    WHERE phone=?
    AND status='scheduled'

    ORDER BY date,start_time

    LIMIT 1
    """, (phone,))

    next_appointment = c.fetchone()

    conn.close()

    return render_template(
        "customer.html",
        customer=customer,
        appointments=appointments,
        visits=visits,
        last_visit=last_visit,
        favorite=favorite,
        next_appointment=next_appointment
    )

@app.route("/update_customer/<int:id>", methods=["POST"])
def update_customer(id):
    if not session.get("logged_in"):
        return redirect("/login")

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
    # if not session.get("logged_in"):
    #     return redirect("/login")

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
        SELECT name, phone, notes
        FROM customers
        WHERE phone LIKE ?
        LIMIT 1
        """,
        (phone + "%",)
    )

    customer = c.fetchone()

    conn.close()

    if customer:
        return jsonify({
            "name": customer[0],
            "phone": customer[1],
            "notes": customer[2]
        })

    return jsonify({})

@app.route("/export_customers")
def export_customers():

    conn = sqlite3.connect("barber.db")
    c = conn.cursor()

    c.execute("""
        SELECT name, phone, notes, created_at
        FROM customers
        ORDER BY name
    """)

    customers = c.fetchall()

    conn.close()

    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow([
        "Name",
        "Phone",
        "Notes",
        "Created At"
    ])

    writer.writerows(customers)

    csv_data = output.getvalue()

    output.close()

    return Response(
        csv_data,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition":
            "attachment; filename=customers.csv"
        }
    )

@app.route("/appointment/<int:id>/status", methods=["POST"])
def update_status(id):

    data = request.get_json()
    status = data["status"]

    conn = sqlite3.connect("barber.db")
    c = conn.cursor()

    c.execute("""
        UPDATE appointments
        SET status = ?
        WHERE id = ?
    """, (status, id))

    conn.commit()
    conn.close()

    return {"ok": True}

@app.route("/analytics")
def analytics():

    conn = sqlite3.connect("barber.db")
    c = conn.cursor()
    c.execute("""

        SELECT
        date,
        SUM(COALESCE(price,0))

        FROM appointments

        WHERE status='completed'

        GROUP BY date

        ORDER BY date ASC

        LIMIT 7

        """)

    chart_data = c.fetchall()
    chart_labels = []
    chart_values = []

    for row in chart_data:
        chart_labels.append(row[0])

        chart_values.append(row[1])

    c.execute("""

        SELECT
        service,
        COUNT(*)

        FROM appointments

        GROUP BY service

        ORDER BY COUNT(*) DESC

        LIMIT 5

        """)

    top_services = c.fetchall()

    c.execute("""

       SELECT

       name,
       SUM(price) as total

       FROM appointments

       WHERE status='completed'

       GROUP BY phone

       ORDER BY total DESC

       LIMIT 5

       """)

    top_customers = c.fetchall()

    c.execute("""

       SELECT

       name,
       COUNT(*) as visits

       FROM appointments

       GROUP BY phone

       ORDER BY visits DESC

       LIMIT 5

       """)

    loyal_customers = c.fetchall()

    conn.close()

    return render_template(

        "analytics.html",

        chart_labels=chart_labels,
        chart_values=chart_values,
        top_services=top_services,
        top_customers=top_customers,
        loyal_customers=loyal_customers
    )


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)