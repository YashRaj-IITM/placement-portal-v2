from flask_security import hash_password

from extensions import db
from models import User, user_datastore

ROLES = {
    "admin": "Placement cell administrator",
    "company": "Recruiting company",
    "student": "Student",
}


def seed_database(app):
    """Create roles and the default admin account if they don't exist."""
    for name, description in ROLES.items():
        user_datastore.find_or_create_role(name=name, description=description)
    db.session.commit()

    admin_email = app.config["ADMIN_EMAIL"].lower()
    if not User.query.filter_by(email=admin_email).first():
        user_datastore.create_user(
            email=admin_email,
            password=hash_password(app.config["ADMIN_PASSWORD"]),
            full_name=app.config["ADMIN_NAME"],
            roles=["admin"],
            active=True,
            is_approved=True,
        )
        db.session.commit()
        app.logger.info("Default admin created: %s", admin_email)
