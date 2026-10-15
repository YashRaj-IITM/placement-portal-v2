"""End-to-end smoke test using Flask's test client (no Redis / SMTP needed).

    python smoke_test.py
"""
import shutil
from datetime import datetime, timedelta, timezone

from app import create_app
from config import TestConfig

app = create_app(TestConfig)
client = app.test_client()
HDR = "Authentication-Token"
passed = 0


def check(label, response, expected):
    global passed
    ok = response.status_code == expected
    print(("PASS" if ok else "FAIL"), f"[{response.status_code}]", label)
    if not ok:
        print("     body:", response.get_data(as_text=True)[:300])
        raise SystemExit(1)
    passed += 1
    return response


def login(email, password):
    r = check(f"login {email}", client.post("/api/auth/login", json={"email": email, "password": password}), 200)
    return {HDR: r.get_json()["token"]}


deadline = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()

# ---- authentication ------------------------------------------------------
check("no token -> 401", client.get("/api/admin/stats"), 401)
check("bad login -> 401", client.post("/api/auth/login", json={"email": "x@y.com", "password": "nope"}), 401)
check("weak password rejected", client.post("/api/auth/register/student",
      json={"email": "s@x.com", "password": "123", "full_name": "S"}), 400)
check("register student", client.post("/api/auth/register/student",
      json={"email": "stu@x.com", "password": "student123", "full_name": "Stu Dent"}), 201)
check("duplicate email rejected", client.post("/api/auth/register/student",
      json={"email": "stu@x.com", "password": "student123", "full_name": "Stu Dent"}), 400)
check("register company", client.post("/api/auth/register/company",
      json={"email": "hr@acme.com", "password": "company123", "full_name": "HR Person",
            "company_name": "Acme Corp", "website": "https://acme.com"}), 201)

admin = login(app.config["ADMIN_EMAIL"], app.config["ADMIN_PASSWORD"])
student = login("stu@x.com", "student123")
company = login("hr@acme.com", "company123")
check("/me works with token", client.get("/api/auth/me", headers=student), 200)

# ---- role based access -----------------------------------------------------
check("student cannot reach admin API", client.get("/api/admin/stats", headers=student), 403)
check("company cannot reach student API", client.get("/api/student/profile", headers=company), 403)
check("admin stats", client.get("/api/admin/stats", headers=admin), 200)

# ---- company flow ------------------------------------------------------------
drive_body = {"job_title": "Software Engineer", "job_description": "Build and ship backend services.",
              "eligible_branches": "CSE,ECE", "min_cgpa": 7, "eligible_years": "2026",
              "application_deadline": deadline}
check("unapproved company cannot create drive", client.post("/api/company/drives", json=drive_body, headers=company), 403)
cid = client.get("/api/admin/companies", headers=admin).get_json()[0]["id"]
check("admin approves company", client.put(f"/api/admin/companies/{cid}/status", json={"action": "approve"}, headers=admin), 200)
check("past deadline rejected", client.post("/api/company/drives",
      json={**drive_body, "application_deadline": "2020-01-01T00:00:00"}, headers=company), 400)
r = check("create drive", client.post("/api/company/drives", json=drive_body, headers=company), 201)
drive_id = r.get_json()["drive"]["id"]
check("update drive", client.put(f"/api/company/drives/{drive_id}", json={"min_cgpa": 7.5}, headers=company), 200)
check("student sees no pending drives", client.get("/api/student/drives", headers=student), 200)
assert client.get("/api/student/drives", headers=student).get_json() == []
check("admin approves drive", client.put(f"/api/admin/drives/{drive_id}/status", json={"status": "Approved"}, headers=admin), 200)

# ---- student flow --------------------------------------------------------------
drives = client.get("/api/student/drives", headers=student).get_json()
assert len(drives) == 1 and drives[0]["eligible"] is False, drives
check("ineligible student cannot apply", client.post(f"/api/student/drives/{drive_id}/apply", headers=student), 403)
check("update profile", client.put("/api/student/profile", json={"branch": "CSE", "cgpa": 8.2,
      "graduation_year": 2026, "resume_path": "https://example.com/cv"}, headers=student), 200)
check("bad cgpa rejected", client.put("/api/student/profile", json={"cgpa": 14}, headers=student), 400)
check("apply", client.post(f"/api/student/drives/{drive_id}/apply", headers=student), 201)
check("duplicate apply blocked", client.post(f"/api/student/drives/{drive_id}/apply", headers=student), 409)

apps = client.get("/api/student/applications", headers=student).get_json()
app_id = apps[0]["application_id"]
check("withdraw application", client.delete(f"/api/student/applications/{app_id}", headers=student), 200)
check("re-apply", client.post(f"/api/student/drives/{drive_id}/apply", headers=student), 201)
app_id = client.get("/api/student/applications", headers=student).get_json()[0]["application_id"]

# ---- company handles applicants (triggers Celery email task, eager mode) -----------
check("company sees applicants", client.get(f"/api/company/drives/{drive_id}/applications", headers=company), 200)
check("invalid status rejected", client.put(f"/api/company/applications/{app_id}/status", json={"status": "Foo"}, headers=company), 400)
check("shortlist applicant", client.put(f"/api/company/applications/{app_id}/status", json={"status": "Shortlisted"}, headers=company), 200)
check("cannot withdraw after shortlist", client.delete(f"/api/student/applications/{app_id}", headers=student), 400)

# ---- Celery export job (eager mode) -------------------------------------------------------
r = check("start CSV export", client.post("/api/student/export", headers=student), 202)
task_id = r.get_json()["task_id"]
resp = client.get(f"/api/student/export/{task_id}", headers=student)
print("INFO export status:", resp.status_code, "(200 = CSV file returned)")

# ---- admin CRUD ----------------------------------------------------------------------------
check("admin lists students", client.get("/api/admin/students?q=stu", headers=admin), 200)
check("admin lists applications", client.get("/api/admin/applications", headers=admin), 200)
check("admin deletes drive", client.delete(f"/api/admin/drives/{drive_id}", headers=admin), 200)

# ---- logout invalidates the token -------------------------------------------------------------
check("logout", client.post("/api/auth/logout", headers=student), 200)
check("token invalid after logout", client.get("/api/auth/me", headers=student), 401)

shutil.rmtree(app.config["EXPORT_DIR"], ignore_errors=True)
print(f"\nAll {passed} checks passed")
