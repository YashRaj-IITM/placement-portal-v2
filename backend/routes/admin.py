from flask import Blueprint, jsonify, request
from sqlalchemy import func

from extensions import db
from models import (
    APPLICATION_STATUSES,
    DRIVE_STATUSES,
    Application,
    CompanyProfile,
    PlacementDrive,
    StudentProfile,
    User,
    iso,
    user_datastore,
)
from utils import error, json_body, search_like, token_roles

admin_bp = Blueprint("admin_api", __name__, url_prefix="/api/admin")
admin_only = token_roles("admin")
PAST_TENSE = {
    "approve": "approved",
    "reject": "rejected",
    "blacklist": "blacklisted",
    "activate": "activated",
}


@admin_bp.get("/stats")
@admin_only
def stats():
    drives_by_status = dict(
        db.session.query(PlacementDrive.status, func.count(PlacementDrive.id))
        .group_by(PlacementDrive.status)
        .all()
    )
    apps_by_status = dict(
        db.session.query(Application.status, func.count(Application.id))
        .group_by(Application.status)
        .all()
    )
    return jsonify(
        {
            "total_students": StudentProfile.query.count(),
            "total_companies": CompanyProfile.query.count(),
            "total_drives": PlacementDrive.query.count(),
            "total_applications": Application.query.count(),
            "pending_companies": User.query.join(CompanyProfile, CompanyProfile.user_id == User.id)
            .filter(User.is_approved.is_(False))
            .count(),
            "drives_by_status": {s: drives_by_status.get(s, 0) for s in DRIVE_STATUSES},
            "applications_by_status": {s: apps_by_status.get(s, 0) for s in APPLICATION_STATUSES},
        }
    )


# --------------------------------------------------------------- companies
def _company_dict(profile):
    u = profile.user
    return {
        "id": u.id,
        "email": u.email,
        "full_name": u.full_name,
        "company_name": profile.company_name,
        "hr_contact": profile.hr_contact,
        "website": profile.website,
        "is_approved": u.is_approved,
        "active": u.active,
        "drive_count": len(profile.drives),
    }


@admin_bp.get("/companies")
@admin_only
def list_companies():
    query = CompanyProfile.query.join(User, CompanyProfile.user_id == User.id)
    like = search_like(request.args.get("q"))
    if like:
        query = query.filter(
            CompanyProfile.company_name.ilike(like) | User.email.ilike(like)
        )
    return jsonify([_company_dict(p) for p in query.order_by(CompanyProfile.company_name).all()])


@admin_bp.put("/companies/<int:user_id>/status")
@admin_only
def update_company_status(user_id):
    action = json_body().get("action")
    user = User.query.join(CompanyProfile, CompanyProfile.user_id == User.id).filter(User.id == user_id).first()
    if not user:
        return error("Company not found", 404)
    if action == "approve":
        user.is_approved = True
    elif action == "reject":
        user.is_approved = False
    elif action == "blacklist":
        user.active = False
        user_datastore.set_uniquifier(user)  # kill any token already issued
    elif action == "activate":
        user.active = True
    else:
        return error("action must be approve, reject, blacklist or activate")
    db.session.commit()
    return jsonify({"message": f"Company {PAST_TENSE[action]}"})


@admin_bp.delete("/companies/<int:user_id>")
@admin_only
def delete_company(user_id):
    user = User.query.join(CompanyProfile, CompanyProfile.user_id == User.id).filter(User.id == user_id).first()
    if not user:
        return error("Company not found", 404)
    db.session.delete(user)  # cascades to profile, drives and applications
    db.session.commit()
    return jsonify({"message": "Company deleted"})


# ---------------------------------------------------------------- students
def _student_dict(profile):
    u = profile.user
    return {
        "id": u.id,
        "email": u.email,
        "full_name": u.full_name,
        "branch": profile.branch,
        "cgpa": profile.cgpa,
        "graduation_year": profile.graduation_year,
        "active": u.active,
        "application_count": len(profile.applications),
    }


@admin_bp.get("/students")
@admin_only
def list_students():
    query = StudentProfile.query.join(User, StudentProfile.user_id == User.id)
    like = search_like(request.args.get("q"))
    if like:
        query = query.filter(
            User.full_name.ilike(like) | User.email.ilike(like) | StudentProfile.branch.ilike(like)
        )
    return jsonify([_student_dict(p) for p in query.order_by(User.full_name).all()])


@admin_bp.put("/students/<int:user_id>/status")
@admin_only
def update_student_status(user_id):
    action = json_body().get("action")
    user = User.query.join(StudentProfile, StudentProfile.user_id == User.id).filter(User.id == user_id).first()
    if not user:
        return error("Student not found", 404)
    if action == "blacklist":
        user.active = False
        user_datastore.set_uniquifier(user)  # kill any token already issued
    elif action == "activate":
        user.active = True
    else:
        return error("action must be blacklist or activate")
    db.session.commit()
    return jsonify({"message": f"Student {PAST_TENSE[action]}"})


@admin_bp.delete("/students/<int:user_id>")
@admin_only
def delete_student(user_id):
    user = User.query.join(StudentProfile, StudentProfile.user_id == User.id).filter(User.id == user_id).first()
    if not user:
        return error("Student not found", 404)
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "Student deleted"})


# ------------------------------------------------------------------ drives
@admin_bp.get("/drives")
@admin_only
def list_drives():
    query = PlacementDrive.query.join(
        CompanyProfile, PlacementDrive.company_profile_id == CompanyProfile.id
    )
    like = search_like(request.args.get("q"))
    if like:
        query = query.filter(
            PlacementDrive.job_title.ilike(like) | CompanyProfile.company_name.ilike(like)
        )
    status = request.args.get("status")
    if status in DRIVE_STATUSES:
        query = query.filter(PlacementDrive.status == status)
    return jsonify([d.to_dict() for d in query.order_by(PlacementDrive.created_at.desc()).all()])


@admin_bp.put("/drives/<int:drive_id>/status")
@admin_only
def update_drive_status(drive_id):
    status = json_body().get("status")
    if status not in DRIVE_STATUSES:
        return error(f"status must be one of {', '.join(DRIVE_STATUSES)}")
    drive = db.session.get(PlacementDrive, drive_id)
    if not drive:
        return error("Drive not found", 404)
    drive.status = status
    db.session.commit()
    return jsonify({"message": f"Drive marked {status}"})


@admin_bp.delete("/drives/<int:drive_id>")
@admin_only
def delete_drive(drive_id):
    drive = db.session.get(PlacementDrive, drive_id)
    if not drive:
        return error("Drive not found", 404)
    db.session.delete(drive)
    db.session.commit()
    return jsonify({"message": "Drive deleted"})


# ------------------------------------------------------------ applications
@admin_bp.get("/applications")
@admin_only
def list_applications():
    query = (
        Application.query.join(PlacementDrive, Application.drive_id == PlacementDrive.id)
        .join(CompanyProfile, PlacementDrive.company_profile_id == CompanyProfile.id)
        .join(StudentProfile, Application.student_profile_id == StudentProfile.id)
        .join(User, StudentProfile.user_id == User.id)
    )
    like = search_like(request.args.get("q"))
    if like:
        query = query.filter(
            User.full_name.ilike(like)
            | CompanyProfile.company_name.ilike(like)
            | PlacementDrive.job_title.ilike(like)
        )
    result = [
        {
            "id": a.id,
            "student_name": a.student.user.full_name,
            "company_name": a.drive.company.company_name,
            "job_title": a.drive.job_title,
            "status": a.status,
            "application_date": iso(a.application_date),
        }
        for a in query.order_by(Application.application_date.desc()).all()
    ]
    return jsonify(result)
