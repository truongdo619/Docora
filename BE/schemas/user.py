from pydantic import BaseModel
from typing import Optional
class UserBase(BaseModel):
    username: str
    email: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int

    class Config:
        orm_mode = True

# class UserCreate(BaseModel):
#     username: str
#     password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenRefresh(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenData(BaseModel):
    username: str

class ParaUpdate(BaseModel):
    paragraphs: list

class ResetRequest(BaseModel):
    email: str

class ResetPassword(BaseModel):
    token: str
    new_password:str

class UpdateUSerInfor(BaseModel):
    username: Optional[str]  = None
    password: Optional[str] = None
    email: Optional[str] = None
    fullname: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    workplace: Optional[str] = None

class ChangePassword(BaseModel):
    old_password:str
    new_password:str
    
class ContactSupport(BaseModel):
    name: str
    email: str
    content: str

