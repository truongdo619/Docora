from database import Base, dev_engine
from sqlalchemy import Column, BigInteger, String, ForeignKey, DateTime, Text, Time, func, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
import json
from datetime import datetime
from .user import User  # Ensure this points to your actual User model import

def datetime_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError("Type not serializable")

def get_bbox_n_text_seperated(para_data):
    block_texts_data = []
    block_bb_data = []
    for para in para_data:
        block_texts_data.append(para["text"])
        block_bb_data.append(para["bbox"])
    return block_texts_data, block_bb_data



class Document(Base):
    __tablename__ = "documents"
    __table_args__ = {'extend_existing': True}
    # PostgreSQL version with UUID
    id = Column(BigInteger, primary_key=True, unique=True, index=True)
    Paragraphs = Column(Text)  # JSONB for structured data
    UploadTime = Column(DateTime(timezone=True), server_default=func.now())
    FilePath = Column(String, nullable=False)
    FileName = Column(String, nullable=False)
    Entities = Column(JSONB)  # JSONB for structured data
    Relation = Column(JSONB)
    Event = Column(JSONB)
    Position = Column(JSONB)
    UserID = Column(Integer, ForeignKey('users.id'), nullable=False)
    StatisticInfor = Column(JSONB)
    
    update = relationship("Update", back_populates="document")
    user = relationship("User", back_populates="document")

    def get_paragraphs(self):
        if isinstance(self.Paragraphs,str):
            return json.loads(self.Paragraphs)
        else:
            return self.Paragraphs

    def set_paragraphs(self, paragraphs):
        self.Paragraphs = json.dumps(paragraphs)
        
    def get_entities(self):
        return self.Entities

    def set_entities(self, entities):
        self.Entities = entities

    def get_relations(self):
        return self.Relation

    def set_relations(self, relation):
        self.Relation = relation

    def get_events(self):
        return self.Event

    def set_events(self, event):
        self.Event = event

    def get_positions(self):
        return self.Position

    def set_positions(self, position):
        self.Position = position

    def get_infor(self):
        return self.StatisticInfor

    def set_infor(self, infor):
        self.StatisticInfor = infor

class Update(Base):
    __tablename__ = "updates"
    __table_args__ = {'extend_existing': True}
    # PostgreSQL version with UUID
    id = Column(BigInteger, primary_key=True, unique=True, index=True)
    Paragraphs = Column(JSONB) 
    Entities = Column(JSONB)
    Relation = Column(JSONB)
    Event = Column(JSONB)
    Position = Column(JSONB)
    UserNote = Column(Text)
    StatisticInfor = Column(JSONB)
    UserID = Column(Integer, ForeignKey('users.id'), nullable=False)
    DocumentID = Column(BigInteger, ForeignKey('documents.id'), nullable=False)
    # Name = Column(String, nullable=True)
    FatherID = Column(Integer, default=-1)
    Name = Column(Text,default="Temporary update")
    UploadDate = Column(Text, nullable=True)
    checkpoint = Column(Integer, default=0)
    document = relationship("Document", back_populates="update")
    user = relationship("User", back_populates="update")
    
    def get_user_notes(self):
        return json.loads(self.UserNote)

    def set_user_notes(self, userNote):
        self.UserNote = json.dumps(userNote)

    def get_paragraphs(self):
        return self.Paragraphs

    def set_paragraphs(self, paragraphs):
        self.Paragraphs = paragraphs

    def get_entities(self):
        if "data" not in self.Entities:
            return self.Entities
        else:
            return json.loads(self.Entities["data"])

    def set_entities(self, entities):
        entity_object = {"data":json.dumps(entities)}
        self.Entities = entity_object

    def get_relations(self):
        if "data" not in self.Relation:
            return self.Relation
        else:
            return json.loads(self.Relation["data"])

    def set_relations(self, relation):
        relation_object = {"data":json.dumps(relation)}
        self.Relation = relation_object

    def get_events(self):
        if "data" not in self.Event:
            return self.Event
        else:
            return json.loads(self.Event["data"])

    def set_events(self, event):
        event_object = {"data":json.dumps(event)}
        self.Event = event_object
    

    def get_positions(self):
        return self.Position

    def set_positions(self, position):
        self.Position = position

    def get_infor(self):
        return self.StatisticInfor

    def set_infor(self, infor):
        self.StatisticInfor = infor

# Add this to your User model to establish bidirectional relationships
User.document = relationship("Document", back_populates="user")
User.update = relationship("Update", back_populates="user")

# Uncomment to create the tables in PostgreSQL
# Base.metadata.create_all(engine)
