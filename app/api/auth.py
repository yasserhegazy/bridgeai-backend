from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.rate_limit import limiter
from app.core.security import create_access_token, get_current_user
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserOut
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
