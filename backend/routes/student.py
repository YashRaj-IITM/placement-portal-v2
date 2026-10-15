import os

from celery.result import AsyncResult
from flask import Blueprint, current_app, jsonify, request, send_file
from flask_security import current_user

from extensions import db
from models import Application, CompanyProfile, PlacementDrive, User, iso, utcnow
from utils import error, json_body, number, search_like, text, token_roles, ValidationError

student_bp = Blueprint("student_api", __name__, url_prefix="/api/student")
student_only = token_roles("student")


def _profile():
    return current_user.student_profile


# ----------------------------------------------------------------- profile
@student_bp.get("/profile")
@student_only
def get_profile():
    p = _profile()
    return jsonify(
        {
            "full_name": current_user.full_name,
            "email": current_user.email,
            "branch": p.branch,
            "cgpa": p.cgpa,
            "graduation_year": p.graduation_year,
            "resume_path": p.resume_path,
        }
    )


@student_bp.put("/profile")
@student_only
def update_profile():
    data = json_body()
    p = _profile()
    if "full_name" in data:
        current_user.full_name = text(data["full_name"], "Full name", min_len=2, max_len=150, required=True)
    if "branch" in data:
        p.branch = text(data["branch"], "Branch", max_len=100)
    if "cgpa" in data:
        p.cgpa = number(data["cgpa"], "CGPA", float, 0, 10)
    if "graduation_year" in data:
        p.graduation_year = number(data["graduation_year"], "Graduation year", int, 2000, 2100)
    if "resume_path" in data:
        link = text(data["resume_path"], "Resume link", max_len=255)
        if link and not link.lower().startswith(("http://", "https://")):
            raise ValidationError("Resume link must start with http:// or https://")
        p.resume_path = link
    db.session.commit()
    return jsonify({"message": "Profile updated"})


@student_bp.delete("/account")
@student_only
def delete_account():
    db.session.delete(current_user._get_current_object())
    db.session.commit()
    return jsonify({"message": "Your account has been deleted"})


# ------------------------------------------------------------------ drives
@student_bp.get("/drives")
@student_only
def list_drives():
    profile = _profile()
    query = (
        PlacementDrive.query.join(CompanyProfile, PlacementDrive.company_profile_id == CompanyProfile.id)
        .join(User, CompanyProfile.user_id == User.id)
        .filter(
            PlacementDrive.status == "Approved",
            PlacementDrive.application_deadline > utcnow(),
            User.active.is_(True),
        )
    )
    like = search_like(request.args.get("q"))
    if like:
        query = query.filter(
            PlacementDrive.job_title.ilike(like) | CompanyProfile.company_name.ilike(like)
        )
    applied = {a.drive_id for a in profile.applications}
    only_eligible = request.args.get("eligible") == "true"

    result = []
    for drive in query.order_by(PlacementDrive.application_deadline).all():
        ok, reason = drive.check_eligibility(profile)
        if only_eligible and not ok:
            continue
        item = drive.to_dict()
        item.update({"eligible": ok, "ineligible_reason": reason, "applied": drive.id in applied})
        result.append(item)
    return jsonify(result)


@student_bp.post("/drives/<int:drive_id>/apply")
@student_only
def apply_to_drive(drive_id):
    drive = db.session.get(PlacementDrive, drive_id)
    if not drive or not drive.is_open or not drive.company.user.active:
        return error("Drive not found or no longer open", 404)
    profile = _profile()
    if Application.query.filter_by(student_profile_id=profile.id, drive_id=drive_id).first():
        return error("You have already applied to this drive", 409)
    ok, reason = drive.check_eligibility(profile)
    if not ok:
        return error(reason, 403)

    db.session.add(Application(student_profile_id=profile.id, drive_id=drive_id))
    db.session.commit()
    return jsonify({"message": "Application submitted"}), 201


# ------------------------------------------------------------ applications
@student_bp.get("/applications")
@student_only
def list_applications():
    apps = sorted(_profile().applications, key=lambda a: a.application_date, reverse=True)
    return jsonify(
        [
            {
                "application_id": a.id,
                "drive_id": a.drive_id,
                "company_name": a.drive.company.company_name,
                "job_title": a.drive.job_title,
                "status": a.status,
                "application_date": iso(a.application_date),
                "deadline": iso(a.drive.application_deadline),
            }
            for a in apps
        ]
    )


@student_bp.delete("/applications/<int:app_id>")
@student_only
def withdraw_application(app_id):
    application = db.session.get(Application, app_id)
    if not application or application.student_profile_id != _profile().id:
        return error("Application not found", 404)
    if application.status != "Applied":
        return error("Only applications that are still 'Applied' can be withdrawn")
    db.session.delete(application)
    db.session.commit()
    return jsonify({"message": "Application withdrawn"})


# ------------------------------------------------- CSV export (Celery job)
@student_bp.post("/export")
@student_only
def start_export():
    try:
        from tasks import export_applications_csv

        task = export_applications_csv.delay(current_user.id)
    except Exception as exc:  # noqa: BLE001  (Redis down, etc.)
        current_app.logger.warning("Could not queue export: %s", exc)
        return error("Background job service (Redis/Celery) is unavailable", 503)
    return jsonify({"message": "Export started", "task_id": task.id}), 202


@student_bp.get("/export/<task_id>")
@student_only
def export_status(task_id):
    try:
        result = AsyncResult(task_id, app=current_app.extensions["celery"])
        state = result.state
        payload = result.result if state == "SUCCESS" else None
    except Exception as exc:  # noqa: BLE001
        current_app.logger.warning("Could not read export result: %s", exc)
        return error("Background job service (Redis/Celery) is unavailable", 503)

    if state == "SUCCESS":
        if not isinstance(payload, dict) or payload.get("user_id") != current_user.id:
            return error("Export not found", 404)
        path = os.path.join(current_app.config["EXPORT_DIR"], os.path.basename(payload["file"]))
        if not os.path.exists(path):
            return error("Export file no longer exists", 404)
        return send_file(path, mimetype="text/csv", as_attachment=True, download_name="applications.csv")
    if state in ("FAILURE", "REVOKED"):
        return error("Export failed, please try again", 500)
    return jsonify({"status": state}), 202
