from flask import Blueprint, jsonify
from flask_security import (
    auth_required,
    current_user,
    hash_password,
    verify_and_update_password,
)

from extensions import db
from models import CompanyProfile, StudentProfile, User, user_datastore
from utils import EMAIL_RE, ValidationError, error, json_body, text

auth_bp = Blueprint("auth_api", __name__, url_prefix="/api/auth")


def _new_account(data, role, is_approved):
    """Validate the common registration fields and create the user."""
    email = text(data.get("email"), "Email", required=True, max_len=150).lower()
    if not EMAIL_RE.match(email):
        raise ValidationError("Enter a valid email address")
    password = data.get("password") or ""
    if not isinstance(password, str) or len(password) < 8:
        raise ValidationError("Password must be at least 8 characters")
    full_name = text(data.get("full_name"), "Full name", min_len=2, max_len=150, required=True)
    if User.query.filter_by(email=email).first():
        raise ValidationError("An account with this email already exists")

    return user_datastore.create_user(
        email=email,
        password=hash_password(password),
        full_name=full_name,
        roles=[role],
        active=True,
        is_approved=is_approved,
    )


@auth_bp.post("/register/student")
def register_student():
    data = json_body()
    user = _new_account(data, "student", is_approved=True)
    db.session.add(StudentProfile(user=user))
    db.session.commit()
    return jsonify({"message": "Student registered successfully. You can log in now."}), 201


@auth_bp.post("/register/company")
def register_company():
    data = json_body()
    company_name = text(data.get("company_name"), "Company name", min_len=2, max_len=150, required=True)
    hr_contact = text(data.get("hr_contact"), "HR contact", max_len=150)
    website = text(data.get("website"), "Website", max_len=255)
    if website and not website.lower().startswith(("http://", "https://")):
        raise ValidationError("Website must start with http:// or https://")

    user = _new_account(data, "company", is_approved=False)  # admin approval needed
    db.session.add(
        CompanyProfile(user=user, company_name=company_name, hr_contact=hr_contact, website=website)
    )
    db.session.commit()
    return jsonify({"message": "Company registered. You can log in now, but you can post drives only after the admin approves your account."}), 201


@auth_bp.post("/login")
def login():
    data = json_body()
    email = text(data.get("email"), "Email").lower()
    password = data.get("password")
    user = User.query.filter_by(email=email).first()

    if not user or not isinstance(password, str) or not verify_and_update_password(password, user):
        return error("Invalid email or password", 401)
    if not user.active:
        return error("Your account has been blacklisted or deactivated", 403)

    db.session.commit()  # persists a rehashed password if Flask-Security upgraded it
    return jsonify({"token": user.get_auth_token(), "user": user.to_dict()}), 200


@auth_bp.post("/logout")
@auth_required("token")
def logout():
    # Rotating fs_uniquifier invalidates every token issued to this user
    user_datastore.set_uniquifier(current_user._get_current_object())
    db.session.commit()
    return jsonify({"message": "Logged out"}), 200


@auth_bp.get("/me")
@auth_required("token")
def me():
    return jsonify({"user": current_user.to_dict()}), 200
