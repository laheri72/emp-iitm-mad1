import os

# Base directory of the project — using this so paths don't break
# when running from different working directories
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Secret key for sessions and CSRF tokens.
    # In a real deployment this would come from an env variable,
    # but for local project this is fine.
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'emp-secret-key-iitm-2026'

    # SQLite DB will be created inside the instance/ folder automatically
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'emp.db')

    # Disabling modification tracking since we don't need that overhead
    SQLALCHEMY_TRACK_MODIFICATIONS = False
