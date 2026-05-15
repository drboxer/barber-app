from flask import Flask, render_template, request, redirect
import sqlite3
from flask import jsonify

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

    selected_time = request.args.get("time", "")
    return render_template("add.html", selected_time=selected_time)

@app.route("/calendar")
def calendar():
    conn = sqlite3.connect("barber.db")
    c = conn.cursor()

    c.execute("""
        SELECT id, name, start_time, duration, service
        FROM appointments
    """)

    appointments = c.fetchall()
    conn.close()

    events = []

    for a in appointments:
        def add_minutes(time_str, duration):

            h, m = map(int, time_str.split(":"))

            total = h * 60 + m + duration

            return f"{total // 60:02d}:{total % 60:02d}"

        events = []

        for a in appointments:
            end_time = add_minutes(a[2], a[3])

            def add_minutes(time_str, duration):

                h, m = map(int, time_str.split(":"))

                total = h * 60 + m + duration

                return f"{total // 60:02d}:{total % 60:02d}"

            events = []

            for a in appointments:
                end_time = add_minutes(a[2], a[3])

                color = "#3788d8"

                if a[4] == "Fade":
                    color = "#ff4d4d"

                elif a[4] == "Ξύρισμα":
                    color = "#222222"

                elif a[4] == "Παιδικό":
                    color = "#4CAF50"

                events.append({
                    "id": a[0],
                    "title": f"{a[1]} - {a[4]}",
                    "start": f"2026-05-15T{a[2]}",
                    "end": f"2026-05-15T{end_time}",
                    "backgroundColor": color,
                    "borderColor": color
                })

    return render_template("calendar.html", events=events)

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):

    conn = sqlite3.connect("barber.db")
    c = conn.cursor()

    if request.method == "POST":

        name = request.form["name"]
        phone = request.form["phone"]
        start_time = request.form["start_time"]
        duration = int(request.form["duration"])
        service = request.form["service"]

        c.execute("""
            UPDATE appointments
            SET name=?, phone=?, start_time=?, duration=?, service=?
            WHERE id=?
        """, (name, phone, start_time, duration, service, id))

        conn.commit()
        conn.close()

        return redirect("/calendar")

    c.execute("""
        SELECT id, name, phone, start_time, duration, service
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


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)