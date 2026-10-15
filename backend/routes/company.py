from flask import Blueprint, current_app, jsonify
from flask_security import current_user

from extensions import db
from models import Application, PlacementDrive, iso, utcnow
from utils import (
    ValidationError,
    csv_list,
    error,
    json_body,
    number,
    parse_datetime,
    text,
    token_roles,
)

company_bp = Blueprint("company_api", __name__, url_prefix="/api/company")
company_only = token_roles("company")

APPLICATION_UPDATES = ("Shortlisted", "Selected", "Rejected")


def _profile():
    return current_user.company_profile


def _own_drive(drive_id):
    drive = db.session.get(PlacementDrive, drive_id)
    if drive and drive.company_profile_id == _profile().id:
        return drive
    return None


def _drive_fields(data, partial):
    """Validate drive input and return a dict of model fields."""
    out = {}
    if not partial or "job_title" in data:
        out["job_title"] = text(data.get("job_title"), "Job title", min_len=3, max_len=150, required=True)
    if not partial or "job_description" in data:
        out["job_description"] = text(
            data.get("job_description"), "Job description", min_len=10, max_len=5000, required=True
        )
    if "min_cgpa" in data or not partial:
        out["min_cgpa"] = number(data.get("min_cgpa"), "Minimum CGPA", float, 0, 10) or 0.0
    if "eligible_branches" in data or not partial:
        out["eligible_branches"] = csv_list(data.get("eligible_branches"), "Eligible branches")
    if "eligible_years" in data or not partial:
        years = csv_list(data.get("eligible_years"), "Eligible years")
        for y in filter(None, years.split(",")):
            number(y, "Eligible year", int, 2000, 2100)
        out["eligible_years"] = years
    if not partial or "application_deadline" in data:
        deadline = parse_datetime(data.get("application_deadline"), "Application deadline")
        if deadline <= utcnow():
            raise ValidationError("Application deadline must be in the future")
        out["application_deadline"] = deadline
    return out


# ----------------------------------------------------------------- profile
@company_bp.get("/profile")
@company_only
def get_profile():
    p = _profile()
    return jsonify(
        {
            "company_name": p.company_name,
            "hr_contact": p.hr_contact,
            "website": p.website,
            "full_name": current_user.full_name,
            "email": current_user.email,
            "is_approved": current_user.is_approved,
        }
    )


@company_bp.put("/profile")
@company_only
def update_profile():
    data = json_body()
    p = _profile()
    if "company_name" in data:
        p.company_name = text(data["company_name"], "Company name", min_len=2, max_len=150, required=True)
    if "hr_contact" in data:
        p.hr_contact = text(data["hr_contact"], "HR contact", max_len=150)
    if "website" in data:
        website = text(data["website"], "Website", max_len=255)
        if website and not website.lower().startswith(("http://", "https://")):
            raise ValidationError("Website must start with http:// or https://")
        p.website = website
    db.session.commit()
    return jsonify({"message": "Profile updated"})


# ------------------------------------------------------------------ drives
@company_bp.get("/drives")
@company_only
def list_drives():
    drives = sorted(_profile().drives, key=lambda d: d.created_at, reverse=True)
    return jsonify([d.to_dict() for d in drives])


@company_bp.post("/drives")
@company_only
def create_drive():
    if not current_user.is_approved:
        return error("Your company must be approved by the admin before creating drives", 403)
    fields = _drive_fields(json_body(), partial=False)
    drive = PlacementDrive(company_profile_id=_profile().id, status="Pending", **fields)
    db.session.add(drive)
    db.session.commit()
    return jsonify({"message": "Drive created. Awaiting admin approval.", "drive": drive.to_dict()}), 201


@company_bp.get("/drives/<int:drive_id>")
@company_only
def get_drive(drive_id):
    drive = _own_drive(drive_id)
    if not drive:
        return error("Drive not found", 404)
    return jsonify(drive.to_dict())


@company_bp.put("/drives/<int:drive_id>")
@company_only
def update_drive(drive_id):
    drive = _own_drive(drive_id)
    if not drive:
        return error("Drive not found", 404)
    if drive.status == "Closed":
        return error("A closed drive cannot be edited")
    fields = _drive_fields(json_body(), partial=True)
    for key, value in fields.items():
        setattr(drive, key, value)
    if drive.status in ("Approved", "Rejected"):
        drive.status = "Pending"  # edits need to be re-approved by the admin
    db.session.commit()
    return jsonify({"message": "Drive updated. It needs admin approval again.", "drive": drive.to_dict()})


@company_bp.delete("/drives/<int:drive_id>")
@company_only
def delete_drive(drive_id):
    drive = _own_drive(drive_id)
    if not drive:
        return error("Drive not found", 404)
    db.session.delete(drive)
    db.session.commit()
    return jsonify({"message": "Drive deleted"})


# ------------------------------------------------------------ applications
@company_bp.get("/drives/<int:drive_id>/applications")
@company_only
def drive_applications(drive_id):
    drive = _own_drive(drive_id)
    if not drive:
        return error("Drive not found", 404)
    result = [
        {
            "application_id": a.id,
            "student_name": a.student.user.full_name,
            "student_email": a.student.user.email,
            "branch": a.student.branch,
            "cgpa": a.student.cgpa,
            "graduation_year": a.student.graduation_year,
            "resume_path": a.student.resume_path,
            "status": a.status,
            "application_date": iso(a.application_date),
        }
        for a in drive.applications
    ]
    return jsonify(result)


@company_bp.put("/applications/<int:app_id>/status")
@company_only
def update_application_status(app_id):
    status = json_body().get("status")
    if status not in APPLICATION_UPDATES:
        return error(f"status must be one of {', '.join(APPLICATION_UPDATES)}")
    application = db.session.get(Application, app_id)
    if not application or application.drive.company_profile_id != _profile().id:
        return error("Application not found", 404)

    application.status = status
    db.session.commit()

    # Background email; the API must still succeed if Redis is down
    try:
        from tasks import send_status_update_email

        send_status_update_email.delay(
            application.student.user.email,
            status,
            application.drive.company.company_name,
            application.drive.job_title,
        )
    except Exception as exc:  # noqa: BLE001
        current_app.logger.warning("Could not queue status email: %s", exc)
    return jsonify({"message": f"Application marked {status}"})
