from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os
from functools import wraps
from datetime import date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "library.db")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_name TEXT NOT NULL,
        accession_no TEXT UNIQUE NOT NULL,
        author TEXT,
        subject TEXT,
        class_name TEXT,
        category TEXT,
        quantity INTEGER NOT NULL DEFAULT 1,
        available_quantity INTEGER NOT NULL DEFAULT 1,
        rack_no TEXT,
        shelf_no TEXT,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_name TEXT NOT NULL,
        admission_no TEXT UNIQUE NOT NULL,
        class_name TEXT,
        section TEXT
    );
    CREATE TABLE IF NOT EXISTS book_issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        book_id INTEGER NOT NULL,
        issue_date TEXT NOT NULL,
        due_date TEXT,
        return_date TEXT,
        status TEXT NOT NULL DEFAULT 'Issued',
        FOREIGN KEY(student_id) REFERENCES students(id),
        FOREIGN KEY(book_id) REFERENCES books(id)
    );
    """)
    if conn.execute("SELECT COUNT(*) FROM admins").fetchone()[0] == 0:
        conn.execute("INSERT INTO admins(username,password_hash) VALUES(?,?)",
                     ("admin", generate_password_hash("admin123")))
    conn.commit()
    conn.close()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)
    return wrapper

@app.route("/health")
def health():
    return {"status": "ok", "service": "school-library"}

@app.route("/")
def index():
    q = request.args.get("q","").strip()
    conn = db()
    if q:
        like = f"%{q}%"
        books = conn.execute("""
          SELECT * FROM books WHERE active=1 AND
          (book_name LIKE ? OR author LIKE ? OR subject LIKE ? OR class_name LIKE ? OR accession_no LIKE ?)
          ORDER BY book_name
        """,(like,like,like,like,like)).fetchall()
    else:
        books = conn.execute("SELECT * FROM books WHERE active=1 ORDER BY book_name").fetchall()
    conn.close()
    return render_template("index.html", books=books, q=q)

@app.route("/admin/login", methods=["GET","POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        conn = db()
        admin = conn.execute("SELECT * FROM admins WHERE username=?", (username,)).fetchone()
        conn.close()
        if admin and check_password_hash(admin["password_hash"], password):
            session["admin_id"] = admin["id"]
            session["admin_username"] = admin["username"]
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")

@app.route("/admin/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/admin")
@login_required
def dashboard():
    conn = db()
    stats = {
        "books": conn.execute("SELECT COUNT(*) FROM books WHERE active=1").fetchone()[0],
        "copies": conn.execute("SELECT COALESCE(SUM(quantity),0) FROM books WHERE active=1").fetchone()[0],
        "available": conn.execute("SELECT COALESCE(SUM(available_quantity),0) FROM books WHERE active=1").fetchone()[0],
        "issued": conn.execute("SELECT COUNT(*) FROM book_issues WHERE status='Issued'").fetchone()[0],
    }
    recent = conn.execute("""
      SELECT i.*, s.student_name, s.admission_no, s.class_name, s.section,
             b.book_name, b.accession_no
      FROM book_issues i JOIN students s ON s.id=i.student_id
      JOIN books b ON b.id=i.book_id ORDER BY i.id DESC LIMIT 10
    """).fetchall()
    conn.close()
    return render_template("dashboard.html", stats=stats, recent=recent)

@app.route("/admin/books")
@login_required
def books():
    conn=db()
    rows=conn.execute("SELECT * FROM books ORDER BY active DESC, book_name").fetchall()
    conn.close()
    return render_template("books.html", books=rows)

@app.route("/admin/books/add", methods=["GET","POST"])
@login_required
def add_book():
    if request.method=="POST":
        f=request.form
        try:
            qty=max(1,int(f.get("quantity",1)))
            conn=db()
            conn.execute("""INSERT INTO books
              (book_name,accession_no,author,subject,class_name,category,quantity,available_quantity,rack_no,shelf_no)
              VALUES(?,?,?,?,?,?,?,?,?,?)""",
              (f["book_name"],f["accession_no"],f.get("author"),f.get("subject"),f.get("class_name"),
               f.get("category"),qty,qty,f.get("rack_no"),f.get("shelf_no")))
            conn.commit(); conn.close()
            flash("Book added successfully.","success")
            return redirect(url_for("books"))
        except sqlite3.IntegrityError:
            flash("Accession number must be unique.","error")
    return render_template("book_form.html", book=None)

@app.route("/admin/books/edit/<int:book_id>", methods=["GET","POST"])
@login_required
def edit_book(book_id):
    conn=db()
    book=conn.execute("SELECT * FROM books WHERE id=?",(book_id,)).fetchone()
    if not book:
        conn.close(); return redirect(url_for("books"))
    if request.method=="POST":
        f=request.form
        old_qty=book["quantity"]; new_qty=max(1,int(f.get("quantity",1)))
        issued=old_qty-book["available_quantity"]
        if new_qty < issued:
            flash(f"Quantity cannot be less than {issued} currently issued copies.","error")
            conn.close(); return redirect(url_for("edit_book",book_id=book_id))
        available=new_qty-issued
        try:
            conn.execute("""UPDATE books SET book_name=?,accession_no=?,author=?,subject=?,class_name=?,
              category=?,quantity=?,available_quantity=?,rack_no=?,shelf_no=? WHERE id=?""",
              (f["book_name"],f["accession_no"],f.get("author"),f.get("subject"),f.get("class_name"),
               f.get("category"),new_qty,available,f.get("rack_no"),f.get("shelf_no"),book_id))
            conn.commit(); conn.close()
            flash("Book updated successfully.","success")
            return redirect(url_for("books"))
        except sqlite3.IntegrityError:
            flash("Accession number must be unique.","error")
    conn.close()
    return render_template("book_form.html", book=book)

@app.route("/admin/books/toggle/<int:book_id>", methods=["POST"])
@login_required
def toggle_book(book_id):
    conn=db()
    conn.execute("UPDATE books SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?",(book_id,))
    conn.commit(); conn.close()
    return redirect(url_for("books"))

@app.route("/admin/students")
@login_required
def students():
    conn=db()
    rows=conn.execute("SELECT * FROM students ORDER BY student_name").fetchall()
    conn.close()
    return render_template("students.html", students=rows)

@app.route("/admin/students/add", methods=["POST"])
@login_required
def add_student():
    f=request.form
    try:
        conn=db()
        conn.execute("INSERT INTO students(student_name,admission_no,class_name,section) VALUES(?,?,?,?)",
                     (f["student_name"],f["admission_no"],f.get("class_name"),f.get("section")))
        conn.commit(); conn.close()
        flash("Student added.","success")
    except sqlite3.IntegrityError:
        flash("Admission number must be unique.","error")
    return redirect(url_for("students"))

@app.route("/admin/issues")
@login_required
def issues():
    conn=db()
    rows=conn.execute("""
      SELECT i.*,s.student_name,s.admission_no,s.class_name,s.section,b.book_name,b.accession_no
      FROM book_issues i JOIN students s ON s.id=i.student_id JOIN books b ON b.id=i.book_id
      ORDER BY CASE WHEN i.status='Issued' THEN 0 ELSE 1 END, i.id DESC
    """).fetchall()
    books=conn.execute("SELECT * FROM books WHERE active=1 AND available_quantity>0 ORDER BY book_name").fetchall()
    students=conn.execute("SELECT * FROM students ORDER BY student_name").fetchall()
    conn.close()
    return render_template("issues.html", issues=rows, books=books, students=students)

@app.route("/admin/issues/add", methods=["POST"])
@login_required
def issue_book():
    student_id=int(request.form["student_id"]); book_id=int(request.form["book_id"])
    issue_date=request.form.get("issue_date") or date.today().isoformat()
    due_date=request.form.get("due_date")
    conn=db()
    book=conn.execute("SELECT * FROM books WHERE id=? AND active=1",(book_id,)).fetchone()
    if not book or book["available_quantity"]<=0:
        flash("This book is currently unavailable.","error")
        conn.close(); return redirect(url_for("issues"))
    conn.execute("""INSERT INTO book_issues(student_id,book_id,issue_date,due_date,status)
                    VALUES(?,?,?,?, 'Issued')""",(student_id,book_id,issue_date,due_date))
    conn.execute("UPDATE books SET available_quantity=available_quantity-1 WHERE id=?",(book_id,))
    conn.commit(); conn.close()
    flash("Book issued successfully.","success")
    return redirect(url_for("issues"))

@app.route("/admin/issues/return/<int:issue_id>", methods=["POST"])
@login_required
def return_book(issue_id):
    conn=db()
    issue=conn.execute("SELECT * FROM book_issues WHERE id=? AND status='Issued'",(issue_id,)).fetchone()
    if issue:
        conn.execute("UPDATE book_issues SET status='Returned',return_date=? WHERE id=?",
                     (request.form.get("return_date") or date.today().isoformat(),issue_id))
        conn.execute("UPDATE books SET available_quantity=available_quantity+1 WHERE id=?",(issue["book_id"],))
        conn.commit()
        flash("Book returned and availability updated.","success")
    conn.close()
    return redirect(url_for("issues"))

@app.route("/api/book/<int:book_id>")
def book_api(book_id):
    conn=db()
    b=conn.execute("SELECT * FROM books WHERE id=? AND active=1",(book_id,)).fetchone()
    conn.close()
    if not b: return jsonify({"error":"Not found"}),404
    status="Available" if b["available_quantity"]>0 else "Currently Issued"
    return jsonify(dict(b, status=status))

init_db()

if __name__=="__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
