from datetime import datetime, timezone

from flask_security import RoleMixin, SQLAlchemyUserDatastore, UserMixin

from extensions import db

# Allowed values (also used by the API for validation)
DRIVE_STATUSES = ("Pending", "Approved", "Rejected", "Closed")
APPLICATION_STATUSES = ("Applied", "Shortlisted", "Selected", "Rejected")


def utcnow():
    """Naive UTC datetime (all datetimes in the DB are UTC)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(dt):
    """ISO string with a trailing Z so browsers parse it as UTC."""
    return dt.isoformat() + "Z" if dt else None


roles_users = db.Table(
    "roles_users",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id"), primary_key=True),
)


class Role(db.Model, RoleMixin):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))
    permissions = db.Column(db.UnicodeText)


class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    # Flask-Security: `active` False means blacklisted / cannot log in
    active = db.Column(db.Boolean, default=True, nullable=False)
    fs_uniquifier = db.Column(db.String(64), unique=True, nullable=False)
    # Companies must be approved by the admin before they can post drives
    is_approved = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    roles = db.relationship(
        "Role", secondary=roles_users, backref=db.backref("users", lazy="dynamic")
    )
    company_profile = db.relationship(
        "CompanyProfile", backref="user", uselist=False, cascade="all, delete-orphan"
    )
    student_profile = db.relationship(
        "StudentProfile", backref="user", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def role_name(self):
        return self.roles[0].name if self.roles else None

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role_name,
            "is_approved": self.is_approved,
            "active": self.active,
        }


class CompanyProfile(db.Model):
    __tablename__ = "company_profile"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True
    )
    company_name = db.Column(db.String(150), nullable=False)
    hr_contact = db.Column(db.String(150))
    website = db.Column(db.String(255))

    drives = db.relationship(
        "PlacementDrive", backref="company", cascade="all, delete-orphan", lazy=True
    )


class StudentProfile(db.Model):
    __tablename__ = "student_profile"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True
    )
    branch = db.Column(db.String(100))
    cgpa = db.Column(db.Float)
    graduation_year = db.Column(db.Integer)
    resume_path = db.Column(db.String(255))

    applications = db.relationship(
        "Application", backref="student", cascade="all, delete-orphan", lazy=True
    )


class PlacementDrive(db.Model):
    __tablename__ = "placement_drive"
    id = db.Column(db.Integer, primary_key=True)
    company_profile_id = db.Column(
        db.Integer, db.ForeignKey("company_profile.id"), nullable=False
    )
    job_title = db.Column(db.String(150), nullable=False)
    job_description = db.Column(db.Text, nullable=False)
    eligible_branches = db.Column(db.String(255), default="")  # comma separated
    min_cgpa = db.Column(db.Float, default=0.0)
    eligible_years = db.Column(db.String(255), default="")  # comma separated
    application_deadline = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    status = db.Column(db.String(20), default="Pending", nullable=False)

    applications = db.relationship(
        "Application", backref="drive", cascade="all, delete-orphan", lazy=True
    )

    @property
    def is_open(self):
        return self.status == "Approved" and self.application_deadline > utcnow()

    def check_eligibility(self, profile):
        """Return (ok, reason) for a StudentProfile."""
        if profile is None:
            return False, "Complete your profile first"
        if self.min_cgpa and (profile.cgpa is None or profile.cgpa < self.min_cgpa):
            return False, f"Minimum CGPA {self.min_cgpa} required"
        branches = [b.strip().lower() for b in (self.eligible_branches or "").split(",") if b.strip()]
        if branches and (not profile.branch or profile.branch.strip().lower() not in branches):
            return False, "Your branch is not eligible"
        years = [y.strip() for y in (self.eligible_years or "").split(",") if y.strip()]
        if years and (not profile.graduation_year or str(profile.graduation_year) not in years):
            return False, "Your graduation year is not eligible"
        return True, ""

    def to_dict(self):
        return {
            "id": self.id,
            "company_name": self.company.company_name if self.company else "",
            "job_title": self.job_title,
            "job_description": self.job_description,
            "eligible_branches": self.eligible_branches or "",
            "min_cgpa": self.min_cgpa or 0,
            "eligible_years": self.eligible_years or "",
            "deadline": iso(self.application_deadline),
            "created_at": iso(self.created_at),
            "status": self.status,
            "applicant_count": len(self.applications),
        }


class Application(db.Model):
    __tablename__ = "application"
    __table_args__ = (
        db.UniqueConstraint("student_profile_id", "drive_id", name="uq_student_drive"),
    )
    id = db.Column(db.Integer, primary_key=True)
    student_profile_id = db.Column(
        db.Integer, db.ForeignKey("student_profile.id"), nullable=False
    )
    drive_id = db.Column(db.Integer, db.ForeignKey("placement_drive.id"), nullable=False)
    application_date = db.Column(db.DateTime, default=utcnow)
    status = db.Column(db.String(20), default="Applied", nullable=False)


# Flask-Security datastore (used by routes, seeding and the Security extension)
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
