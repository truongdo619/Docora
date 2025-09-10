from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os, sys
sys.path.append("/home/antrieu/drive/DOCORA")
from models.psql.legacy_user import Base as StableBase, LegacyUser as StableUser, LegacyToken as StableToken, LegacyRefreshToken as StableRefreshToken, LegacyResetPasswordToken as StableResetPasswordToken
from models.psql.user import Base as DevelopBase, User as DevelopUser, Token as DevelopToken, RefreshToken as DevelopRefreshToken, ResetPasswordToken as DevelopResetPasswordToken

# Connection URLs (adjust with your actual database credentials)
stable_db_url = "postgresql://admin:admin@localhost:5432/polyminder"
develop_db_url = "postgresql://admin:admin@localhost:5433/polyminder_dev"

# Create engines for both databases
stable_engine = create_engine(stable_db_url)
develop_engine = create_engine(develop_db_url)

# Create sessionmakers
StableSession = sessionmaker(bind=stable_engine)
DevelopSession = sessionmaker(bind=develop_engine)

# Create sessions
stable_session = StableSession()
develop_session = DevelopSession()

stable_users = stable_session.query(StableUser).all()
stable_tokens = stable_session.query(StableToken).all()

stable_refresh_tokens = stable_session.query(StableRefreshToken).all()
stable_reset_password_tokens = stable_session.query(StableResetPasswordToken).all()

# Migrate users to the develop database
for stable_user in stable_users:
    # Check if the user with the same id or username already exists in the develop database
    existing_user = develop_session.query(DevelopUser).filter(
        (DevelopUser.id == stable_user.id) | (DevelopUser.username == stable_user.username) | (DevelopUser.email == stable_user.email) 
    ).first()
    
    if not existing_user:  # If user doesn't exist, add it
        develop_user = DevelopUser(
            id=stable_user.id,
            username=stable_user.username,
            email=stable_user.email,
            hashed_password=stable_user.hashed_password,
            fullname=None,  # Set default value or None
            address=None,   # Set default value or None
            phone=None,     # Set default value or None
            workplace=None  # Set default value or None
        )
        develop_session.add(develop_user)

# Commit the session to save the changes
develop_session.commit()

# Closing sessions
stable_session.close()
develop_session.close()