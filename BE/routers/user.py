
import json

from datetime import timedelta, datetime

from fastapi import APIRouter
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from sqlalchemy.orm import Session
from crud.psql import user as user_crud

from models.psql import user as user_model
from schemas import user  as user_schemas 

from utils import utils

from .dependencies import get_current_user, get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
dev_account_id = 2335
HIGHLIGHTED_DOCUMENT_FOLDER_PATH="highlighted_documents"
DOCUMENTS_DIR="uploads"
log_folder = "dev_logs"
router = APIRouter()


@router.post("/register/")
@router.post("/register")
def register(user: user_schemas.UserCreate, db: Session = Depends(get_db)):
    db_user_existed = user_crud.get_user_by_username(db, user.username) is not None
    if db_user_existed:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Check if email is already registered
    db_email_existed = user_crud.get_user_by_email(db, user.email) is not None
    if db_email_existed:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = utils.get_password_hash(user.password)
    user.password = hashed_password
    new_user = user_crud.create_user(db, user)
    return new_user

@router.post("/login", response_model=user_schemas.TokenRefresh)  # Changed to /login
@router.post("/login/", response_model=user_schemas.TokenRefresh) 
def login_for_access_token(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    # Try to find user by username first
    db_user = user_crud.get_user_by_username(db, form_data.username)
    # If not found by username, try to find by email
    if not db_user:
        db_user = user_crud.get_user_by_email(db, form_data.username)
    
    if not db_user or not utils.verify_password(form_data.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username, email, or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=utils.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = utils.create_access_token(
        data={"sub": db_user.username}, expires_delta=access_token_expires
    )
    refresh_token_expires = timedelta(days=utils.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = utils.create_refresh_token(
        data={"sub": db_user.username}, expires_delta=refresh_token_expires
    )
    try:
        user_crud.create_token(db, access_token, datetime.utcnow() + access_token_expires, db_user)
        user_crud.create_refresh_token(db, refresh_token, datetime.utcnow() + refresh_token_expires, db_user)
    except Exception as E:
        print(E)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/refresh-token", response_model=user_schemas.Token)
def refresh_access_token(refresh_token: str, db: Session = Depends(get_db)):
    token_data = utils.decode_token(refresh_token, utils.REFRESH_SECRET_KEY)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    db_refresh_token = user_crud.get_refresh_token(db, refresh_token)
    if not db_refresh_token or db_refresh_token.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = user_crud.get_user_by_username(db, token_data["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=utils.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = utils.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/forget-password/")
async def forget_password(email:user_schemas.ResetRequest,
                          db: Session = Depends(get_db)):
    sttime = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    utils.logging(log_folder,sttime)
    logging_state = {
        "API": "/forget-password",
        "email":email.email,
    }
    utils.logging(log_folder, json.dumps(logging_state))

    user = user_crud.get_user_by_email(db,email.email)

    if user:
        reset_token_expires = timedelta(minutes=utils.RESET_TOKEN_EXPIRE_MINUTES)
        reset_token = utils.create_access_token(
            data={"sub": user.username}, expires_delta=reset_token_expires
        )
        reset_link = f"{utils.ROOT_PAGE_ADDRESS}{reset_token}"
        utils.logging(log_folder, reset_link)
        utils.h_log(log_folder)
        if utils.send_reset_password_email(email.email,reset_link, user.username):
        # if utils.send_reset_password_email("trieuhoangan06@gmail.com",reset_link, user.username):
            return "Reset password email sent successully"
        else:
            return "Failed to send reset password email"
    else:
        utils.h_log(log_folder)
        return "There is no user registered with this email"
    
@router.post("/reset-password/")
async def reset_password(reset_infor:user_schemas.ResetPassword,
                         db: Session = Depends(get_db)):
    sttime = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    utils.logging(log_folder,sttime)
    logging_state = {
        "API": "/reset-password/",
        "new_password":reset_infor.new_password
    }
    utils.logging(log_folder, json.dumps(logging_state))

    reset_token = reset_infor.token
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Reset token no longer valid",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = utils.decode_token(reset_token, utils.SECRET_KEY)
    if payload is None:
        raise credentials_exception
    username: str = payload.get("sub")
    # if username is None:
    #     raise credentials_exception
    # token_data = user_schemas.TokenData(username=username)
    user = user_crud.get_user_by_username(db,username)

    hashed_password = utils.get_password_hash(reset_infor.new_password)

    user.hashed_password = hashed_password

    # user = user_crud.reset_password(db,user)
    user = user_crud.update_password(db,user.id,hashed_password)

    utils.h_log(log_folder)
    return "ok"
    
@router.post("/update-user-infor")
async def update_user_infor(infor: user_schemas.UpdateUSerInfor, 
                            db:Session = Depends(get_db), 
                            current_user: user_model.User = Depends(get_current_user)):
    sttime = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    utils.logging(log_folder,sttime)

    infor.password = infor.password and utils.get_password_hash(infor.password)

    logging_state = dict({
        "API": "/update-user-infor",
        "user": current_user.username,
            
        }, **{
            attr:getattr(infor,attr) for attr in type(infor).model_fields
        }
    )
    utils.logging(log_folder, json.dumps(logging_state))

    infor.username = None

    for attr in type(infor).model_fields:
        if (value:=getattr(infor,attr)) is not None:
            setattr(current_user,attr,value)

    user = user_crud.update_user(db,current_user, current_user.id)
    user.hashed_password = ""
    utils.h_log(log_folder)
    return user

@router.post("/change-password")
async def change_password(infor: user_schemas.ChangePassword, 
                          db:Session = Depends(get_db), 
                          current_user: user_model.User = Depends(get_current_user)):
    sttime = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    utils.logging(log_folder,sttime)
    logging_state = {
        "API": "/change-password",
        "user": current_user.username,
        # "old_password":infor.old_password,
        # "new_password":infor.new_password,
    }
    utils.logging(log_folder, json.dumps(logging_state))
    if utils.verify_password(infor.old_password, current_user.hashed_password):
        hashed_password = utils.get_password_hash(infor.new_password)
        current_user.hashed_password = hashed_password
        user = user_crud.update_user(db,current_user, current_user.id)
        result={"msg":"done"}
    else:
        result={"msg":"wrong password"}
    utils.logging(log_folder, json.dumps(result))
    utils.h_log(log_folder)
    return result

@router.get("/get-user-infor")
async def get_user_infor(db:Session = Depends(get_db), 
                         current_user: user_model.User = Depends(get_current_user)):
    user = user_crud.get_user(db,current_user.id)
    sttime = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    utils.logging(log_folder,sttime)
    logging_state = {
        "API": "/get-user-infor",
        "user": current_user.username
    }
    utils.logging(log_folder, json.dumps(logging_state))
    result_obj = {
        "username": user.username,
        "email": user.email,
        "fullname": user.fullname,
        "workplace": user.workplace,
        "address": user.address,
        "phone": user.phone,
    }
    for key in result_obj:
        if result_obj[key] is None:
            result_obj[key] = ""
    return result_obj

@router.post("/contact-support")
async def change_password(infor: user_schemas.ContactSupport, db:Session = Depends(get_db)):
    sttime = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    utils.logging(log_folder,sttime)
    logging_state = {
        "API": "/contact-support",
        "name":infor.name,
        "email":infor.email,
        "content":infor.content
    }
    utils.logging(log_folder, json.dumps(logging_state))
    try:
        utils.send_contact_support_email(infor.email, infor.name, infor.content)
        result={"msg":"done"}
    except:
        result={"msg":"cannot send email"}
    utils.logging(log_folder, json.dumps(result))
    utils.h_log(log_folder)
    return result