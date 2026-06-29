from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from core.dependencies import get_current_user
from models.user import User
from schemas.company import CompanyResponse, CompanyUpdate
from services.notification_service import notify_admins

router = APIRouter(prefix="/company", tags=["Company"])


@router.get("/me", response_model=CompanyResponse)
def get_company(current_user: User = Depends(get_current_user)):
    if current_user.account_type != "company":
        raise HTTPException(status_code=403, detail="This is not a company account")
    return current_user


@router.put("/me", response_model=CompanyResponse)
def update_company(
    data: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.account_type != "company":
        raise HTTPException(status_code=403, detail="This is not a company account")
    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(current_user, field, value)
    if current_user.company_status == "approved":
        current_user.company_status = "pending"
        current_user.company_verified = False
        notify_admins(
            db,
            "Company details changed",
            f"{current_user.company_name or current_user.full_name} updated company details and needs review.",
            "company_pending",
        )
    db.commit()
    db.refresh(current_user)
    return current_user
