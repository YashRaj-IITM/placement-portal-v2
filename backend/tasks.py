"""Background jobs (Celery + Redis)."""
import csv
import os
from datetime import timedelta

from celery import shared_task
from flask import current_app
from flask_mail import Message
from sqlalchemy import func

from extensions import db, mail
from models import (
    Application,
    CompanyProfile,
    PlacementDrive,
    StudentProfile,
    User,
    utcnow,
)


def _send_mail(subject, recipients, body, html=None, attachment=None):
    """Send an email; never raise (MailHog may not be running)."""
    msg = Message(subject=subject, recipients=recipients, body=body, html=html)
    if attachment:
        msg.attach(*attachment)
    try:
        mail.send(msg)
        return True
    except Exception as exc:  # noqa: BLE001
        current_app.logger.warning("Could not send email to %s: %s", recipients, exc)
        return False


def _export_dir():
    path = current_app.config["EXPORT_DIR"]
    os.makedirs(path, exist_ok=True)
    return path


# --------------------------------------------------------------------------
# 1. User triggered: export application history as CSV
# --------------------------------------------------------------------------
@shared_task(name="tasks.export_applications_csv")
def export_applications_csv(user_id):
    user = db.session.get(User, user_id)
    if not user or not user.student_profile:
        raise ValueError("Student not found")

    filename = f"applications_{user_id}_{utcnow().strftime('%Y%m%d%H%M%S')}.csv"
    path = os.path.join(_export_dir(), filename)

    rows = (
        Application.query.filter_by(student_profile_id=user.student_profile.id)
        .order_by(Application.application_date.desc())
        .all()
    )
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["Application ID", "Company", "Job Title", "Status", "Applied On (UTC)", "Deadline (UTC)"]
        )
        for a in rows:
            writer.writerow(
                [
                    a.id,
                    a.drive.company.company_name,
                    a.drive.job_title,
                    a.status,
                    a.application_date.strftime("%Y-%m-%d %H:%M"),
                    a.drive.application_deadline.strftime("%Y-%m-%d %H:%M"),
                ]
            )

    with open(path, "rb") as fh:
        _send_mail(
            "Your application history (CSV export)",
            [user.email],
            f"Hello {user.full_name},\n\nYour application history export is attached.\n\nPlacement Portal",
            attachment=(filename, "text/csv", fh.read()),
        )
    return {"user_id": user_id, "file": filename, "rows": len(rows)}


# --------------------------------------------------------------------------
# 2. Event triggered: notify a student when a company updates the status
# --------------------------------------------------------------------------
@shared_task(name="tasks.send_status_update_email")
def send_status_update_email(student_email, new_status, company_name, job_title):
    return _send_mail(
        f"Application update: {company_name}",
        [student_email],
        f"Hello,\n\nYour application for '{job_title}' at {company_name} "
        f"is now: {new_status}.\n\nPlacement Portal",
    )


# --------------------------------------------------------------------------
# 3. Scheduled (daily 08:00): deadline reminders
# --------------------------------------------------------------------------
@shared_task(name="tasks.daily_deadline_reminders")
def daily_deadline_reminders():
    now = utcnow()
    soon = now + timedelta(hours=48)
    drives = PlacementDrive.query.filter(
        PlacementDrive.status == "Approved",
        PlacementDrive.application_deadline > now,
        PlacementDrive.application_deadline <= soon,
    ).all()
    if not drives:
        return {"drives": 0, "emails": 0}

    students = (
        StudentProfile.query.join(User, StudentProfile.user_id == User.id)
        .filter(User.active.is_(True))
        .all()
    )
    sent = 0
    for profile in students:
        applied = {a.drive_id for a in profile.applications}
        todo = [
            d
            for d in drives
            if d.id not in applied and d.check_eligibility(profile)[0]
        ]
        if not todo:
            continue
        lines = "\n".join(
            f"- {d.job_title} at {d.company.company_name} "
            f"(closes {d.application_deadline.strftime('%d %b %Y %H:%M')} UTC)"
            for d in todo
        )
        body = (
            f"Hello {profile.user.full_name},\n\nThese drives you are eligible for "
            f"close within 48 hours:\n\n{lines}\n\nPlacement Portal"
        )
        if _send_mail("Placement drives closing soon", [profile.user.email], body):
            sent += 1
    return {"drives": len(drives), "emails": sent}


# --------------------------------------------------------------------------
# 4. Scheduled (1st of every month): monthly activity report for admins
# --------------------------------------------------------------------------
@shared_task(name="tasks.monthly_activity_report")
def monthly_activity_report():
    first_this = utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start = (first_this - timedelta(days=1)).replace(day=1)
    end = first_this
    label = start.strftime("%B %Y")

    drives_created = PlacementDrive.query.filter(
        PlacementDrive.created_at >= start, PlacementDrive.created_at < end
    ).count()
    apps = Application.query.filter(
        Application.application_date >= start, Application.application_date < end
    )
    total_apps = apps.count()
    by_status = dict(
        db.session.query(Application.status, func.count(Application.id))
        .filter(Application.application_date >= start, Application.application_date < end)
        .group_by(Application.status)
        .all()
    )
    top = (
        db.session.query(CompanyProfile.company_name, func.count(Application.id))
        .join(PlacementDrive, PlacementDrive.company_profile_id == CompanyProfile.id)
        .join(Application, Application.drive_id == PlacementDrive.id)
        .filter(Application.application_date >= start, Application.application_date < end)
        .group_by(CompanyProfile.id)
        .order_by(func.count(Application.id).desc())
        .limit(5)
        .all()
    )

    rows = "".join(f"<tr><td>{n}</td><td>{c}</td></tr>" for n, c in top) or (
        "<tr><td colspan='2'>No applications</td></tr>"
    )
    html = f"""
    <h2>Placement Portal - Monthly Report ({label})</h2>
    <ul>
      <li>Drives created: <b>{drives_created}</b></li>
      <li>Applications received: <b>{total_apps}</b></li>
      <li>Shortlisted: <b>{by_status.get('Shortlisted', 0)}</b>,
          Selected: <b>{by_status.get('Selected', 0)}</b>,
          Rejected: <b>{by_status.get('Rejected', 0)}</b></li>
    </ul>
    <h3>Top companies by applications</h3>
    <table border="1" cellpadding="6" cellspacing="0">
      <tr><th>Company</th><th>Applications</th></tr>{rows}
    </table>"""

    path = os.path.join(_export_dir(), f"monthly_report_{start.strftime('%Y_%m')}.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)

    admins = [u.email for u in User.query.filter_by(active=True).all() if u.role_name == "admin"]
    if admins:
        _send_mail(
            f"Placement Portal monthly report - {label}",
            admins,
            f"Monthly report for {label}: {drives_created} drives, {total_apps} applications.",
            html=html,
        )
    return {"month": label, "drives": drives_created, "applications": total_apps, "file": path}
