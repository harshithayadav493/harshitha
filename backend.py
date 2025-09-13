# backend.py
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import statistics

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance.db'
db = SQLAlchemy(app)

# ------------------- Models -------------------
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    target = db.Column(db.Float, nullable=False)
    current = db.Column(db.Float, default=0.0)

# ------------------- Utils -------------------
def auto_category(desc: str) -> str:
    d = desc.lower()
    if any(word in d for word in ["bus", "metro", "uber", "auto", "train"]):
        return "Transport"
    if any(word in d for word in ["book", "pen", "stationery", "notebook"]):
        return "Books"
    if any(word in d for word in ["canteen", "lunch", "dinner", "cafe", "mess", "food"]):
        return "Food"
    if any(word in d for word in ["movie", "netflix", "spotify", "game"]):
        return "Entertainment"
    return "Others"

def predict_next(spends):
    if len(spends) < 3:
        return spends[-1] if spends else 0
    last3 = spends[-3:]
    slope = (last3[-1] - last3[0]) / 2
    return round(last3[-1] + slope, 2)

# ------------------- Routes -------------------
@app.route("/add_expense", methods=["POST"])
def add_expense():
    data = request.json
    desc = data.get("description")
    amt = float(data.get("amount", 0))
    cat = data.get("category") or auto_category(desc)

    new_expense = Expense(description=desc, amount=amt, category=cat)
    db.session.add(new_expense)
    db.session.commit()

    return jsonify({"message": "Expense added", "category": cat}), 201

@app.route("/expenses", methods=["GET"])
def get_expenses():
    expenses = Expense.query.order_by(Expense.date.desc()).all()
    return jsonify([
        {"id": e.id, "desc": e.description, "amount": e.amount,
         "category": e.category, "date": e.date.strftime("%Y-%m-%d")}
        for e in expenses
    ])

@app.route("/summary", methods=["GET"])
def get_summary():
    expenses = Expense.query.all()
    monthly_budget = 15000
    total_spent = sum(e.amount for e in expenses)

    # fake balance (budget - spent)
    balance = monthly_budget - total_spent

    # spending trend (monthly grouped, simplified)
    monthly_spends = []
    for e in expenses:
        ym = e.date.strftime("%Y-%m")
        found = next((item for item in monthly_spends if item["month"] == ym), None)
        if found:
            found["amount"] += e.amount
        else:
            monthly_spends.append({"month": ym, "amount": e.amount})

    monthly_spends_sorted = [m["amount"] for m in sorted(monthly_spends, key=lambda x: x["month"])]
    projection = predict_next(monthly_spends_sorted)

    alert = "Within budget"
    if projection > monthly_budget:
        alert = "Projected spending exceeds budget"

    return jsonify({
        "balance": balance,
        "spent": total_spent,
        "monthly_budget": monthly_budget,
        "projection": projection,
        "alert": alert
    })

@app.route("/goals", methods=["GET", "POST"])
def goals():
    if request.method == "POST":
        data = request.json
        g = Goal(name=data["name"], target=data["target"], current=data.get("current", 0))
        db.session.add(g)
        db.session.commit()
        return jsonify({"message": "Goal created"}), 201

    goals = Goal.query.all()
    return jsonify([{"name": g.name, "target": g.target, "current": g.current} for g in goals])

# ------------------- Run -------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
