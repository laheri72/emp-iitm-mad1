"""
Examination Management Portal (EMP)
------------------------------------
IITM BS Data Science — App Dev 1 Project | September 2026 Term
Built with: Flask + SQLAlchemy + Jinja2 + Bootstrap + SQLite

This is the main application entry point.
Running this file directly will:
  1. Create all tables in the SQLite database (if not already present)
  2. Seed one admin user so you can log in right away
  3. Start the dev server on http://127.0.0.1:5000
"""

import os
from flask import Flask
from flask_login import LoginManager

from config import Config
from models import db, User


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # make sure the instance folder exists so SQLite can write there
    os.makedirs(os.path.join(app.root_path, 'instance'), exist_ok=True)

    # hook up the database
    db.init_app(app)

    # set up flask-login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        # flask-login calls this every request to get the current user object
        return User.query.get(int(user_id))

    # register all the route blueprints
    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.examiner import examiner_bp
    from routes.student import student_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(examiner_bp, url_prefix='/examiner')
    app.register_blueprint(student_bp, url_prefix='/student')

    # create all DB tables + seed admin on first run
    with app.app_context():
        db.create_all()
        seed_admin()

    return app


def seed_admin():
    """
    Creates the default admin account if it doesn't exist yet.
    This runs every time the app starts, but the check ensures
    it only actually inserts once.
    """
    admin_email = 'admin@emp.iitm.ac.in'
    existing = User.query.filter_by(email=admin_email).first()

    if not existing:
        admin = User(
            name='EMP Administrator',
            email=admin_email,
            role='admin',
            is_active=True,
            is_approved=True
        )
        admin.set_password('Admin@1234')  # change this after first login
        db.session.add(admin)
        db.session.commit()
        print('[EMP] Admin account seeded — email: admin@emp.iitm.ac.in | pass: Admin@1234')


# create the app instance at module level so Flask CLI can find it
app = create_app()


if __name__ == '__main__':
    # debug=True only for development — hot reload + better error pages
    app.run(debug=True, host='127.0.0.1', port=5000)
