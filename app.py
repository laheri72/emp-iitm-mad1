import os
from flask import Flask
from flask_login import LoginManager

from config import Config
from models import db, User


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(os.path.join(app.root_path, 'instance'), exist_ok=True)

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.examiner import examiner_bp
    from routes.student import student_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(examiner_bp, url_prefix='/examiner')
    app.register_blueprint(student_bp, url_prefix='/student')

    with app.app_context():
        db.create_all()
        seed_admin()

    return app


def seed_admin():
    # only creates admin if not already there
    admin_email = 'admin@emp.iitm.ac.in'
    if not User.query.filter_by(email=admin_email).first():
        admin = User(
            name='EMP Administrator',
            email=admin_email,
            role='admin',
            is_active=True,
            is_approved=True
        )
        admin.set_password('Admin@1234')
        db.session.add(admin)
        db.session.commit()
        print('Admin seeded — login: admin@emp.iitm.ac.in / Admin@1234')


app = create_app()


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
