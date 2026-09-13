import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from db.session import get_db
from core.security import decode_access_token
from models.user import User

bearer_scheme = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    credential_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )
    token = credentials.credentials
    try:
        user_id = decode_access_token(token)
    except jwt.PyJWTError:
        raise credential_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credential_exception
    return user
