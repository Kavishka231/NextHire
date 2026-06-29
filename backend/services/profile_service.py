from sqlalchemy.orm import Session

from models.profile import UserProfile
from models.user import User
from schemas.profile import ProfileUpdate


class ProfileService:
    @staticmethod
    def get_or_create(db: Session, user: User) -> UserProfile:
        profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
        if profile:
            return profile

        profile = UserProfile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def update(db: Session, user: User, data: ProfileUpdate) -> UserProfile:
        profile = ProfileService.get_or_create(db, user)
        updates = data.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(profile, field, value)
        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def to_response(profile: UserProfile, user: User) -> dict:
        payload = {
            "id": profile.id,
            "user_id": profile.user_id,
            "email": user.email,
            "full_name": user.full_name,
        }

        fields = [
            "avatar_url", "headline", "location", "bio", "open_to_work",
            "phone", "linkedin_url", "github_url", "portfolio_url",
            "desired_job_title", "preferred_job_type", "preferred_work_style",
            "preferred_locations", "expected_salary_min", "expected_salary_max",
            "industries", "available_from", "available_immediately",
            "resume_file_name", "resume_url", "resume_visible_to_recruiters",
            "work_experience", "education", "skills", "certifications",
            "projects", "languages", "volunteer_experience", "achievements",
            "created_at", "updated_at",
        ]
        for field in fields:
            payload[field] = getattr(profile, field)

        completeness, missing = ProfileService.completeness(payload)
        payload["completeness"] = completeness
        payload["missing_items"] = missing
        return payload

    @staticmethod
    def completeness(profile: dict) -> tuple[int, list[str]]:
        checks = [
            ("Add a profile photo", bool(profile.get("avatar_url"))),
            ("Add a professional headline", bool(profile.get("headline"))),
            ("Add your location", bool(profile.get("location"))),
            ("Write your about section", bool(profile.get("bio"))),
            ("Add a phone number", bool(profile.get("phone"))),
            ("Add LinkedIn, GitHub, or portfolio", any([
                profile.get("linkedin_url"),
                profile.get("github_url"),
                profile.get("portfolio_url"),
            ])),
            ("Add work experience", bool(profile.get("work_experience"))),
            ("Add education", bool(profile.get("education"))),
            ("Add skills", bool(profile.get("skills"))),
            ("Add certifications", bool(profile.get("certifications"))),
            ("Add projects", bool(profile.get("projects"))),
            ("Add languages", bool(profile.get("languages"))),
            ("Set job preferences", any([
                profile.get("desired_job_title"),
                profile.get("preferred_job_type"),
                profile.get("preferred_work_style"),
                profile.get("preferred_locations"),
            ])),
            ("Add expected salary", bool(profile.get("expected_salary_min") or profile.get("expected_salary_max"))),
            ("Add your resume link", bool(profile.get("resume_url") or profile.get("resume_file_name"))),
        ]
        completed = sum(1 for _, ok in checks if ok)
        missing = [label for label, ok in checks if not ok]
        return round((completed / len(checks)) * 100), missing
