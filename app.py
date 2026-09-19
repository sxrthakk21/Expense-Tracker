from flask import Flask, render_template, request, redirect, Response, session, url_for
import sqlite3
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import os
import csv
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer
)
from reportlab.lib.styles import getSampleStyleSheet


app = Flask(__name__)

# =========================================================
# SECRET KEY FOR LOGIN SESSION
# =========================================================

app.secret_key = "expense_tracker_secret_key_12345"


# =========================================================
# DATABASE
# =========================================================

def create_database():

    connection = sqlite3.connect("expenses.db")
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'expense'
        )
    """)

    connection.commit()
    connection.close()


# =========================================================
# CREATE CHARTS
# =========================================================

def create_charts():

    connection = sqlite3.connect("expenses.db")
    cursor = connection.cursor()

    os.makedirs("static/charts", exist_ok=True)

    # -----------------------------------------------------
    # PIE CHART
    # -----------------------------------------------------

    cursor.execute("""
        SELECT category, SUM(amount)
        FROM expenses
        WHERE type = 'expense'
        GROUP BY category
    """)

    category_data = cursor.fetchall()

    if category_data:

        categories = []
        amounts = []

        for row in category_data:
            categories.append(row[0])
            amounts.append(row[1])

        plt.figure(figsize=(6, 6))

        plt.pie(
            amounts,
            labels=categories,
            autopct="%1.1f%%",
            startangle=90
        )

        plt.title("Pie Chart")

        plt.tight_layout()

        plt.savefig(
            "static/charts/pie_chart.png",
            dpi=150
        )

        plt.close()

    # -----------------------------------------------------
    # BAR GRAPH
    # -----------------------------------------------------

    cursor.execute("""
        SELECT substr(date, 1, 7), SUM(amount)
        FROM expenses
        WHERE type = 'expense'
        GROUP BY substr(date, 1, 7)
        ORDER BY substr(date, 1, 7)
    """)

    monthly_data = cursor.fetchall()

    if monthly_data:

        months = []
        amounts = []

        for row in monthly_data:
            months.append(row[0])
            amounts.append(row[1])

        plt.figure(figsize=(8, 5))

        plt.bar(months, amounts)

        plt.title("Bar Graph")
        plt.xlabel("Month")
        plt.ylabel("Amount (₹)")

        plt.xticks(rotation=45)

        plt.tight_layout()

        plt.savefig(
            "static/charts/bar_chart.png",
            dpi=150
        )

        plt.close()

    connection.close()


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def home():

    return render_template("index.html")


# =========================================================
# LOGIN PAGE
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    # -----------------------------------------------------
    # WHEN USER SUBMITS LOGIN FORM
    # -----------------------------------------------------

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        # -------------------------------------------------
        # DEMO LOGIN CREDENTIALS
        # -------------------------------------------------

        if username == "admin" and password == "1234":

            # Store login information in session
            session["logged_in"] = True
            session["username"] = username

            # Send user to dashboard
            return redirect(url_for("dashboard"))

        else:

            # Wrong username/password
            return render_template(
                "login.html",
                error="Invalid username or password"
            )

    # -----------------------------------------------------
    # WHEN USER OPENS /login
    # -----------------------------------------------------

    return render_template("login.html")


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    # Remove all login/session information
    session.clear()

    # Return user to login page
    return redirect(url_for("login"))


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    # -----------------------------------------------------
    # CHECK LOGIN
    # -----------------------------------------------------

    if not session.get("logged_in"):

        return redirect(url_for("login"))

    # -----------------------------------------------------
    # DATABASE CONNECTION
    # -----------------------------------------------------

    connection = sqlite3.connect("expenses.db")
    cursor = connection.cursor()

    # -----------------------------------------------------
    # RECENT EXPENSES
    # -----------------------------------------------------

    cursor.execute("""
        SELECT *
        FROM expenses
        ORDER BY date DESC
        LIMIT 10
    """)

    recent_expenses = cursor.fetchall()

    # -----------------------------------------------------
    # TOTAL INCOME
    # -----------------------------------------------------

    cursor.execute("""
        SELECT SUM(amount)
        FROM expenses
        WHERE type = 'income'
    """)

    total_income = cursor.fetchone()[0] or 0

    # -----------------------------------------------------
    # TOTAL EXPENSE
    # -----------------------------------------------------

    cursor.execute("""
        SELECT SUM(amount)
        FROM expenses
        WHERE type = 'expense'
    """)

    total_expense = cursor.fetchone()[0] or 0

    # -----------------------------------------------------
    # BALANCE
    # -----------------------------------------------------

    balance = total_income - total_expense

    connection.close()

    # Create/update charts
    create_charts()

    # -----------------------------------------------------
    # SEND DATA TO DASHBOARD
    # -----------------------------------------------------

    return render_template(
        "dashboard.html",
        expenses=recent_expenses,
        total_income=total_income,
        total_expense=total_expense,
        balance=balance
    )


# =========================================================
# TRANSACTIONS PAGE
# =========================================================

@app.route("/transaction")
def transactions():

    # Check login
    if not session.get("logged_in"):

        return redirect(url_for("login"))

    connection = sqlite3.connect("expenses.db")
    cursor = connection.cursor()

    # -----------------------------------------------------
    # ALL TRANSACTIONS
    # -----------------------------------------------------

    cursor.execute("""
        SELECT *
        FROM expenses
        ORDER BY date DESC
    """)

    expenses = cursor.fetchall()

    # -----------------------------------------------------
    # CATEGORY SUMMARY
    # -----------------------------------------------------

    cursor.execute("""
        SELECT category, SUM(amount)
        FROM expenses
        WHERE type = 'expense'
        GROUP BY category
        ORDER BY SUM(amount) DESC
    """)

    categories = cursor.fetchall()

    connection.close()

    return render_template(
        "transaction.html",
        expenses=expenses,
        categories=categories
    )


# =========================================================
# ADD EXPENSE / INCOME
# =========================================================

@app.route("/add", methods=["POST"])
def add_expense():

    # Check login
    if not session.get("logged_in"):

        return redirect(url_for("login"))

    description = request.form["description"]
    amount = request.form["amount"]
    category = request.form["category"]
    date = request.form["date"]
    type_ = request.form["type"]

    connection = sqlite3.connect("expenses.db")
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO expenses
        (description, amount, category, date, type)
        VALUES (?, ?, ?, ?, ?)
    """, (
        description,
        amount,
        category,
        date,
        type_
    ))

    connection.commit()
    connection.close()

    return redirect(url_for("dashboard"))


# =========================================================
# DELETE EXPENSE
# =========================================================

@app.route("/delete/<int:id>")
def delete_expense(id):

    # Check login
    if not session.get("logged_in"):

        return redirect(url_for("login"))

    connection = sqlite3.connect("expenses.db")
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM expenses WHERE id = ?",
        (id,)
    )

    connection.commit()
    connection.close()

    return redirect(url_for("transactions"))


# =========================================================
# EXPORT TO CSV
# =========================================================

@app.route("/export/csv")
def export_csv():

    # Check login
    if not session.get("logged_in"):

        return redirect(url_for("login"))

    connection = sqlite3.connect("expenses.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, description, amount, category, date, type
        FROM expenses
        ORDER BY date DESC
    """)

    rows = cursor.fetchall()

    connection.close()

    # Create CSV file in memory
    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow([
        "ID",
        "Description",
        "Amount",
        "Category",
        "Date",
        "Type"
    ])

    for row in rows:

        writer.writerow(row)

    csv_data = output.getvalue()

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition":
            "attachment; filename=transactions.csv"
        }
    )


# =========================================================
# EXPORT TO PDF
# =========================================================

@app.route("/export/pdf")
def export_pdf():

    # Check login
    if not session.get("logged_in"):

        return redirect(url_for("login"))

    connection = sqlite3.connect("expenses.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT description, amount, category, date, type
        FROM expenses
        ORDER BY date DESC
    """)

    rows = cursor.fetchall()

    connection.close()

    # Create PDF in memory
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4
    )

    styles = getSampleStyleSheet()

    elements = []

    elements.append(
        Paragraph(
            "Transaction History",
            styles["Title"]
        )
    )

    elements.append(
        Spacer(1, 20)
    )

    # -----------------------------------------------------
    # TABLE DATA
    # -----------------------------------------------------

    table_data = [
        [
            "Description",
            "Amount",
            "Category",
            "Date",
            "Type"
        ]
    ]

    for row in rows:

        table_data.append(
            [str(cell) for cell in row]
        )

    # -----------------------------------------------------
    # TABLE
    # -----------------------------------------------------

    table = Table(
        table_data,
        repeatRows=1
    )

    table.setStyle(
        TableStyle([

            (
                'BACKGROUND',
                (0, 0),
                (-1, 0),
                colors.HexColor("#0279CE")
            ),

            (
                'TEXTCOLOR',
                (0, 0),
                (-1, 0),
                colors.white
            ),

            (
                'FONTNAME',
                (0, 0),
                (-1, 0),
                'Helvetica-Bold'
            ),

            (
                'FONTSIZE',
                (0, 0),
                (-1, -1),
                10
            ),

            (
                'GRID',
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),

            (
                'ROWBACKGROUNDS',
                (0, 1),
                (-1, -1),
                [
                    colors.white,
                    colors.HexColor("#f5f5f5")
                ]
            ),

            (
                'ALIGN',
                (0, 0),
                (-1, -1),
                'LEFT'
            ),

            (
                'VALIGN',
                (0, 0),
                (-1, -1),
                'MIDDLE'
            ),

            (
                'TOPPADDING',
                (0, 0),
                (-1, -1),
                8
            ),

            (
                'BOTTOMPADDING',
                (0, 0),
                (-1, -1),
                8
            )

        ])
    )

    elements.append(table)

    doc.build(elements)

    buffer.seek(0)

    return Response(
        buffer.getvalue(),
        mimetype="application/pdf",
        headers={
            "Content-Disposition":
            "attachment; filename=transactions.pdf"
        }
    )


# =========================================================
# CONTACT / ABOUT PAGE
# =========================================================

@app.route("/contact")
def contact():

    # Check login
    if not session.get("logged_in"):

        return redirect(url_for("login"))

    return render_template("contact.html")


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    create_database()

    app.run(debug=True)