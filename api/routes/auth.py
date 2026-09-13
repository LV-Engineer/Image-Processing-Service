from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.session import get_db
from models.user import User
from schemas.user import SignupRequest, LoginRequest, UserResponse, TokenResponse
from core.security import hash_password, verify_password, create_access_token
from api.deps import get_current_user

router = APIRouter(prefix='/auth', tags=['auth'])

@router.post('/signup', response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> UserResponse:
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail='Email already registered')

    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)

@router.post('/login', response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail='Invalide credentials')

    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token)

@router.get('/me', response_model=UserResponse)
def read_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)