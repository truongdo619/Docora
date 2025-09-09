import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
# from routes import router

from config import UPLOAD_DIR
from database import Base,dev_engine

from routers.documents import router as documents_router
from routers.user import router as user_router
from routers.relations import router as relations_router
from routers.entities import router as entities_router
from routers.paragraphs import router as paragraphs_router
from routers.events import router as events_router
from routers.download import router as download_router




Base.metadata.create_all(bind=dev_engine)
# Base.metadata.create_all(bind=engine)
# Define the FastAPI app
app = FastAPI()

# CORS settings
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
app.mount("/statics", StaticFiles(directory="uploads"), name="static")

# Create uploads directory if it doesn't exist
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# Include routes
# app.include_router(router)
app.include_router(documents_router)
app.include_router(user_router)
app.include_router(relations_router)
app.include_router(entities_router)
app.include_router(paragraphs_router)
app.include_router(events_router)
app.include_router(download_router)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
