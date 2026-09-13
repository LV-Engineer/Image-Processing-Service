from pydantic import BaseModel, EmailStr

class SignupRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: EmailStr

    model_config = {'from_attributes': True}

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'