from flask import Flask, render_template, request, redirect, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-this-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///students.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models


class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    admission_number = db.Column(db.String(50), unique=True, nullable=False)
    student_class = db.Column(db.String(20), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Student {self.name}>'


# Create tables
with app.app_context():
    db.create_all()

    # Create default admin if not exists
    if not Admin.query.filter_by(username='admin').first():
        default_admin = Admin(username='admin', password='1234')
        db.session.add(default_admin)
        db.session.commit()


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        admin = Admin.query.filter_by(
            username=username, password=password).first()

        if admin:
            session["user"] = username
            session["user_id"] = admin.id
            flash("Login successful!", "success")
            return redirect("/dashboard")
        else:
            flash("Invalid credentials. Please try again.", "error")

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        flash("Please login first", "error")
        return redirect("/")

    # Get statistics from database
    total_students = Student.query.count()

    # Get unique classes count
    unique_classes = db.session.query(Student.student_class).distinct().count()

    # Get recent students (last 5 added)
    recent_students = Student.query.order_by(
        Student.date_added.desc()).limit(5).all()

    # Age statistics
    avg_age = db.session.query(db.func.avg(Student.age)).scalar() or 0

    return render_template("dashboard.html",
                           total_students=total_students,
                           unique_classes=unique_classes,
                           recent_students=recent_students,
                           avg_age=round(avg_age, 1))


@app.route("/students", methods=["GET", "POST"])
def students():
    if "user" not in session:
        flash("Please login first", "error")
        return redirect("/")

    if request.method == "POST":
        name = request.form["name"]
        admission = request.form["admission"]
        student_class = request.form["class"]
        age = request.form["age"]

        # Check if admission number already exists
        existing_student = Student.query.filter_by(
            admission_number=admission).first()
        if existing_student:
            flash(
                f"Student with admission number {admission} already exists!", "error")
        else:
            # Create new student
            new_student = Student(
                name=name,
                admission_number=admission,
                student_class=student_class,
                age=age
            )

            try:
                db.session.add(new_student)
                db.session.commit()
                flash(f"Student {name} added successfully!", "success")
            except Exception as e:
                db.session.rollback()
                flash("Error adding student. Please try again.", "error")

    # Get all students from database
    all_students = Student.query.order_by(Student.date_added.desc()).all()

    # Get statistics
    total_count = len(all_students)

    return render_template("students.html",
                           students=all_students,
                           total_count=total_count)


@app.route("/student/<int:student_id>/delete", methods=["POST"])
def delete_student(student_id):
    if "user" not in session:
        return {"error": "Unauthorized"}, 401

    student = Student.query.get_or_404(student_id)
    try:
        db.session.delete(student)
        db.session.commit()
        flash(f"Student {student.name} deleted successfully!", "success")
    except:
        db.session.rollback()
        flash("Error deleting student", "error")

    return redirect("/students")


@app.route("/student/<int:student_id>/edit", methods=["GET", "POST"])
def edit_student(student_id):
    if "user" not in session:
        flash("Please login first", "error")
        return redirect("/")

    student = Student.query.get_or_404(student_id)

    if request.method == "POST":
        student.name = request.form["name"]
        student.admission_number = request.form["admission"]
        student.student_class = request.form["class"]
        student.age = request.form["age"]

        try:
            db.session.commit()
            flash(f"Student {student.name} updated successfully!", "success")
            return redirect("/students")
        except:
            db.session.rollback()
            flash("Error updating student", "error")

    return render_template("edit_student.html", student=student)


@app.route("/search")
def search_students():
    if "user" not in session:
        return {"error": "Unauthorized"}, 401

    query = request.args.get('q', '')
    if query:
        students = Student.query.filter(
            (Student.name.contains(query)) |
            (Student.admission_number.contains(query)) |
            (Student.student_class.contains(query))
        ).all()
    else:
        students = []

    return render_template("search_results.html", students=students, query=query)


@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("user_id", None)
    flash("You have been logged out", "info")
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
