import datetime
from pydantic import BaseModel, EmailStr, field_validator

class LoginUser(BaseModel):
    email: EmailStr
    password: str   
    
class RegisterUser(BaseModel):
    login: str
    email: EmailStr
    dob:datetime.date
    password: str | bytes 

class ShowUser(BaseModel):
    
    id: int
    login: str
    email: EmailStr
    dob: datetime.date
    
class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str