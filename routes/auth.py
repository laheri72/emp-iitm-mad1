from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def index():
    """Landing page — redirect based on who's logged in."""
    if current_user.is_authenticated:
        return redirect_to_dashboard()
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # if already logged in, no need to see this page
    if current_user.is_authenticated:
        return redirect_to_dashboard()

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Both email and password are required.', 'danger')
            return render_template('auth/login.html')

        user = User.query.filter_by(email=email).first()

        # check user exists and password matches
        if not user or not user.check_password(password):
            flash('Invalid email or password. Please try again.', 'danger')
            return render_template('auth/login.html')

        # check if the account is active
        if not user.is_active:
            flash('Your account has been deactivated. Contact admin.', 'warning')
            return render_template('auth/login.html')

        # examiners need admin approval before they can log in
        if user.is_examiner and not user.is_approved:
            flash('Your examiner account is pending admin approval.', 'info')
            return render_template('auth/login.html')

        login_user(user, remember=True)
        flash(f'Welcome back, {user.name}!', 'success')

        # send user to the next page if they were redirected here, else their dashboard
        next_page = request.args.get('next')
        return redirect(next_page or redirect_to_dashboard())

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registration is only for students and examiners — admin is pre-seeded."""
    if current_user.is_authenticated:
        return redirect_to_dashboard()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role = request.form.get('role', 'student')  # student or examiner
        department = request.form.get('department', '').strip()
        phone = request.form.get('phone', '').strip()

        # basic validation
        if not name or not email or not password:
            flash('Name, email, and password are all required.', 'danger')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('auth/register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')

        # don't allow admin registration through this form
        if role not in ('student', 'examiner'):
            flash('Invalid role selected.', 'danger')
            return render_template('auth/register.html')

        # make sure the email isn't already taken
        if User.query.filter_by(email=email).first():
            flash('An account with this email already exists.', 'danger')
            return render_template('auth/register.html')

        # create the new user
        new_user = User(
            name=name,
            email=email,
            role=role,
            department=department if role == 'examiner' else None,
            phone=phone if role == 'examiner' else None,
            is_active=True,
            # students are immediately active; examiners need admin approval
            is_approved=(role == 'student')
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        if role == 'examiner':
            flash('Examiner registration successful! Waiting for admin approval before you can log in.', 'info')
        else:
            flash('Registration successful! You can now log in.', 'success')

        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


def redirect_to_dashboard():
    """
    Helper: returns the correct dashboard URL string for the current user's role.
    Used after login and when already-authenticated users hit public pages.
    """
    if current_user.is_admin:
        return url_for('admin.dashboard')
    elif current_user.is_examiner:
        return url_for('examiner.dashboard')
    else:
        return url_for('student.dashboard')
