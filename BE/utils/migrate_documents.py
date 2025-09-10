from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os, sys
sys.path.append("/home/antrieu/drive/DOCORA")
from models.psql.legacy_document import Base as StableBase, LegacyDocument, LegacyUpdate
from models.psql.document import Base as DevelopBase, Document, Update, User

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

# Query stable database for the data to migrate
stable_documents = stable_session.query(LegacyDocument).all()
stable_updates = stable_session.query(LegacyUpdate).all()

# Migrate LegacyDocument to Document in the develop database
for stable_document in stable_documents:
    # Check if the document with the same id already exists in the develop database
    existing_document = develop_session.query(Document).filter(Document.id == stable_document.id).first()
    
    if not existing_document:  # If document doesn't exist, add it
        develop_document = Document(
            id=stable_document.id,
            Paragraphs=stable_document.Paragraphs,
            UploadTime=stable_document.UploadTime,
            FilePath=stable_document.FilePath,
            FileName=stable_document.FileName,
            Entities=stable_document.Entities,
            Relation=stable_document.Relation,
            Event=stable_document.Event,
            Position=stable_document.Position,
            UserID=stable_document.UserID,
            StatisticInfor=stable_document.StatisticInfor
        )
        develop_session.add(develop_document)

# Migrate LegacyUpdate to Update in the develop database
for stable_update in stable_updates:
    # Check if the update with the same id already exists in the develop database
    existing_update = develop_session.query(Update).filter(Update.id == stable_update.id).first()
    
    if not existing_update:  # If update doesn't exist, add it
        develop_update = Update(
            id=stable_update.id,
            Paragraphs=stable_update.Paragraphs,
            Entities=stable_update.Entities,
            Relation=stable_update.Relation,
            Event=stable_update.Event,
            Position=stable_update.Position,
            UserNote=stable_update.UserNote,
            StatisticInfor=stable_update.StatisticInfor,
            UserID=stable_update.UserID,
            DocumentID=stable_update.DocumentID,
            FatherID=stable_update.FatherID,
            Name=stable_update.Name,
            UploadDate=stable_update.UploadDate,
            checkpoint=stable_update.checkpoint
        )
        develop_session.add(develop_update)

# Commit the session to save the changes
develop_session.commit()

# Closing sessions
stable_session.close()
develop_session.close()
