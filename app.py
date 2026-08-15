from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "CHANGE_THIS_SECRET"
DB = "bale_panel.db"

def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init():
    c = conn()
    c.execute("""CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_link TEXT NOT NULL,
        target INTEGER NOT NULL,
        delivered INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT NOT NULL
    )""")
    c.commit(); c.close()

@app.route("/")
def home():
    c = conn()
    orders = c.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    total = c.execute("SELECT COUNT(*) n FROM orders").fetchone()["n"]
    active = c.execute("SELECT COUNT(*) n FROM orders WHERE status IN ('pending','active')").fetchone()["n"]
    done = c.execute("SELECT COUNT(*) n FROM orders WHERE status='completed'").fetchone()["n"]
    c.close()
    return render_template("index.html", orders=orders, total=total, active=active, done=done)

@app.post("/orders")
def add():
    link = request.form.get("channel_link","").strip()
    try: target = int(request.form.get("target","0"))
    except: target = 0
    if not link.startswith("https://ble.ir/"):
        flash("لینک کانال بله را به شکل https://ble.ir/... وارد کن.")
        return redirect(url_for("home"))
    if target < 1:
        flash("تعداد هدف باید حداقل ۱ باشد.")
        return redirect(url_for("home"))
    c=conn()
    c.execute("INSERT INTO orders(channel_link,target,created_at) VALUES(?,?,?)",
              (link,target,datetime.now().strftime("%Y-%m-%d %H:%M")))
    c.commit(); c.close()
    return redirect(url_for("home"))

@app.post("/orders/<int:oid>/status")
def status(oid):
    new = request.form.get("status","active")
    if new not in ("pending","active","paused","completed"):
        new="pending"
    c=conn(); c.execute("UPDATE orders SET status=? WHERE id=?",(new,oid)); c.commit(); c.close()
    return redirect(url_for("home"))

@app.post("/orders/<int:oid>/progress")
def progress(oid):
    try: delivered=max(0,int(request.form.get("delivered","0")))
    except: delivered=0
    c=conn(); row=c.execute("SELECT target FROM orders WHERE id=?",(oid,)).fetchone()
    if row:
        delivered=min(delivered,row["target"])
        st="completed" if delivered>=row["target"] else "active"
        c.execute("UPDATE orders SET delivered=?,status=? WHERE id=?",(delivered,st,oid))
        c.commit()
    c.close(); return redirect(url_for("home"))

@app.post("/orders/<int:oid>/delete")
def delete(oid):
    c=conn(); c.execute("DELETE FROM orders WHERE id=?",(oid,)); c.commit(); c.close()
    return redirect(url_for("home"))

@app.get("/api/orders")
def api_orders():
    c=conn(); rows=[dict(x) for x in c.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()]; c.close()
    return jsonify(rows)

if __name__=="__main__":
    init()
    app.run(host="0.0.0.0", port=5000, debug=False)
