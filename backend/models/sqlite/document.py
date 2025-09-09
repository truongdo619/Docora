from database import Base,engine
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Time, func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.dialects.postgresql import JSONB
# from sqlalchemy.dialects.mysql import TIME
from .user import User 
import json
import pytz
from datetime import datetime

# Define Japan Standard Time
JST = pytz.timezone('Asia/Tokyo')

def datetime_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError("Type not serializable")

class Document(Base):
    __tablename__ = "documents"

    # #### SQLite version
    id = Column(Integer, primary_key=True, index=True)
    # #### PostgreSQL version
    # id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


    Paragraphs = Column(Text)  # This is specific to PostgreSQL
    UploadTime = Column(DateTime(timezone=True), server_default=func.now())
    FilePath = Column(String, nullable=False)
    FileName = Column(String, nullable=False)
    Entities = Column(Text)  # Use Text to store large strings
    Relation = Column(Text)
    Event = Column(Text)
    Position = Column(Text)
    UserID = Column(Integer, ForeignKey('users.id'), nullable=False)
    StatisticInfor = Column(Text)
    update = relationship("Update",back_populates="document")
    # Define the relationship to the User model
    user = relationship("User", back_populates="document")
    def get_paragraphs(self):
        if type(self.Paragraphs) == str:
            return json.loads(self.Paragraphs)
        else:
            return self.Paragraphs
        # return json.loads(self.Paragraphs)

    def set_paragraphs(self, paragraphs):
        self.Paragraphs = json.dumps(paragraphs)
        
    def get_entities(self):
        if type(self.Entities) == str:
            return json.loads(self.Entities)
        else:
            return self.Entities
        
        # return json.loads(self.Entities)

    def set_entities(self, entities):
        self.Entities = json.dumps(entities)

    def get_relations(self):
        if type(self.Relation) == str:
            return json.loads(self.Relation)
        else:
            return self.Relation
        

    def set_relations(self, relation):
        self.Relation = json.dumps(relation)

    def get_events(self):
        return json.loads(self.Event)

    def set_events(self, event):
        self.Event = json.dumps(event)

    def get_positions(self):
        if type(self.Position) == str:
            return json.loads(self.Position)
        else:
            return self.Position

    def set_positions(self, position):
        self.Position = json.dumps(position)

    def get_infor(self):
        try:
            return json.loads(self.StatisticInfor)
        except:
            return []

    def set_infor(self, infor):
        self.StatisticInfor = json.dumps(infor,default=datetime_serializer)
    
    @property
    def upload_time_jst(self):
        if self.UploadTime:
            utc_time = self.UploadTime.replace(tzinfo=pytz.utc)
            return utc_time.astimezone(JST)
        return None

        
class Update(Base):
    __tablename__ = "updates"
    # #### SQLite version
    id = Column(Integer, primary_key=True, index=True)
    # #### PostgreSQL version
    # id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    Paragraphs = Column(Text) 
    Entities = Column(Text)  # Use Text to store large strings
    Relation = Column(Text)
    Event = Column(Text)
    Position = Column(Text)
    UserNote = Column(Text)
    StatisticInfor = Column(Text)
    UserID = Column(Integer, ForeignKey('users.id'), nullable=False)
    DocumentID = Column(Integer, ForeignKey('documents.id'), nullable=False)
    document = relationship("Document",back_populates="update")
    # Define the relationship to the User model
    FatherID = Column(Integer, default=-1)
    Name = Column(Text,default="Temporary update")
    UploadDate = Column(Text, nullable=True)
    checkpoint = Column(Integer, default=0)

    user = relationship("User", back_populates="update")
    
    def get_user_notes(self):
        notes = json.loads(self.UserNote)
        return notes
    
    def set_user_notes(self,usernotes):
        self.UserNote = json.dumps(usernotes)

    def get_paragraphs(self):
        para = json.loads(self.Paragraphs)
        return para

    def set_paragraphs(self, paragraphs):
        self.Paragraphs = json.dumps(paragraphs)

    def get_entities(self):
        return json.loads(self.Entities)

    def set_entities(self, entities):
        self.Entities = json.dumps(entities)

    def get_relations(self):
        relation = json.loads(self.Relation)
        return relation

    def set_relations(self, relation):
        self.Relation = json.dumps(relation)

    def get_events(self):
        event = json.loads(self.Event)
        return event

    def set_events(self, event):
        self.Event = json.dumps(event)

    def get_positions(self):
        pos = json.loads(self.Position)
        return pos

    def set_positions(self, position):
        self.Position = json.dumps(position)

    def get_user_notes(self):
        return json.loads(self.UserNote)

    def set_user_notes(self, userNote):
        self.UserNote = json.dumps(userNote)
        
    def get_infor(self):
        try:
            return json.loads(self.StatisticInfor)
        except:
            return []

    def set_infor(self, infor):
        self.StatisticInfor = json.dumps(infor,default=datetime_serializer)

# Add this to your User model to establish a bidirectional relationship
User.document = relationship("Document", back_populates="user")
User.update = relationship("Update", back_populates="user")
# Base.metadata.create_all(engine)