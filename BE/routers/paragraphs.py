
import copy
import time
import json
from datetime import  datetime

from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from crud.psql import document as document_crud
from models.psql import user as user_model

from schemas import document as document_schemas

from celery.result import AsyncResult
from celery_app import app as celery_app

from dev_tasks import re_run_for_changed_para
from ner_re_processing import convert_to_output_v2

from utils import utils

from .dependencies import get_current_user, format_output, get_db, load_para


log_folder = "dev_logs"
router = APIRouter()

@router.post("/edit-paragraph")
async def update_paragraph(data: document_schemas.ParaUpdate,current_user: user_model.User = Depends(get_current_user),db: Session = Depends(get_db)):
    sttime = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    utils.logging(log_folder,sttime)
    logging_state = {
        "API": "/edit-paragraph",
        "document_id":data.document_id,
        "update_id":data.update_id,
        "paragraphs":data.paragraphs
    }
    utils.logging(log_folder, json.dumps(logging_state))

    start = datetime.now()
    document = document_crud.get_document(db,data.document_id)
    # update = document_crud.get_last_update(db,data.document_id,current_user.id)
    update = document_crud.get_current_temporary_update(db,current_user.id,data.update_id,data.document_id)
    user_notes = update.get_user_notes()
    old_text, old_pos,change_ids, para_data = load_para(document,user_notes)
    old_entity = document.get_entities()
    old_relations = document.get_relations()
    # finished load data


    ### detect changes in new paragraphs
    changed_ids, changed_para, changed_old_text, changed_old_pos = [], [], [], []
    for index, para in enumerate(data.paragraphs):
        if para != old_text[index]:
            changed_ids.append(index)
            changed_para.append(para)
            changed_old_text.append(old_text[index])
            changed_old_pos.append(old_pos[index])
            print("----------------------------------")
            print(old_text[index])
            print(para)
    print("changed_ids", changed_ids)
    
    ### start to re processing with new paragraphs
    # 
    # 
    changed_bbox = utils.organize_new_box(changed_old_text,changed_old_pos,changed_para)
    new_pos = copy.deepcopy(old_pos)
    new_text = copy.deepcopy(old_text)
    for id,index in enumerate(changed_ids):
        if type(para_data[0]) == str:
            new_pos[index] = changed_bbox[id]
            new_text[index] = changed_para[0]
            update.set_positions(new_pos)
            update.set_paragraphs(new_text)
        else:
            new_para_data = copy.deepcopy(para_data)
            new_para_data[index]["text"] = changed_para[0]
            new_para_data[index]["bbox"] = changed_bbox[id]
            update.set_paragraphs(new_para_data)


    print(len(changed_bbox))
    print(changed_bbox)
    update_content = []
    for id in changed_ids:
        update_content.append({
            "para_id":id,
            "text": data.paragraphs[id]
        })
    update_note = {
        "action":"update",
        "target":"para",
        "content":update_content
    }
    user_notes.append(update_note)
    update.set_user_notes(user_notes)
    
    update = document_crud.modify_update_as_object(db,update.id,update)
    

    # GET new NER and new RE set 
    #  Enqueue
    task = re_run_for_changed_para.apply_async(
        args=[update.id, current_user.id, document.id]
    )
    task_result = AsyncResult(task.id, app=celery_app)
    while task_result.state == "PENDING":
        print("waiting for queue")
        time.sleep(1)
    db.refresh(update)

    new_pos = old_pos
    old_relations = update.get_relations()
    

    ### reassign changes in entities and relation to save in future uses
    for id,index in enumerate(changed_ids):
        new_pos[index] = changed_bbox[id]

    # new_output, _, _ = convert_to_output_v2(old_relations, new_pos, data.paragraphs)
    if type(para_data[0]) == str:
        new_output, normalized_all_pages_bb_data, normalized_all_pages_text_data = convert_to_output_v2(old_relations, new_pos, data.paragraphs)
    else:
        new_output, normalized_all_pages_bb_data, normalized_all_pages_text_data = convert_to_output_v2(old_relations, new_pos, data.paragraphs,para_data=para_data)

    new_output = format_output(new_output,data.document_id,document.FileName,update.id,update.get_user_notes(),apply_visibility=True)
    end = datetime.now()
    dist = end-start
    print(dist.seconds)
    utils.h_log(log_folder)
    return new_output

@router.post("/reorder-paragraph")
async def update_paragraph(data: document_schemas.ReorderPara,current_user: user_model.User = Depends(get_current_user),db: Session = Depends(get_db)):
    sttime = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    utils.logging(log_folder,sttime)
    logging_state = {
        "API": "/reorder-paragraph",
        "user": current_user.username,
        "doc":data.document_id,
        "update":data.update_id,
        "old para id":data.old_para_id,
        "new order": data.paragraphs
    }
    utils.logging(log_folder, json.dumps(logging_state))
    start = datetime.now()
    document = document_crud.get_document(db,data.document_id)
    # update = document_crud.get_last_update(db,data.document_id,current_user.id)
    update = document_crud.get_current_temporary_update(db,current_user.id,data.update_id,data.document_id)
    user_notes = update.get_user_notes()
    
    cur_para, cur_pos,change_ids, para_data = load_para(document,user_notes)
    old_entity = update.get_entities()
    old_relations = update.get_relations()

    if old_relations ==[]:
        old_relations = document.get_relations()
        old_relations = utils.execute_user_note_on_relations(user_notes,old_relations)
    if old_entity ==[]:
        old_entity = document.get_entities()
        old_entity = utils.execute_user_note_on_entities(user_notes,old_entity)
    # finished load data
    old_edit_status=user_notes[0]["content"]

    new_text = []
    new_pos = []
    new_entities = []
    new_relations = []
    new_edit_status = []
    new_para_data = []
    add_content=[
        {
            "new_order":data.paragraphs
        }
    ]

    action = {
        "action":"reorder",
        "target":"all",
        "content":add_content
    }
    user_notes.append(action)
    for index in data.paragraphs:
        # real_index = index -1 
        print(index)
        new_text.append(cur_para[index])
        new_pos.append(cur_pos[index])
        new_entities.append(old_entity[index])
        new_relations.append(old_relations[index])
        new_edit_status.append(old_edit_status[index])
        if type(para_data[0])!=str:
            new_para_data.append(para_data[index])
    user_notes[0]['content'] = new_edit_status
    update.set_user_notes(user_notes)
    update.set_entities(new_entities)
    update.set_relations(new_relations)
    
    update = document_crud.modify_update_as_object(db,update.id,update)
    
    if type(para_data[0])==str:
        new_output, _, _ = convert_to_output_v2(new_relations, new_pos, new_text)
    else:
        new_output, _, _ = convert_to_output_v2(new_relations, new_pos, new_text,para_data=new_para_data)
    
    new_output = format_output(new_output,data.document_id,document.FileName,update.id,update.get_user_notes(),apply_visibility=True)
    # print(data.paragraphs)
    end = datetime.now()
    dist = end-start
    print(dist.seconds)
    utils.h_log(log_folder)
    return new_output

@router.post("/set-visible")
async def set_visible(infor: document_schemas.VisibleList, db:Session = Depends(get_db), current_user: user_model.User = Depends(get_current_user)):
    sttime = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    utils.logging(log_folder,sttime)
    logging_state = {
        "API": "/set-visible",
        "document_id":infor.document_id,
        "update_id":infor.update_id,
        "visible_list":infor.visible_list
    }
    utils.logging(log_folder, json.dumps(logging_state))
    document = document_crud.get_document(db,infor.document_id)
    # update = document_crud.get_last_update(db,data.document_id,current_user.id)
    update = document_crud.get_current_temporary_update(db,current_user.id,infor.update_id,infor.document_id)

    user_notes = update.get_user_notes()
    add_content={
            "visible_list":infor.visible_list
        }
    
    action = {
        "action":"update_visible",
        "target":"visible",
        "content":add_content
    }
    user_notes.append(action)
    update.set_user_notes(user_notes)
    update = document_crud.modify_update_as_object(db,update.id,update)
    
    utils.h_log(log_folder)
    
    
    relations = update.get_relations()
    if relations == []:
        relations = document.get_relations()
        relations = utils.execute_user_note_on_relations(user_notes,relations)
    
    paragraphs,bbox, change_ids,para_data =load_para(document, user_notes)
    if type(para_data[0])==str:
        new_output, _, _ = convert_to_output_v2(relations, bbox, paragraphs)
    else:
        new_output, _, _ = convert_to_output_v2(relations, bbox, paragraphs,para_data=para_data)
    
    new_output = format_output(new_output,document.id,document.FileName,update.id,update.get_user_notes(),apply_visibility=True)
    return new_output