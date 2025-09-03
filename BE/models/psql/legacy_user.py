from database import Base,engine
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
# from .document import Document,Update
from sqlalchemy.orm import backref
# Base = declarative_base()

class LegacyUser(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}
    # __table_args__ = {'keep_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    token = relationship("LegacyToken", back_populates="owner")
    rtoken = relationship("LegacyRefreshToken", back_populates="owner")
    rptoken = relationship("LegacyResetPasswordToken", back_populates="owner")
    # documents = relationship("Documents", backref="user")
    # update = relationship("Updates", backref="user")
    def __repr__(self):
        return "<User(id='%s', username='%s', email='%s', hashed_password='%s')>" % (
            self.id,
            self.username,
            self.email,
            self.hashed_password
        )
    
class LegacyRefreshToken(Base):
    
    __tablename__ = "refresh_tokens"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True)
    expires_at = Column(DateTime, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("LegacyUser", back_populates="rtoken")
# 
    def __repr__(self):
        return f"<Refresh_tokens(id='{self.id}', token='{self.token}', expires_at='{self.expires_at}', user_id='{self.user_id}')>" 

class LegacyToken(Base):
    
    __tablename__ = "tokens"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True)
    expires_at = Column(DateTime, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("LegacyUser", back_populates="token")
# 
    def __repr__(self):
        return f"<Refresh_tokens(id='{self.id}', token='{self.token}', expires_at='{self.expires_at}', user_id='{self.user_id}')>" 


class LegacyResetPasswordToken(Base):
    
    __tablename__ = "reset_password_tokens"
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True)
    expires_at = Column(DateTime, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("LegacyUser", back_populates="rptoken")
# 
    def __repr__(self):
        return f"<Refresh_tokens(id='{self.id}', token='{self.token}', expires_at='{self.expires_at}', user_id='{self.user_id}')>" 

