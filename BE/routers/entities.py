
import json

from datetime import  datetime

from fastapi import APIRouter
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends

from sqlalchemy.orm import Session
from crud.psql import document as document_crud
from models.psql import user as user_model

from schemas import document as document_schemas


# from tasks import process_pdf_task, re_run_re, re_run_for_changed_para, re_run


# from EAE.predict_EAE import predict as eae_predict

from utils.utils import get_cur_relations_entities
from utils import utils

from .dependencies import get_current_user, return_formated_result, update_entity_function, find_new_entity_position_within_range, get_db, load_para

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
dev_account_id = 2335
HIGHLIGHTED_DOCUMENT_FOLDER_PATH="highlighted_documents"
DOCUMENTS_DIR="uploads"
log_folder = "dev_logs"
router = APIRouter()

@router.post("/delete-entity")
async def delete_entity(entity:document_schemas.DeleteEntitySchema,current_user: user_model.User = Depends(get_current_user),db: Session = Depends(get_db)):
    """
    This function is used to delete the entity of the document.
    Input:
        entity: document_schemas.DeleteEntitySchema
        current_user: user_model.User
        db: Session
    Output:
        new_output: same format as /get-document/{document_id}    
    """
    document = document_crud.get_document(db,entity.document_id)
    # update = document_crud.get_last_update(db,document.id,current_user.id)
    update = document_crud.get_current_temporary_update(db,current_user.id,entity.update_id,entity.document_id)
    user_notes = update.get_user_notes()

    cur_entities, cur_relations = get_cur_relations_entities(document,update,user_notes)
    

    action = {
        "action":"delete",
        "target":"ent",
    }
    delete_content=[]
    for id in entity.ids:
        para_id, entity_id = document_schemas.UpdateEntitySchema.parse_id(id) 
        delete_content = [
            {
                "para_id":para_id,
                "ent_id":entity_id,
                "ent_type":e[1],
                "ent_text":e[-1],
                "head":e[2][0][0],
                "tail":e[2][0][1],
                "comment":e[-2] if len(e)==5 else ""
            }
            for e in cur_entities[para_id]["entities"] if e[0] == entity_id
        ]
        cur_entities[para_id]["entities"] = list(filter(lambda e: e[0] != entity_id, cur_entities[para_id]["entities"]))
        cur_relations[para_id]["entities"] = list(filter(lambda e: e[0] != entity_id, cur_relations[para_id]["entities"]))
        cur_relations[para_id]["relations"] =  list(filter(lambda r: entity_id not in (r[2][0][1],r[2][1][1]), cur_relations[para_id].get("relations",[])))

    
    action["content"] =  delete_content
    user_notes.append(action)
    
    num_ent, num_rel = utils.count_ent_and_rel(cur_relations)
    info_obj = {
        "id": document.id,
        "filename": document.FileName,
        "upload_time": document.get_infor()["upload_time"],
        "entities": num_ent,
        "relations": num_rel,
        "pages": document.get_infor()["pages"],
        "status": "completed"
    }
    
    update.set_infor(info_obj)
    update.set_user_notes(user_notes)
    update.set_entities(cur_entities)  
    update.set_relations(cur_relations)
    
    update = document_crud.modify_update_as_object(db,update.id,update)
    return return_formated_result(db,entity,document,update,cur_entities)

@router.post("/update-entity")
async def update_entity(update_info:document_schemas.UpdateEntitySchema,
                        current_user: user_model.User = Depends(get_current_user),
                        db: Session = Depends(get_db)):


    document = document_crud.get_document(db,update_info.document_id)
    update = document_crud.get_current_temporary_update(db,current_user.id,update_info.update_id,update_info.document_id)

    user_notes = update.get_user_notes()
    cur_entities, cur_relations = get_cur_relations_entities(document,update,user_notes)

    action = {
        "action":"update",
        "target":"ent",
    }
    update_content=[]
    new_entity_dict={
        "para_id": update_info.para_id,
        "entity_id":update_info.entity_id,
        "entity_type":update_info.type,
        "entity_text":cur_relations[update_info.para_id]["text"][update_info.head_pos:update_info.tail_pos],
        "head":update_info.head_pos,
        "tail":update_info.tail_pos,
    }
    print(new_entity_dict)
    object_for_confirmation, matched_entity_list, update = update_entity_function(db,
                                                                                  new_entity_dict,
                                                                                  cur_entities,
                                                                                  cur_relations,
                                                                                  user_notes,
                                                                                  update,
                                                                                  return_confirmation=True
                                                                                  )
    
    optional= {"update_content":object_for_confirmation,"matched_entities":matched_entity_list}
    return return_formated_result(db,update_info,document,update,cur_entities,optional=optional)

@router.post("/apply-update")
def apply_update(update_info:document_schemas.ApplyUpdateSchema,
                 current_user: user_model.User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    
    document = document_crud.get_document(db,update_info.document_id)
    update = document_crud.get_current_temporary_update(db,current_user.id,update_info.update_id,update_info.document_id)
    user_notes = update.get_user_notes()
    cur_entities, cur_relations = get_cur_relations_entities(document,update,user_notes)
    
    for entity_infor in update_info.list_update:
        current_entity = next((obj for obj in cur_entities[entity_infor.para_id]["entities"] if obj[0] == entity_infor.entity_id), [])
        current_entity_dict = utils.convert_entity_from_list_to_dict(current_entity)
        new_entity = next((obj for obj in cur_entities[update_info.new_entity.para_id]["entities"] if obj[0] == update_info.new_entity.entity_id), [])
        head_pos,tail_pos = find_new_entity_position_within_range(cur_entities,
                                                                  current_entity_dict,
                                                                  new_entity,
                                                                  entity_infor.para_id
                                                                )
        if head_pos<0 or tail_pos<0:
            continue
        entity_dict={
            "para_id": entity_infor.para_id,
            "entity_id":entity_infor.entity_id,
            "entity_type":update_info.new_entity.entity_type,
            "entity_text":update_info.new_entity.entity_text,
            "head":head_pos,
            "tail":tail_pos
        }
        print(entity_dict)
        _, _, update = update_entity_function(db,
                                              entity_dict,
                                              cur_entities,
                                              cur_relations,
                                              user_notes,
                                              update)
        
    return return_formated_result(db,update_info,document,update,cur_entities)


@router.post("/create-entity")
async def create_entity(entity:document_schemas.CreateEntitySchema,
                        current_user: user_model.User = Depends(get_current_user),
                        db: Session = Depends(get_db)): 
    sttime = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    utils.logging(log_folder,sttime)
    
    logging_state = {
        "API": "/create-entity",
        "comment": entity.comment,
        "para_id": entity.para_id,
        "position": json.dumps(utils.compose_position_object_from_Position(entity.position)),
        "document_id": entity.document_id,
        "update_id": entity.update_id,
        "scale_value": entity.scale_value,
    }
    utils.logging(log_folder, json.dumps(logging_state))

    document = document_crud.get_document(db,entity.document_id)
    # update = document_crud.get_last_update(db,document.id,current_user.id)
    update = document_crud.get_current_temporary_update(db,current_user.id,entity.update_id,entity.document_id)
    user_notes = update.get_user_notes()
    
    cur_entities = update.get_entities()
    if cur_entities==[]:
        cur_entities = document.get_entities()
        cur_entities = utils.execute_user_note_on_entities(user_notes,cur_entities)
    
    cur_relations = update.get_relations()
    if cur_relations == []:
        cur_relations = document.get_relations()
        cur_relations = utils.execute_user_note_on_relations(user_notes,cur_relations)

    old_text, old_pos,change_ids, para_data =load_para(document, user_notes)

    para_id,idx = utils.decide_new_pos(entity,old_pos)

    if len(idx) == 0:
        print(entity)
    print(para_id)
    print(idx)
    # return idx
    new_head = idx[0]
    new_tail = idx[-1]
    new_id_number = utils.decide_new_ent_number(cur_entities,user_notes,para_id)
    new_id = f"T{new_id_number}"
    def add_entitiy_tow_wrapper(wrapper, infor, para_id,new_id, new_head, new_tail):
        wrapper[para_id]["entities"].append([
            new_id,
            infor.comment,
            [[
                new_head,
                new_tail
            ]],
            infor.user_comment,
            wrapper[para_id]["text"][new_head:new_tail]
        ])
        return wrapper
    cur_entities = add_entitiy_tow_wrapper(cur_entities, entity, para_id,new_id, new_head, new_tail)
    cur_relations = add_entitiy_tow_wrapper(cur_relations, entity, para_id,new_id, new_head, new_tail)

    # print(cur_relations[7]["entities"])
    add_content=[
        {
            "para_id":para_id,
            "ent_type":entity.comment,
            "ent_id":new_id,
            "ent_text":cur_entities[ para_id]["text"][new_head:new_tail],
            "head": new_head,
            "tail": new_tail,
            "user_comment": entity.user_comment
        }
    ]
    print("add_content ",add_content)
    utils.logging(log_folder, json.dumps(add_content))
    action = {
        "action":"add",
        "target":"ent",
        "content":add_content
    }
    user_notes.append(action)

    num_ent, num_rel = utils.count_ent_and_rel(cur_relations)
    info_obj = {
        "id": document.id,
        "filename": document.FileName,
        "upload_time": document.get_infor()["upload_time"],
        "entities": num_ent,
        "relations": num_rel,
        "pages": document.get_infor()["pages"],
        "status": "completed"
    }
    
    update.set_infor(info_obj)
    update.set_entities(cur_entities)
    update.set_user_notes(user_notes)
    update.set_relations(cur_relations)
    
    update = document_crud.modify_update_as_object(db,update.id,update)
    new_relations = update.get_relations()
    # print(new_relations[7]["entities"])

    return return_formated_result(db,entity,document,update,cur_entities)

@router.post("/change-edit-status")
async def mark_edit(edit_entity: document_schemas.ChangeEditStatusSchema,current_user: user_model.User = Depends(get_current_user),db: Session = Depends(get_db)):
    # try:
        document = document_crud.get_document(db,edit_entity.document_id)
        # update = document_crud.get_last_update(db,edit_entity.document_id,current_user.id)
        update = document_crud.get_current_temporary_update(db,current_user.id,edit_entity.update_id,edit_entity.document_id)
        user_notes = update.get_user_notes()
        edit_status_change_list = user_notes[0]
        
        cur_relations = update.get_relations() or utils.execute_user_note_on_relations(user_notes,document.get_relations())
        
        id = edit_entity.id

        if document_schemas.UpdateEntitySchema.valid_id(id):
            para_id, entity_id = document_schemas.UpdateEntitySchema.parse_id(id)
            edit_status_change_list["content"][para_id] = utils.add_edit_status(edit_status_change_list["content"][para_id],"entities",entity_id)

            for rel in cur_relations[para_id].get("relations",[]):
                if rel[2][0][1] != entity_id: continue
                # FIXME: function add_edit_status did not add relation id into edit_status_change_list['relations']
                edit_status_change_list["content"][para_id] = utils.add_edit_status(edit_status_change_list["content"][para_id],"relations",rel[0])

        elif document_schemas.Relation.valid_id(id):
            para_id, entity_id = document_schemas.Relation.parse_id(id)
            edit_status_change_list["content"][para_id] = utils.add_edit_status(edit_status_change_list["content"][para_id],"relations",entity_id)

        else:
            raise ValueError("Invalid id")

        user_notes[0] = edit_status_change_list
        edit_status_lits = edit_status_change_list["content"]
        for index, note_list in enumerate(edit_status_lits):
            try:
                cur_relations[index]["edit_status"] = note_list
            except:
                print("+++++++++++++++++++++++++++")
                print(len(cur_relations))
                print("+++++++++++++++++++++++++++")
                print(index)
                print("++++++++++++++++++++++++++++++")
                print(note_list)

        update.set_user_notes(user_notes)
        update.set_relations(cur_relations)
        update = document_crud.modify_update_as_object(db,update.id,update)

        return "ok"

@router.post("/get-nodes-and-edges")
async def get_nodes_and_edges(
    infor: document_schemas.ChangeEditStatusSchema,
    db: Session = Depends(get_db),
    current_user: user_model.User = Depends(get_current_user)
):
    # Logging start
    now_str = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
    utils.logging(log_folder, now_str)
    utils.logging(log_folder, json.dumps({
        "API": "/get-nodes-and-edges",
        "document_id": infor.document_id,
        "update_id": infor.update_id,
        "id": infor.id
    }))

    # Parse identifiers
    para_id, entity_id = infor.id.split("_")
    para_id = int(para_id.replace("para", ""))

    # Fetch updates and relations
    last_update = document_crud.get_current_temporary_update(db, current_user.id, infor.update_id, infor.document_id)
    document = document_crud.get_document(db, infor.document_id)
    relations_data = last_update.get_relations() or document.get_relations()
    para = relations_data[para_id]
    entities = para["entities"]

    # Find entity type and name
    ent_type, ent_name = next(
        (ent[1], ent[-1]) for ent in entities if ent[0] == entity_id
    )
    print(ent_name)
    # Get graph
    relations = para.get("relations", [])
    all_graphs = utils.generate_graphs_manual(entities, relations)

    # Load visualization config
    config = utils.load_graph_config()

    if entity_id in all_graphs:
        result = all_graphs[entity_id]
    else:
        result = {
            "nodes": [{
                "id": "1",
                "data": {"label": f"{ent_type}: {ent_name}"},
                "position": config["default_node"]["position"],
                "className": ent_type,
                "sourcePosition": config["default_node"]["sourcePosition"],
                "targetPosition": config["default_node"]["targetPosition"]
            }],
            "edges": [],
            "options": config["options"]
        }

    utils.h_log(log_folder)
    return result