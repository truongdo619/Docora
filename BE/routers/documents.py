import os
import json

from datetime import datetime

import httpx
from httpx import Client
import asyncio

from fastapi import APIRouter, File, UploadFile, Request, Form
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from sqlalchemy.orm import Session

from crud.psql import document as document_crud
from models.psql import user as user_model
from config import UPLOAD_DIR
from schemas import document as document_schemas

from celery.result import AsyncResult
from celery_app import app as celery_app
# from tasks import process_pdf_task, re_run_re, re_run_for_changed_para, re_run

from dev_tasks import process_pdf_task, process_pdf_task_with_json, extract_table_from_PDF
# from dev_tasks import process_text_task
from ner_re_processing import  convert_to_output_v2
# from EAE.predict_EAE import predict as eae_predict
from utils import utils

from .dependencies import get_current_user, format_output, format_output_for_rerun, get_db, load_para

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
dev_account_id = 2335
HIGHLIGHTED_DOCUMENT_FOLDER_PATH="highlighted_documents"
DOCUMENTS_DIR="uploads"
log_folder = "dev_logs"
router = APIRouter()

@router.post("/process-pdf-v3/")
async def process_pdf_v3(current_user: user_model.User = Depends(get_current_user),file: UploadFile = File(...),db: Session = Depends(get_db)):

    file_location = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_location, "wb") as f:
        f.write(await file.read())

    # all_pages_text_data, all_pages_bb_data = convert_pdf_to_text_and_bounding_boxes(file_location)
    current_doc = document_crud.create_document(
        db, current_user.id, [], file_location,  file.filename, [], [], {}, [], []
    )
    info_obj = {
            "id": current_doc.id,
            "filename": current_doc.FileName,
            "upload_time": current_doc.UploadTime,
            "entities": 0,
            "relations": 0,
            "pages": 0,
            "status": "queued"
        }
    current_doc.set_infor(info_obj)
    current_doc = document_crud.update_document(db,current_doc.id,current_doc)
    # Enqueue the task
    task = process_pdf_task.apply_async(
        args=[file_location, current_user.id, current_doc.id]
    )
    print(info_obj)
    task_result = AsyncResult(task.id, app=celery_app).get()
    db.refresh(current_doc)
    model_output = current_doc.get_relations()
    all_pages_bb_data = current_doc.get_positions()
    all_pages_text_data = current_doc.get_paragraphs()
    
    output, normalized_all_pages_bb_data, normalized_all_pages_text_data = convert_to_output_v2(model_output, all_pages_bb_data, all_pages_text_data)
    current_doc.set_positions(normalized_all_pages_bb_data)
    current_doc.set_paragraphs(normalized_all_pages_text_data)
    current_doc = document_crud.update_document(db,current_doc.id,current_doc)

    # output["document_id"] = current_doc.id
    # output["filename"] = current_doc.FileName
    # output["update_id"] = -1
    
    # return output
    return format_output(output,current_doc.id,current_doc.FileName,-1,[],apply_visibility=False)

@router.post("/get-update")
async def get_update(update_id:document_schemas.UpdateIDSchema, current_user: user_model.User = Depends(get_current_user),db: Session = Depends(get_db)):
    update = document_crud.get_update(db,update_id.update_id)
    return update

@router.post("/get-document/{document_id}")
async def get_document_as_id(document_id:int, current_user: user_model.User = Depends(get_current_user),db: Session = Depends(get_db)):
    """
    This function is used to get the document as id.
    """
    document = document_crud.get_document(db,document_id)
    last_update = document_crud.get_last_update(db,document_id,current_user.id)
    # TODO: reformat this function
    # 1. get last update need to be reworked. Since update id no longer incremental -> need another method to get last update
    if last_update.get_user_notes():
        user_notes = last_update.get_user_notes()
        paragraphs, bbox,change_ids, para_data = load_para(document, user_notes)
        relations = last_update.get_relations()
        if relations==[]:
            relations = document.get_relations()
            relations = utils.execute_user_note_on_relations(user_notes,relations)
        if type(para_data[0]) == str:
            output, normalized_all_pages_bb_data, normalized_all_pages_text_data = convert_to_output_v2(relations, bbox, paragraphs)
        else:
            output, normalized_all_pages_bb_data, normalized_all_pages_text_data = convert_to_output_v2(relations, bbox, paragraphs,para_data=para_data)
        output = format_output(output,document.id,document.FileName,last_update.id,user_notes,apply_visibility=True)
    else:
        output, normalized_all_pages_bb_data, normalized_all_pages_text_data = convert_to_output_v2(document.get_relations(), document.get_positions(), document.get_paragraphs())
        output = format_output(output,document.id,document.FileName,-1,[],apply_visibility=False)
    if "domamin" not in output:
        output['domain']="polymer"
    return output

@router.get("/delete-document/{document_id}")
def delete_document(document_id:int, current_user: user_model.User = Depends(get_current_user),db: Session = Depends(get_db)):
    """
    This function is used to delete the document.
    Input:
        document_id: int
        current_user: user_model.User
        db: Session
    Output:
        msg: str
    """
    
    try:
        msg = document_crud.delete_document(db,document_id)
        return msg
    except:
        credentials_exception = HTTPException(
            status_code=status. HTTP_500_INTERNAL_SERVER_ERROR ,
            detail="server error"
        )
        raise credentials_exception
    
@router.post("/download-document/{document_id}")
async def download_document(document_id:int, current_user: user_model.User = Depends(get_current_user),db: Session = Depends(get_db)):
    """
    This function is used to download the document.
    Input:
        document_id: int
        current_user: user_model.User
        db: Session
    Output:
        file_path: str
    """

    doc = document_crud.get_document(db,document_id)
    file_name = doc.FileName
    # Construct the file path
    # file_path = os.path.join(DOCUMENTS_DIR, f"{document_id}.pdf")
    file_path = os.path.join(DOCUMENTS_DIR, file_name)
    # Check if the file exists
    if os.path.exists(file_path):
        # Serve the file as a downloadable response
        return FileResponse(file_path, media_type='application/pdf', filename=file_name)
    else:
        return {"error": "File not found"}

@router.post("/documents")
async def get_user_document(current_user: user_model.User = Depends(get_current_user),db: Session = Depends(get_db)):
    """
    This function is used to get the user document.
    Input:
        current_user: user_model.User
        db: Session
    Output:
        result: list
    """
    
    # TODO: add user note and synchronize with 1 update only
    
    documents = document_crud.get_user_document(db,current_user.id)
    print(current_user.id)

    result = []
    for doc in documents:
        try:
            cur_update = document_crud.get_last_update(db,doc.id,current_user.id)

            info_obj = cur_update.get_infor()
            if info_obj is None:
                info_obj = doc.get_infor()
            if "domain" not in info_obj:
                info_obj["domain"] = "material"
            result.append(info_obj)
        except:
            print(doc.id)
            continue
    settings = utils.load_settings_from_domain()
    return {"documents":result,"settings":settings}

@router.get("/re-extract-relations/{document_id}")
async def re_extract_relations(document_id:int,
                               current_user: user_model.User = Depends(get_current_user),
                               db: Session = Depends(get_db)):
    
    document = document_crud.get_document(db,document_id)
    update = document_crud.get_last_update(db,document_id,current_user.id)

    return format_output_for_rerun(document,current_user,update,db)

@router.get("/re-extract-all/{document_id}")
async def re_extract_all(document_id:int,
                         current_user: user_model.User = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    
    document = document_crud.get_document(db,document_id)
    update = document_crud.get_last_update(db,document_id,current_user.id)

    return format_output_for_rerun(document,current_user,update,db,run_ner=True)

@router.post("/upload-pdf-queue/")
async def upload_queue(
    current_user: user_model.User = Depends(get_current_user),
    file: UploadFile = File(...),
    domain: str = Form(...),
    db: Session = Depends(get_db)
):
    
    if file.content_type != "application/pdf":
        return JSONResponse(status_code=400, content={"message": "Only PDF files are allowed"})

    file_location = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_location, "wb") as f:
        f.write(await file.read())

    # save document to data before enqueue the task
    sttime = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    utils.logging(log_folder,sttime)
    logging_state = {
        "API": "/upload-pdf-queue/",
        "filename": file.filename,
        "file_location": file_location
    }
    utils.logging(log_folder, json.dumps(logging_state))

    current_doc = document_crud.create_document(
        db, current_user.id, [], file_location,  file.filename, [], [], {}, [], []
    )
    info_obj = {
            "id": current_doc.id,
            "filename": current_doc.FileName,
            "upload_time": current_doc.UploadTime,
            "entities": 0,
            "relations": 0,
            "pages": 0,
            "status": "queued",
            "domain":domain
        }
    utils.logging(log_folder, json.dumps(info_obj))
    
    
    current_doc.set_infor(info_obj)
    current_doc = document_crud.update_document(db,current_doc.id,current_doc)
    # Enqueue the task
    task = process_pdf_task.apply_async(
        args=[file_location, current_user.id, current_doc.id, domain]
    )
    logging_state = {
        "task_id": task.id
    }
    utils.logging(log_folder, json.dumps(logging_state))
    utils.h_log(log_folder)
    return {"task_id": task.id, "status": "queued", "infor":info_obj}

@router.post("/upload-pdf-with-json/")
async def upload_pdf_with_json(
    request: Request,
    current_user: user_model.User = Depends(get_current_user),
    db: Session = Depends(get_db),    
):

    form = await request.form() 
    print(form)
    pdf_file = None
    json_file=None
    for key, value in form.items():
        if hasattr(value, "filename"):
            # It's an uploaded file
            file: UploadFile = value
            location  = os.path.join(UPLOAD_DIR, file.filename)
            # print(json_file.filename)
            # print(pdf_file.filename)
            if file.content_type == "application/pdf":
                pdf_file = file
            if file.content_type == "application/json":
                json_file = file
            with open(location, "wb") as f:
                f.write(await file.read())
            # with open(json_location, "wb") as f:
            #     f.write(await json_file.read())
            print(f"File field: {key}, filename: {file.filename}, content_type: {file.content_type}")
            # content = await file.read()  # read file content bytes
            # print(f"File size: {len(content)} bytes")
        else:
            # It's a normal form field
            print(f"Field: {key} = {value}")

    pdf_location  = os.path.join(UPLOAD_DIR, pdf_file.filename)
    json_location = os.path.join(UPLOAD_DIR, json_file.filename)
    current_doc = document_crud.create_document(
        db, current_user.id, [], pdf_location,  pdf_file.filename, [], [], {}, [], []
    )
    info_obj = {
        "id": current_doc.id,
        "filename": current_doc.FileName,
        "upload_time": current_doc.UploadTime,
        "entities": 0,
        "relations": 0,
        "pages": 0,
        "status": "queued"
    }
    current_doc.set_infor(info_obj)
    current_doc = document_crud.update_document(db,current_doc.id,current_doc)
    # Enqueue the task
    task = process_pdf_task_with_json.apply_async(
        args=[pdf_location, json_location, current_user.id, current_doc.id]
    )
    return {"task_id": task.id, "status": "queued", "infor":info_obj}
    # return "ok"

def handle_pending(task_id, task_result):
    return {"task_id": task_id, "status": "pending"}

def handle_success(task_id, task_result):
    return {"task_id": task_id, "status": "completed", "result": task_result.result}

def handle_failure(task_id, task_result):
    return {"task_id": task_id, "status": "failed", "error": str(task_result.info),"result": task_result.result}

def handle_default(task_id, task_result):
    return {"task_id": task_id, "status": task_result.state}

status_handlers = {
    "PENDING": handle_pending,
    "SUCCESS": handle_success,
    "FAILURE": handle_failure
}

@router.get("/task-status/{task_id}/")
async def get_task_status(task_id: str):
    task_result = AsyncResult(task_id, app=celery_app)
    handler = status_handlers.get(task_result.state, handle_default)
    return handler(task_id, task_result)

@router.post("/save/")
async def create_new_update(
    update_entity : document_schemas.NewUpdateEntity,
    current_user: user_model.User = Depends(get_current_user),
    db: Session = Depends(get_db)
    ):
    sttime = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    utils.logging(log_folder,sttime)
    logging_state = {
        "API": f"/save/"
    }
    utils.logging(log_folder, json.dumps(logging_state))
    print(update_entity.document_id)
    currtime = datetime.now()
    uploadtime = currtime.strftime('%d-%m-%Y %H:%M:%S')
    # update = document_crud.get_last_update(db,update_entity.document_id,current_user.id)
    update = document_crud.get_update_of_user(db,update_entity.document_id,update_entity.update_id,current_user.id )
    # update = document_crud.get_update(db,update_entity.update_id)
    update.Name =update_entity.update_name
    update.UploadDate = uploadtime
    update.checkpoint = 1
    update = document_crud.modify_update_as_object(db,update.id,update)
    # delete not suitable update

    cur_update = document_crud.create_update_as_object(db,update)
    cur_update.FatherID=update.id
    curtime = datetime.now()
    uploadtime = curtime.strftime('%d-%m-%Y %H:%M:%S')
    cur_update.UploadDate = uploadtime
    cur_update = document_crud.modify_update_as_object(db,cur_update.id,cur_update)
    
    utils.h_log(log_folder)
    return {"update_id":cur_update.id}

@router.get("/get-update-history/{document_id}")
async def get_update_history(
    document_id:int,
    current_user: user_model.User = Depends(get_current_user),
    db: Session = Depends(get_db)
    ):
    updates = document_crud.get_list_updates(db,current_user.id,document_id)

    return {"updates":updates}

@router.get("/get-document/{document_id}/{update_id}")
async def get_document_as_id(document_id:int,update_id:int, 
                             current_user: user_model.User = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    sttime = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    utils.logging(log_folder,sttime)
    logging_state = {
        "API": f"/get-document/{document_id}/{update_id}",
        "document_id": document_id,
        "update_id": update_id,
    }
    utils.logging(log_folder, json.dumps(logging_state))
    document = document_crud.get_document(db,document_id)
    # last_update = document_crud.get_last_update(db,document_id,current_user.id)
    # if update_id < 0:
    #     output, normalized_all_pages_bb_data, normalized_all_pages_text_data = convert_to_output_v2(document.get_relations(), document.get_positions(), document.get_paragraphs())
    #     output["document_id"] = document.id
    #     output["filename"] = document.FileName
    #     output["update_id"] = -1
    # else:
        # last_update = document_crud.get_update_of_user(db,update_id,current_user.id)
    last_update = document_crud.get_current_temporary_update(db,current_user.id,update_id,document_id)
        # TODO: reformat this function
        # 1. last_update no longer be able to be None
        # 2. Need to perform user notes before send to users
        # delete
    if last_update.get_user_notes():
        user_notes = last_update.get_user_notes()
        paragraphs,old_bboxs, change_ids, para_data = load_para(document, user_notes)    

        relations = document.get_relations()
        # relations = utils.execute_user_note_on_entities(user_notes,relations)
        relations = utils.execute_user_note_on_relations(user_notes,relations)

        # last_update = document_crud.create_update_as_object(db,last_update)select
        if type(para_data[0])==str:
            output, normalized_all_pages_bb_data, normalized_all_pages_text_data = convert_to_output_v2(relations, old_bboxs, paragraphs)
        else:
            output, normalized_all_pages_bb_data, normalized_all_pages_text_data = convert_to_output_v2(relations, old_bboxs, paragraphs, para_data=para_data)
        output = format_output(output,document.id,document.FileName,last_update.id,last_update.get_user_notes(),apply_visibility=True)
    utils.h_log(log_folder)
    return output

# @router.post("/text-process/")
# async def text_process(
#     request: document_schemas.CheckTextSchema,
#     db: Session = Depends(get_db)
#     ):
#     # text_process_func(db,request,False)
#     new_doc = document_crud.create_document(db,dev_account_id,"","","",[],[],[],[],[])
#     new_doc.set_paragraphs([request.text])
#     info_obj = {
#         "id": new_doc.id,
#         "filename": new_doc.FileName,
#         "upload_time": new_doc.UploadTime,
#         "entities": 0,
#         "relations": 0,
#         "pages": 0,
#         "status": "queued"
#     }
#     new_doc.set_infor(info_obj)
#     document_crud.update_document(db,new_doc.id,new_doc)
    
#     task = process_text_task.apply_async(
#         args=[dev_account_id, new_doc.id,request.ner_model, request.re_model]
#     )
#     task_result = AsyncResult(task.id, app=celery_app).get()
    
#     doc = document_crud.get_document(db,new_doc.id)
#     db.refresh(doc)
#     output = doc.get_relations()
#     return {"brat_format_output":output}

# @router.post("/process-text-event/")
# async def text_process(
#     request: document_schemas.CheckTextSchema,
#     db: Session = Depends(get_db)
#     ):
#     # text_process_func(db,request,False)
#     new_doc = document_crud.create_document(db,dev_account_id,"","","",[],[],[],[],[])
#     new_doc.set_paragraphs([request.text])
#     info_obj = {
#         "id": new_doc.id,
#         "filename": new_doc.FileName,
#         "upload_time": new_doc.UploadTime,
#         "entities": 0,
#         "relations": 0,
#         "pages": 0,
#         "status": "queued"
#     }
#     new_doc.set_infor(info_obj)
#     document_crud.update_document(db,new_doc.id,new_doc)
    
#     task = process_text_task.apply_async(
#         args=[dev_account_id, new_doc.id,request.ner_model, request.re_model,True]
#     )
#     task_result = AsyncResult(task.id, app=celery_app).get()
    
#     doc = document_crud.get_document(db,new_doc.id)
#     db.refresh(doc)
#     output = doc.get_relations()
#     return {"brat_format_output":output}


@router.post("/upload-pdf-for-table-extract")
async def upload_pdf_for_extract_table(
    file: UploadFile = Form(...),
    text: str = Form(...),
    db: Session = Depends(get_db),
):
    # Validate file type
    if file.content_type != "application/pdf":
        return {"error": "Only PDF files are accepted"}

    # Save the PDF
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_location, "wb") as f:
        f.write(await file.read())

    print(f"Saved PDF: {file_location}")
    print(f"Received plain text: {text}")

    # save document to data before enqueue the task
    sttime = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    utils.logging(log_folder,sttime)
    logging_state = {
        "API": "/upload-pdf-for-table-extract",
        "filename": file.filename,
        "file_location": file_location
    }
    utils.logging(log_folder, json.dumps(logging_state))

    current_doc = document_crud.create_document(
        db, dev_account_id, [], file_location,  file.filename, [], [], {}, [], []
    )
    info_obj = {
            "id": current_doc.id,
            "filename": current_doc.FileName,
            "upload_time": current_doc.UploadTime,
            "entities": 0,
            "relations": 0,
            "pages": 0,
            "status": "queued"
        }
    utils.logging(log_folder, json.dumps(info_obj))
    
    
    current_doc.set_infor(info_obj)
    current_doc = document_crud.update_document(db,current_doc.id,current_doc)
    # Enqueue the task
    base_prompt=text
    task = extract_table_from_PDF.apply_async(
        args=[file_location,base_prompt,dev_account_id, current_doc.id]
    )
    task_result = AsyncResult(task.id, app=celery_app).get()
    
    db.refresh(current_doc)
    results = current_doc.get_events()
    return results

TARGET_URL = "http://192.168.10.2:8000/process"
# TARGET_URL= "http://192.168.10.7:8000/v1/completions"
# class TextRequest(BaseModel):
#     model: str="Qwen/Qwen2.5-14B-Instruct"
#     prompt: str
#     max_tokens: int=2048
#     temperature: float=0.8

def sync_forward_text_sync(request):
    timeout = httpx.Timeout(connect=10.0, read=180.0, write=10.0, pool=5.0)
    with Client(timeout=timeout) as client:
        resp = client.post(TARGET_URL, json=request)
        resp.raise_for_status()
        return resp.json()

# @router.post("/generate-table-content")
# async def upload_pdf_for_extract_table(
#     data:document_schemas.ParseTableSchema,
#     db: Session = Depends(get_db),
# ):

    
#     table = data.dict()

#     new_table_data = utils.build_prompt(table,data.prompt) 
#     response = sync_forward_text_sync({"text": new_table_data["prompt"]})   
#     table["answer"]=response['result']

#     new_doc = document_crud.create_document(db,dev_account_id,"","","",[],[],[],[],[])
#     new_doc.set_paragraphs([table["answer"]])
#     info_obj = {
#         "id": new_doc.id,
#         "filename": new_doc.FileName,
#         "upload_time": new_doc.UploadTime,
#         "entities": 0,
#         "relations": 0,
#         "pages": 0,
#         "status": "queued"
#     }
#     new_doc.set_infor(info_obj)
#     document_crud.update_document(db,new_doc.id,new_doc)

#     task = process_text_task.apply_async(
#         args=[dev_account_id, new_doc.id,"v1", "v2",True]
#     )
#     task_result = AsyncResult(task.id, app=celery_app).get()
#     db.refresh(new_doc)
#     output = new_doc.get_relations()
#     return {"brat_format_output":output}