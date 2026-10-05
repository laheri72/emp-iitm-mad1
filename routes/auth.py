from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(get_dashboard_url())
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(get_dashboard_url())

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('auth/login.html')

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash('Invalid email or password.', 'danger')
            return render_template('auth/login.html')

        if not user.is_active:
            flash('Account is deactivated. Contact admin.', 'warning')
            return render_template('auth/login.html')

        if user.is_examiner and not user.is_approved:
            flash('Your account is pending admin approval.', 'info')
            return render_template('auth/login.html')

        login_user(user, remember=True)
        flash(f'Welcome, {user.name}!', 'success')

        next_page = request.args.get('next')
        return redirect(next_page or get_dashboard_url())

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(get_dashboard_url())

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role = request.form.get('role', 'student')
        department = request.form.get('department', '').strip()
        phone = request.form.get('phone', '').strip()

        if not name or not email or not password:
            flash('Name, email and password are required.', 'danger')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('auth/register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')

        if role not in ('student', 'examiner'):
            flash('Invalid role.', 'danger')
            return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('auth/register.html')

        new_user = User(
            name=name,
            email=email,
            role=role,
            department=department if role == 'examiner' else None,
            phone=phone if role == 'examiner' else None,
            is_active=True,
            is_approved=(role == 'student')
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        if role == 'examiner':
            flash('Registered! Waiting for admin approval before you can log in.', 'info')
        else:
            flash('Registered successfully! You can now log in.', 'success')

        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.', 'info')
    return redirect(url_for('auth.login'))


def get_dashboard_url():
    if current_user.is_admin:
        return url_for('admin.dashboard')
    elif current_user.is_examiner:
        return url_for('examiner.dashboard')
    else:
        return url_for('student.dashboard')
