
from fastapi import APIRouter, File, UploadFile, Request

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from sqlalchemy.orm import Session

from crud.psql import document as document_crud
from models.psql import user as user_model

# from database import get_db
from database import get_dev_db as get_db

from schemas import user  as user_schemas 


from celery.result import AsyncResult
from celery_app import app as celery_app


from dev_tasks import re_run
from ner_re_processing import  convert_to_output_v2
# from EAE.predict_EAE import predict as eae_predict


from utils import utils

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
dev_account_id = 2335
HIGHLIGHTED_DOCUMENT_FOLDER_PATH="highlighted_documents"
DOCUMENTS_DIR="uploads"
log_folder = "dev_logs"
router = APIRouter()




def get_current_user(request: Request,db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    headers = request.headers
    print("Request Headers:", headers)
    
    try:
        payload = utils.decode_token(token, utils.SECRET_KEY)
        username: str = payload.get("sub")
        token_data = user_schemas.TokenData(username=username)
        user = db.query(user_model.User).filter(user_model.User.username == token_data.username).first()
        if user is None:
            raise ValueError("user is none")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Need to refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e 
    return user

def format_output(output,doc_id,filename,update_id,user_notes,apply_visibility=False):
    output["document_id"] = doc_id
    output["filename"] = filename
    output["update_id"] = update_id
    if apply_visibility:
        v_list = utils.collect_visible_list(user_notes)
        output = utils.apply_visibility_to_result(output,v_list)
    return output

def collect_update(db,current_user,entity):
    """
    This function is used to collect the update of the document.
    Input:
        db: Session
        current_user: user_model.User
        entity: document_schemas.Entity
    Output:
        update: Update
        document: Document
    """
    document = document_crud.get_document(db,entity.document_id)
    update = None
    if entity.update_id >0:
        update = document_crud.get_update(db,entity.update_id)
        print("upper if    ",update)
    else:
        update = document_crud.create_update(db,current_user.id,entity.document_id,[],document.get_entities(),document.get_relations(),[],[],[],document.get_infor())
        print(update)
    return update,document

def return_formated_result(db,update_infor,document,update,cur_entities,optional=None):
    """
    This function is used to return the formated result of the update.
    Input:
        db: Session
        update_infor: dict
        document: Document
        update: Update
        cur_entities: list
        optional: dict
    Output:
        new_output: same format as /get-document/{document_id}
    """
    db.refresh(update)
    paragraphs,old_bboxs, change_ids,para_data = load_para(document,update.get_user_notes())

    new_relation = update.get_relations()
    if new_relation == []:
        new_relation = document.get_relations()
        new_relation = utils.execute_user_note_on_relations(update.get_user_notes(), new_relation)
    if type(para_data[0])==str:
        new_output, _, _ = convert_to_output_v2(new_relation, old_bboxs, paragraphs)
    else:
        new_output, _, _ = convert_to_output_v2(new_relation, old_bboxs, paragraphs,para_data=para_data)
    new_output = format_output(new_output,update_infor.document_id,document.FileName,update.id,update.get_user_notes(),apply_visibility=True)
    utils.h_log(log_folder)
    if optional is not None:
        for key in optional:
            new_output[key] = optional[key]
    return new_output

def execute_update_on_entities_wrapper(update_infor, wrapper,para_id):
    """
    This function is used to execute the update on the entities wrapper.
    Input:
        update_infor: dict
        wrapper: list
        para_id: int
    Output:
        wrapper: list
    """
    for index, e in enumerate(wrapper[para_id]["entities"]):
        entity_dict = utils.convert_entity_from_list_to_dict(e)
        if entity_dict.get("entity_id") == update_infor.get("entity_id"):    
            entity_dict["entity_type"] = update_infor.get("entity_type")
            entity_dict["head"] = update_infor.get("head")
            entity_dict["tail"] = update_infor.get("tail")
            entity_dict["comment"] = update_infor.get("comment","")
            entity_dict["entity_text"] = wrapper[para_id]["text"][update_infor.get("head"):update_infor.get("tail")]
            new_entity_list = utils.convert_entity_from_dict_to_list(entity_dict)
            for i in range(len(e)):
                e[i] = new_entity_list[i]
    return wrapper



def compose_update_content(paragraph_text,update_schema,target_entity,page_number,edit_status):
    """
    This function is used to compose the update content for the user note.
    Input:
        paragraph_text: str
        update_schema: dict
        target_entity: list
        page_number: int
        edit_status: str    
    Output:
        object_for_user_note: dict
        object_for_confirmation: dict

        object_for_user_note format:
        {
            "update_content":{
                old_entity:{
                    entity_id:"",
                    entity_type:"",
                    entity_text:"",
                    para_id:0,
                    page_number:0
                },
                new_entity:{
                    entity_id:"",
                    entity_type:"",
                    entity_text:"",
                    para_id:0,
                    page_number:0
                }
            }
        }
        object_for_confirmation format:
        {
            "old_entity":{
                "entity_id":"",
                "entity_type":"",
                "entity_text":"",
                "para_id":0,    
                "page_number":0
            },
            "new_entity":{
                "entity_id":"", 
                "entity_type":"",
                "entity_text":"",
                "para_id":0,
                "page_number":0
            }
        }   
    """
    
    para_id = update_schema.get("para_id")
    entity_id = update_schema.get("entity_id")
    dict_target_entity = utils.convert_entity_from_list_to_dict(target_entity)

    object_for_user_note = {
        "para_id":para_id,
        "ent_id":entity_id,
        "ent_type": update_schema.get("entity_type") ,
        "ent_text":paragraph_text[update_schema.get("head"):update_schema.get("tail")],
        "head":update_schema.get("head"),
        "tail":update_schema.get("tail"),
        "edit_status": "confirmed",
        "comment": update_schema.get("comment"),
        "old_ent_type":dict_target_entity.get("entity_type"),
        "old_ent_text":dict_target_entity.get("entity_text"),
        "old_head":dict_target_entity.get("head"),
        "old_tail":dict_target_entity.get("tail"),
        "old_id": dict_target_entity.get("entity_id"),
        "old_comment": dict_target_entity.get("comment") if len(target_entity)==5 else "",
        "old_edit_status": edit_status
    }

    
    object_for_confirmation={
        "old_entity":{
                "entity_id":entity_id,
                "entity_type":dict_target_entity.get("entity_type"),
                "entity_text":dict_target_entity.get("entity_text"),
                "para_id":para_id,
                "page_number":page_number[0] if type(page_number)==list else page_number
            },
        "new_entity":{
            "entity_id":entity_id,
            "entity_type":update_schema.get("entity_type"),
            "entity_text":paragraph_text[update_schema.get("head"):update_schema.get("tail")],
            "para_id":para_id,
            "page_number":page_number[0] if type(page_number)==list else page_number
        }
    }
    return object_for_user_note, object_for_confirmation

def find_new_entity_position_within_range(
    ENTITIES_WRAPPER, CURRENT_ENTITY, NEW_ENTITY, CURRENT_PARA_ID, MAX_OFFSET=50
):
    """
    Find head and tail index of NEW_ENTITY text in the `text` field of the paragraph identified by CURRENT_PARA_ID,
    with a constraint that the found match must lie within a fixed range from the CURRENT_ENTITY span.

    Parameters:
        - ENTITIES_WRAPPER (list): List of paragraphs with their entities.
        - CURRENT_ENTITY (dict): The currently selected entity to use as a reference.
        - NEW_ENTITY (list): The new entity information (same format as original entity).
        - CURRENT_PARA_ID (int): Index of the paragraph being processed.
        - MAX_OFFSET (int): Max number of characters to look before/after CURRENT_ENTITY for NEW_ENTITY.

    Returns:
        - A tuple of (head_idx, tail_idx) if found, otherwise None
    """

    para_data = ENTITIES_WRAPPER[CURRENT_PARA_ID]
    para_text = para_data["text"]
    
    reference_spans = [
        span for ent in para_data["entities"]
        if ent[0] == CURRENT_ENTITY["entity_id"]
        for span in ent[2]
    ]

    if not reference_spans:
        return -1,-1  # No reference position found

    ref_start, ref_end = reference_spans[0]
    new_text = NEW_ENTITY[-1].strip()

    # Search range
    start_search = max(0, ref_start - MAX_OFFSET)
    end_search = min(len(para_text), ref_end + MAX_OFFSET)

    window_text = para_text[start_search:end_search]

    # Find all occurrences of new_text in the window
    import re
    matches = [m for m in re.finditer(re.escape(new_text), window_text)]

    if not matches:
        return (-1,-1)  # Signal that nothing was found

    # Choose the match closest to the reference start
    closest_match = min(
        matches,
        key=lambda m: abs((start_search + m.start()) - ref_start)
    )

    head_idx = start_search + closest_match.start()
    tail_idx = start_search + closest_match.end()
    return (head_idx, tail_idx)

def compose_matched_entity_list(target_entity,new_entity,entities_wrapper,short_text_bound=100):
    """
        input: 
            target_entity(list): has format of entity under a list
            new_entity(list): has format of entity under a list
            entities_wrapper : entities or relations

        output:
            "matched_entities":[
                {
                    short_text:"",
                    para_id:0,
                    page_number:0
                    entity_id:"",
                    head:0,
                    tail:0,
                    entity_text:"",
                    entity_type:"",
                },
            ]
    }
    """
    dict_new_entity = utils.convert_entity_from_list_to_dict(new_entity)
    dict_target_entity = utils.convert_entity_from_list_to_dict(target_entity)
    target_entity_text = dict_target_entity.get("entity_text")
    target_entity_type = dict_target_entity.get("entity_type")
    matched_entities =[]
    print("findding matched entity")
    print(dict_target_entity)
    for index,para in enumerate(entities_wrapper):
        for entity in para.get("entities",[]):
            dict_entity = utils.convert_entity_from_list_to_dict(entity)
            
            if (dict_entity.get("entity_text") == target_entity_text and 
                dict_entity.get("entity_type") == target_entity_type and 
                dict_target_entity.get("entity_id")!=dict_entity.get("entity_id")):
                # if dic
                # print(dict_entity)
                # new_text_head , new_text_tail = find_new_entity_position_within_range(entities_wrapper,
                #                                                                       dict_entity,
                #                                                                       new_entity,
                #                                                                       index)
                # if new_text_head < 0 or new_text_tail <0:
                #     continue
                new_head = dict_entity["head"] + (dict_new_entity["head"]-dict_target_entity["head"])
                new_tail = dict_entity["tail"] + (dict_new_entity["tail"]-dict_target_entity["tail"])
                if entities_wrapper[index]["text"][new_head:new_tail]!=dict_new_entity["entity_text"]:
                    continue
                matched_para_id = index
                matched_entity_id = dict_entity.get("entity_id")
                

                head_limit = dict_entity.get("head") - min(short_text_bound,dict_entity.get("head"))
                tail_limit = min(dict_entity.get("tail")+short_text_bound,len(para.get("text",""))-1)

                new_head = short_text_bound if head_limit !=0 else dict_entity.get("head")
                new_tail = new_head + len(target_entity_text)

                matched_entity_page_number = para.get("page_number",0)
                match_short_text = para.get("text","")[head_limit:tail_limit]
                matched_entity = {
                    "short_text":match_short_text,
                    "para_id":matched_para_id,
                    "page_number":matched_entity_page_number[0] if type(matched_entity_page_number)==list else matched_entity_page_number,
                    "entity_id":matched_entity_id,
                    "head":new_head,
                    "tail":new_tail,
                    "entity_text":target_entity_text,
                    "entity_type":target_entity_type,
                }
                matched_entities.append(matched_entity)
    print("done finding matched entity")
    return matched_entities



def update_entity_function(db,new_entity_dict,cur_entities,cur_relations,user_notes,update,return_confirmation=False):
    """
    This function is used to update the entity of the document.
    Input:
        db: Session
        new_entity_dict: dict
        cur_entities: list
        cur_relations: list
        user_notes: list
        update: Update
        return_confirmation: bool
    Output:
        object_for_confirmation: dict
        matched_entity_list: list
        update: Update
    """
    print(new_entity_dict)
    action = {
        "action":"update",
        "target":"ent",
    }
    update_content=[]
    para_id = new_entity_dict.get("para_id",0)
    entity_id = new_entity_dict.get("entity_id","")
    target_entity = next((obj for obj in cur_relations[para_id]["entities"] if obj[0] == entity_id), [])
    
    edit_status = next((obj.get("status","") for obj in cur_relations[para_id].get("edit_status",{}).get("entities",[]) if obj.get("id","") == entity_id), "none")
    object_for_user_note, object_for_confirmation = compose_update_content(cur_entities[para_id].get("text",""),new_entity_dict,target_entity,cur_entities[para_id].get("page_number",0),edit_status)
    if return_confirmation:
        new_entity=[
            new_entity_dict["entity_id"],
            new_entity_dict["entity_type"],
            [
                [
                    new_entity_dict["head"],
                    new_entity_dict["tail"]
                ]
            ],
            "",
            new_entity_dict["entity_text"]
        ]
        matched_entity_list = compose_matched_entity_list(target_entity,new_entity,cur_entities)    

    
    update_content.append(object_for_user_note)
    print(target_entity)
    cur_entities =  execute_update_on_entities_wrapper(new_entity_dict, cur_entities,para_id)
    cur_relations =  execute_update_on_entities_wrapper(new_entity_dict, cur_relations,para_id)
    print(target_entity)
    action["content"] =  update_content
    user_notes.append(action)
    update.set_user_notes(user_notes)
    update.set_entities(cur_entities)  
    update.set_relations(cur_relations)  
    update = document_crud.modify_update_as_object(db,update.id,update)


    if return_confirmation:
        return object_for_confirmation, matched_entity_list, update
    else:
        return [],[], update

def format_output_for_rerun(document,current_user,update,db, run_ner = False):

    task = re_run.apply_async(
        args=[update.id, current_user.id, document.id, run_ner]
    )
    task_result = AsyncResult(task.id, app=celery_app).get()
    db.refresh(update)
    cur_relations = update.get_relations()
    paragraphs,old_bboxs, change_ids, para_data = load_para(document,update.get_user_notes())
    if type(para_data[0])==str:
        output, normalized_all_pages_bb_data, normalized_all_pages_text_data = convert_to_output_v2(cur_relations, old_bboxs, paragraphs)
    else:
        output, normalized_all_pages_bb_data, normalized_all_pages_text_data = convert_to_output_v2(cur_relations, old_bboxs, paragraphs,para_data=para_data)


    output = format_output(output,document.id,document.FileName,update.id,[],apply_visibility=False)
    return output

def text_process_func(db,request,new_model):
    new_doc = document_crud.create_document(db,dev_account_id,"","","",[],[],[],[],[])
    new_doc.set_paragraphs([request.text])
    info_obj = {
        "id": new_doc.id,
        "filename": new_doc.FileName,
        "upload_time": new_doc.UploadTime,
        "entities": 0,
        "relations": 0,
        "pages": 0,
        "status": "queued"
    }
    new_doc.set_infor(info_obj)
    document_crud.update_document(db,new_doc.id,new_doc)
    
    task = process_text_task.apply_async(
        args=[dev_account_id, new_doc.id,new_model]
    )
    task_result = AsyncResult(task.id, app=celery_app).get()
    
    doc = document_crud.get_document(db,new_doc.id)
    db.refresh(doc)
    output = doc.get_relations()
    return {"brat_format_output":output}

def load_para(document,user_notes):
    para_data = document.get_paragraphs()
    if type(para_data[0]) == str:
        old_pos = document.get_positions()
        old_text = para_data
        old_text, old_pos,change_ids, _ = utils.execute_user_note_on_paragraphs(user_notes, old_text, old_pos)
    else:
        old_text,old_pos = utils.get_bbox_n_text_seperated(para_data)
        old_text, old_pos,change_ids, para_data = utils.execute_user_note_on_paragraphs(user_notes, old_text, old_pos,para_data=para_data)
    
    return old_text, old_pos,change_ids, para_data