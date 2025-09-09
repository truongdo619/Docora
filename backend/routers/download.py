import os
import json
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import FileResponse
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from sqlalchemy.orm import Session
from crud.psql import document as document_crud
from models.psql import user as user_model

from schemas import document as document_schemas
# from tasks import process_pdf_task, re_run_re, re_run_for_changed_para, re_run


from ner_re_processing import convert_to_output_v2
# from EAE.predict_EAE import predict as eae_predict

from utils.utils import get_cur_relations_entities
from utils import utils

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
dev_account_id = 2335
HIGHLIGHTED_DOCUMENT_FOLDER_PATH="highlighted_documents"
DOCUMENTS_DIR="uploads"
log_folder = "dev_logs"
router = APIRouter()

from .dependencies import get_current_user, get_db, load_para

@router.post("/download-entity/")
async def download_entity(entity_id:document_schemas.ChangeEditStatusSchema, 
                          current_user: user_model.User = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    

    document = document_crud.get_document(db,entity_id.document_id)
    update = document_crud.get_last_update(db,entity_id.document_id,current_user.id)
    user_notes = update.get_user_notes()
    cur_entities = update.get_entities()

    para_id, ent_id = document_schemas.UpdateEntitySchema.parse_id(entity_id.id)

    result  = cur_entities[para_id]
    result["entities"] = next((obj for obj in cur_entities[para_id]["entities"] if obj[0] == ent_id), None)
    if "relations" in cur_entities[para_id]:
        result["relations"] = [(obj for obj in cur_entities[para_id]["relations"] if obj[2][0][1] == ent_id)]
    else:
        result["relations"] = []
    return result

def download_default(info, current_user, db):
    document = document_crud.get_document(db,info.document_id)
    update = document_crud.get_last_update(db,info.document_id,current_user.id)
    user_notes = update.get_user_notes()
    
    cur_entities = document.get_entities()
    cur_entities = utils.execute_user_note_on_entities(user_notes,cur_entities)
    cur_relations = document.get_relations()
    cur_relations = utils.execute_user_note_on_relations(user_notes,cur_relations)
    
    visible_list = utils.collect_visible_list(user_notes)
    result = utils.filter_with_visible_list(cur_relations,visible_list)
    
    
    
    return result

def download_editted(info, current_user, db):
    document = document_crud.get_document(db,info.document_id)
    # TODO: Need to check what update should be picked here
    update = document_crud.get_last_update(db,info.document_id,current_user.id)
    user_notes = update.get_user_notes()
    cur_entities = update.get_entities()
    cur_relations = document.get_relations()
    cur_relations = utils.execute_user_note_on_relations(user_notes,cur_relations)
    edit_status_list = user_notes[0]["content"]
    result= []
    for cur_para_entities, cur_para_relations, para_edit_status in zip(cur_entities, cur_relations, edit_status_list):
        if not para_edit_status.get("entities"): continue
        tmp = dict()

        for status in para_edit_status["entities"]:
            if status["status"] != "none":
                tmp.update(cur_para_entities)
                break
        
        editted_entities_ids = {status["id"] for status in para_edit_status["entities"] if status["status"] != "none"}
        tmp["entities"] = list(filter(lambda e: e[0] in editted_entities_ids, cur_para_entities["entities"]))    

        editted_relations_ids = {status["id"] for status in para_edit_status["relations"] if status["status"] != "none"}
        tmp["relations"] = list(filter(lambda r: r[0] in editted_relations_ids, cur_para_relations.get("relations",[])))
        result.append(tmp)
    return result

def download_filter(info, current_user, db):
    document = document_crud.get_document(db,info.document_id)
    update = document_crud.get_last_update(db,info.document_id,current_user.id)
    print(info)
    user_notes = update.get_user_notes()
    ori_rel = document.get_relations()

    cur_rel = utils.execute_user_note_on_relations(user_notes,ori_rel)
    ent_result = utils.filter_entities(cur_rel,info.filtering_entity_types)
    rel_result = utils.filter_relations(cur_rel, info.filtering_relation_types)
    result = utils.merge_filtered_entities(ent_result, rel_result)
    return result

def download_entity_type(info, current_user, db):
    update = document_crud.get_last_update(db,info.document_id,current_user.id)
    cur_entities = update.get_entities()

    result = cur_entities
    for para in result:
        para["relations"] = []
        para["entities"] = [ent for ent in para["entities"] if ent[1] == info.type]
    return result


download_handlers={
    "all": download_default,
    "confirmed": download_editted,
    "filter": download_filter,
    "entity_type": download_entity_type
}

@router.post("/download-json/")
async def download_json(
    infor: document_schemas.DownloadJSONSchema,
    current_user: user_model.User = Depends(get_current_user),
    db: Session = Depends(get_db)
    ):
    sttime = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    utils.logging(log_folder,sttime)
    logging_state = {
        "API": "/download-highlighted-document",
        "document_id":infor.document_id,
        "update_id":infor.update_id,
        **{
            attr:getattr(infor,attr) for attr in type(infor).model_fields
        }
    }
    utils.logging(log_folder, json.dumps(logging_state,default=document_schemas.custom_serializer))
    handler = download_handlers.get(infor.mode, download_default)

    return handler(infor, current_user, db )

@router.post("/download-highlighted-document")
async def download_highlighted_document(infor: document_schemas.DownloadDocumentSchema, 
                                        db:Session = Depends(get_db), 
                                        current_user: user_model.User = Depends(get_current_user)):
    sttime = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    utils.logging(log_folder,sttime)
    logging_state = {
        "API": "/download-highlighted-document",
        "document_id":infor.document_id,
        "update_id":infor.update_id,
        **{
            attr:getattr(infor,attr) for attr in type(infor).model_fields
        }
    }
    utils.logging(log_folder, json.dumps(logging_state,default=document_schemas.custom_serializer))
    last_update = document_crud.get_current_temporary_update(db, current_user.id, infor.update_id, infor.document_id)
    document = document_crud.get_document(db, infor.document_id)
    
    user_notes = last_update.get_user_notes()
    paragraphs,bbox, change_ids, para_data = load_para(document,user_notes)

    handler = download_handlers.get(infor.mode, download_default)
    relations = handler(infor, current_user, db )

    cur_entities, cur_relations = get_cur_relations_entities(document,last_update,user_notes)
    print("original len of filtered relations", len(relations))
    print("original len of filtered relations", len(cur_relations))
    relations = utils.convert_output_to_full_pdf_creating(relations,cur_relations)
    print("len of converted relations", len(relations))
    # print(bbox[96][-1])
    if type(para_data[0]) == str:
        output, _, _ = convert_to_output_v2(relations, bbox, paragraphs,full_data_mode=False)
    else:
        output, _, _ = convert_to_output_v2(relations, bbox, paragraphs,para_data=para_data,full_data_mode=False)

    hightlighted_filename = "highlighted_"+document.FileName
    output_file_path = os.path.join(HIGHLIGHTED_DOCUMENT_FOLDER_PATH)
    utils.create_highlighted_pdf_file(document.FilePath,output,output_file_path)
    return FileResponse(output_file_path, filename=hightlighted_filename)
