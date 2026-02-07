from fastapi import APIRouter, Depends, HTTPException, Request, status, File, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.rate_limit import limiter
from app.core.security import get_current_user, get_current_user_allow_null_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import (
    UserCreate,
    UserOut,
    ForgotPasswordRequest,
    VerifyOTPRequest,
    ResetPasswordRequest,
    UserProfileUpdate,
    PasswordChangeRequest,
    GoogleLoginRequest,
    RoleSelectionRequest,
)
from app.services.auth_service import AuthService
from app.services.file_storage_service import FileStorageService

router = APIRouter(tags=["Authentication"])


@router.post("/google", response_model=Token)
@limiter.limit("20/minute")
def google_login(
    request: Request,
    login_data: GoogleLoginRequest,
    db: Session = Depends(get_db),
):
    from app.core.config import settings
    
    return AuthService.google_login(
        db, login_data.token, settings.GOOGLE_CLIENT_ID
    )


@router.post("/register", response_model=UserOut)
@limiter.limit("1000/hour")
def register_user(request: Request, data: UserCreate, db: Session = Depends(get_db)):
    return AuthService.register_user(
        db, data.full_name, data.email, data.password
    )


@router.post("/token", response_model=Token)
@limiter.limit("5/minute")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    return AuthService.authenticate_user(db, form_data.username, form_data.password)


@router.patch("/role", response_model=Token)
@limiter.limit("10/minute")
def select_role(
    request: Request,
    data: RoleSelectionRequest,
    current_user: User = Depends(get_current_user_allow_null_role),
    db: Session = Depends(get_db),
):
    """
    Select user role after registration or OAuth login.
    Can only be called once when role is NULL.
    Returns new access token with role included.
    """
    return AuthService.select_role(db, current_user, data.role)


@router.get("/me", response_model=UserOut)
@limiter.limit("30/minute")
def get_me(request: Request, current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/users/{user_id}", response_model=UserOut)
def get_user_by_id(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get user details by ID. Requires authentication."""
    return AuthService.get_user_by_id(db, user_id)


@router.post("/forgot-password")
@limiter.limit("3/minute")
def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """Step 1: Check email and send OTP."""
    return AuthService.initiate_password_reset(db, data.email)


@router.post("/verify-otp")
@limiter.limit("5/minute")
def verify_otp(
    request: Request,
    data: VerifyOTPRequest,
    db: Session = Depends(get_db),
):
    """Step 2: Verify the OTP code."""
    return AuthService.verify_otp(db, data.email, data.otp_code)


@router.post("/reset-password")
@limiter.limit("3/minute")
def reset_password(
    request: Request,
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """Step 3: Reset the password after verification."""
    return AuthService.reset_password(db, data.email, data.otp_code, data.new_password)


@router.put("/me", response_model=UserOut)
@limiter.limit("10/minute")
def update_profile(
    request: Request,
    data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update current user's profile information."""
    return AuthService.update_profile(db, current_user, data.full_name)


@router.post("/change-password")
@limiter.limit("5/minute")
def change_password(
    request: Request,
    data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change password for authenticated user."""
    return AuthService.change_password(
        db, current_user, data.current_password, data.new_password
    )


@router.post("/avatar")
@limiter.limit("10/minute")
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload user avatar image."""
    # Read file contents
    contents = await file.read()
    
    # Upload via service
    result = FileStorageService.upload_avatar(file, current_user, contents)
    
    # Update user's avatar_url in database
    current_user.avatar_url = result["avatar_url"]
    db.commit()
    db.refresh(current_user)
    
    return result


@router.delete("/avatar")
@limiter.limit("10/minute")
def delete_avatar(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete user avatar."""
    result = FileStorageService.delete_avatar(current_user)
    
    # Clear avatar_url in database
    current_user.avatar_url = None
    db.commit()
    
    return result
