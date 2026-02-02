from fastapi import APIRouter, Depends, HTTPException, Request, status, File, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.rate_limit import limiter
from app.core.security import create_access_token, get_current_user
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.token import Token
from app.schemas.user import (
    UserCreate,
    UserOut,
    ForgotPasswordRequest,
    VerifyOTPRequest,
    ResetPasswordRequest,
    UserProfileUpdate,
    PasswordChangeRequest,
)
from app.utils.hash import hash_password, verify_password
from google.oauth2 import id_token
from google.auth.transport import requests
from app.schemas.user import GoogleLoginRequest

router = APIRouter(tags=["Authentication"])


@router.post("/google", response_model=Token)
@limiter.limit("20/minute")
def google_login(
    request: Request,
    login_data: GoogleLoginRequest,
    db: Session = Depends(get_db),
):
    try:
        from app.core.config import settings
        CLIENT_ID = settings.GOOGLE_CLIENT_ID
        
        # Verify the token
        # strictly verify the token is intended for our app
        # Add clock_skew_in_seconds to handle small time differences between client and server
        id_info = id_token.verify_oauth2_token(
            login_data.token, 
            requests.Request(), 
            CLIENT_ID,
            clock_skew_in_seconds=10  # Allow 10 seconds of clock skew tolerance
        )

        # Get user info
        email = id_info.get("email")
        google_id = id_info.get("sub")
        name = id_info.get("name")
        picture = id_info.get("picture")

        if not email:
            raise HTTPException(status_code=400, detail="Invalid Google token: no email found")

        # Check if user exists
        user = db.query(User).filter((User.email == email) | (User.google_id == google_id)).first()

        if not user:
            # Create new user
            user = User(
                full_name=name,
                email=email,
                google_id=google_id,
                avatar_url=picture,
                role=login_data.role,
                password_hash=None,  # No password for Google users
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # Update existing user if needed (e.g. add google_id if missing)
            if not user.google_id:
                user.google_id = google_id
                db.add(user)
            
            # Update avatar if changed
            if picture and user.avatar_url != picture:
                user.avatar_url = picture
                db.add(user)
                
            db.commit()

        # Create access token
        # Ensure user has a role, default to client if None
        user_role = user.role if user.role is not None else UserRole.client
        token = create_access_token({"sub": str(user.id), "role": user_role})
        
        return {"access_token": token, "token_type": "bearer", "role": user_role.value}

    except ValueError as e:
        # Invalid token
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {str(e)}")



@router.post("/register", response_model=UserOut)
@limiter.limit("1000/hour")
def register_user(request: Request, data: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        full_name=data.full_name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Check for pending invitations and create notifications
    from app.models.invitation import Invitation
    from app.models.notification import Notification, NotificationType
    from app.models.team import Team

    pending_invitations = (
        db.query(Invitation)
        .filter(Invitation.email == data.email, Invitation.status == "pending")
        .all()
    )

    for invitation in pending_invitations:
        # Get team details for the notification message
        team = db.query(Team).filter(Team.id == invitation.team_id).first()
        if team and invitation.inviter:
            notification = Notification(
                user_id=user.id,
                type=NotificationType.TEAM_INVITATION,
                reference_id=invitation.team_id,
                title="Team Invitation",
                message=f"{invitation.inviter.full_name} has invited you to join the team '{team.name}' as {invitation.role}.",
                is_read=False,
            )
            db.add(notification)

    db.commit()

    return user


@router.post("/token", response_model=Token)
@limiter.limit("5/minute")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    # Ensure user has a role, default to client if None
    user_role = user.role if user.role is not None else UserRole.client

    token = create_access_token({"sub": str(user.id), "role": user_role})
    return {"access_token": token, "token_type": "bearer", "role": user_role.value}


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
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.post("/forgot-password")
@limiter.limit("3/minute")
def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """Step 1: Check email and send OTP."""
    # Check if user exists
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This email is not registered with BridgeAI."
        )

    # Generate 6-digit OTP
    import random
    import string
    from datetime import datetime, timedelta
    from app.models.user_otp import UserOTP
    from app.utils.email import send_password_reset_email

    otp_code = "".join(random.choices(string.digits, k=6))
    expires_at = datetime.utcnow() + timedelta(minutes=15)

    # Store in DB (delete old ones first)
    db.query(UserOTP).filter(UserOTP.email == data.email).delete()
    
    db_otp = UserOTP(
        email=data.email,
        otp_code=otp_code,
        expires_at=expires_at
    )
    db.add(db_otp)
    db.commit()

    # Send email
    send_password_reset_email(data.email, otp_code)

    return {"message": "Verification code sent to your email."}


@router.post("/verify-otp")
@limiter.limit("5/minute")
def verify_otp(
    request: Request,
    data: VerifyOTPRequest,
    db: Session = Depends(get_db),
):
    """Step 2: Verify the OTP code."""
    from app.models.user_otp import UserOTP

    db_otp = db.query(UserOTP).filter(
        UserOTP.email == data.email,
        UserOTP.otp_code == data.otp_code
    ).first()

    if not db_otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code."
        )

    if db_otp.is_expired:
        db.delete(db_otp)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired."
        )

    return {"message": "Verification successful."}


@router.post("/reset-password")
@limiter.limit("3/minute")
def reset_password(
    request: Request,
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """Step 3: Reset the password after verification."""
    from app.models.user_otp import UserOTP

    # 1. Verify OTP again (stateless verification for the final step)
    db_otp = db.query(UserOTP).filter(
        UserOTP.email == data.email,
        UserOTP.otp_code == data.otp_code
    ).first()

    if not db_otp or db_otp.is_expired:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification session."
        )

    # 2. Get User
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )

    # 3. Update Password
    user.password_hash = hash_password(data.new_password)
    
    # 4. Clean up OTP
    db.delete(db_otp)
    
    db.commit()

    return {"message": "Password reset successfully. You can now log in."}


@router.put("/me", response_model=UserOut)
@limiter.limit("10/minute")
def update_profile(
    request: Request,
    data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update current user's profile information."""
    # Update full name
    current_user.full_name = data.full_name
    
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.post("/change-password")
@limiter.limit("5/minute")
def change_password(
    request: Request,
    data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change password for authenticated user."""
    # Check if user has a password (not a Google OAuth user)
    if not current_user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change password for Google OAuth users. Your account uses Google Sign-In."
        )
    
    # Verify current password
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.password_hash = hash_password(data.new_password)
    
    db.commit()
    
    return {"message": "Password changed successfully"}


@router.post("/avatar")
@limiter.limit("10/minute")
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload user avatar image."""
    import os
    import uuid
    from pathlib import Path
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only JPEG, PNG, and WebP images are allowed."
        )
    
    # Validate file size (max 5MB)
    max_size = 5 * 1024 * 1024  # 5MB
    contents = await file.read()
    if len(contents) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size too large. Maximum size is 5MB."
        )
    
    # Create avatars directory if it doesn't exist
    avatars_dir = Path("public/avatars")
    avatars_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = avatars_dir / unique_filename
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(contents)
    
    # Delete old avatar if it exists and is not a Google avatar
    if current_user.avatar_url and not current_user.avatar_url.startswith("http"):
        old_file_path = Path(current_user.avatar_url)
        if old_file_path.exists():
            try:
                os.remove(old_file_path)
            except Exception:
                pass  # Ignore errors when deleting old file
    
    # Update user's avatar_url in database
    avatar_url = f"public/avatars/{unique_filename}"
    current_user.avatar_url = avatar_url
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "message": "Avatar uploaded successfully",
        "avatar_url": avatar_url
    }


@router.delete("/avatar")
@limiter.limit("10/minute")
def delete_avatar(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete user avatar."""
    import os
    from pathlib import Path
    
    if not current_user.avatar_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No avatar to delete"
        )
    
    # Don't delete Google avatars
    if current_user.avatar_url.startswith("http"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete Google avatar"
        )
    
    # Delete file from disk
    file_path = Path(current_user.avatar_url)
    if file_path.exists():
        try:
            os.remove(file_path)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete avatar file: {str(e)}"
            )
    
    # Clear avatar_url in database
    current_user.avatar_url = None
    
    db.commit()
    
    return {"message": "Avatar deleted successfully"}

