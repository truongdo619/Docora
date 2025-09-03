
import copy



from fastapi import APIRouter
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from sqlalchemy.orm import Session

from crud.psql import document as document_crud
from models.psql import user as user_model

from schemas import document as document_schemas

from utils.utils import get_cur_relations_entities, compose_update_event_content
from utils import utils

from .dependencies import get_current_user, return_formated_result, execute_update_on_entities_wrapper, get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
dev_account_id = 2335
HIGHLIGHTED_DOCUMENT_FOLDER_PATH="highlighted_documents"
DOCUMENTS_DIR="uploads"
log_folder = "dev_logs"
router = APIRouter()

@router.post("/edit-event")
async def edit_event(update_info: document_schemas.UpdateEventSchema, db:Session = Depends(get_db), current_user: user_model.User = Depends(get_current_user)):
    """
    This function is used to edit the event of the document.
    Input:
        update_infor: document_schemas.UpdateEventSchema
            document_id: int
            update_id: int
            para_id: int
            event: {
                event_id: str
                trigger_id: str
                arguments: List[List[str]]
            }
    Output:
        Same output as /get-document/{document_id}
    """
    document = document_crud.get_document(db,update_info.document_id)
    update = document_crud.get_last_update(db,update_info.document_id,current_user.id)
    user_notes = update.get_user_notes()
    para_data = document.get_paragraphs()
    if type(para_data[0]) == str:
        paragraphs,bbox, _, _ = utils.execute_user_note_on_paragraphs(user_notes,document.get_paragraphs(),document.get_positions())
    else:
        paragraphs,bbox = utils.get_bbox_n_text_seperated(para_data)
        paragraphs,bbox, _ , para_data  = utils.execute_user_note_on_paragraphs(user_notes,paragraphs,bbox,para_data=para_data)
    
    cur_entities, cur_relations = get_cur_relations_entities(document,update,user_notes)

    for index, event in enumerate(cur_relations[update_info.para_id].get("events_info",{}).get("events",[])):
        event_id, trigger_id, arguments = event
        new_arguments = [
            [role, arg_id.split("_", 1)[1]] if "para" in arg_id else [role, arg_id]
            for role, arg_id in update_info.event.arguments
        ]
        if event_id == update_info.event.event_id:
            cur_relations[update_info.para_id].get("events_info",{}).get("events",[])[index][2] = new_arguments
            cur_relations[update_info.para_id].get("events_info",{}).get("events",[])[index][1] = update_info.event.trigger_id
        for role, arg_id in new_arguments:
            if next((ent for ent in cur_relations[update_info.para_id].get("events_info",{}).get("entities",[]) if ent[0]==arg_id),None) is None:
                mentioned_entity = next(ent for ent in cur_relations[update_info.para_id].get("entities",[]) if ent[0]==arg_id)
                cur_relations[update_info.para_id].get("events_info",{}).get("entities",[]).append(mentioned_entity)
    
    old_event = next((event for event in cur_relations[update_info.para_id].get("events_info").get("events") if event[0]==update_info.event.event_id),[])
    update_content = compose_update_event_content(update_info, old_event)
    



    action = {
            "action":"update",
            "target":"event",
            "content":  update_content
        }
    user_notes.append(action)
    update.set_user_notes(user_notes)
    update.set_entities(cur_entities)  
    update.set_relations(cur_relations)  
    update = document_crud.modify_update_as_object(db,update.id,update)


    
    if update_info.trigger_new_head!=0 or update_info.trigger_new_tail!=0:
        trigger_entity = next(ent for ent in cur_relations[update_info.para_id].get("entities",[]) if ent[0]==update_info.event.trigger_id)
        dict_trigger_entity = utils.convert_entity_from_list_to_dict(trigger_entity)
        action = {
            "para_id":update_info.para_id,
            "ent_id":update_info.event.trigger_id,
            "ent_type": dict_trigger_entity.get("entity_type") ,
            "ent_text":cur_relations[update_info.para_id].get("text")[update_info.trigger_new_head:update_info.trigger_new_tail],
            "head":update_info.trigger_new_head,
            "tail":update_info.trigger_new_tail,
            "edit_status": "confirmed",
            "comment": dict_trigger_entity.get("comment"),
            "old_ent_type":dict_trigger_entity.get("entity_type"),
            "old_ent_text":dict_trigger_entity.get("entity_text"),
            "old_head":dict_trigger_entity.get("head"),
            "old_tail":dict_trigger_entity.get("tail"),
            "old_id": dict_trigger_entity.get("entity_id"),
            "old_comment": dict_trigger_entity.get("comment"),
            "old_edit_status": "none"
        }
        new_entity_dict = copy.deepcopy(dict_trigger_entity)
        new_entity_dict["head"] = update_info.trigger_new_head
        new_entity_dict["tail"] = update_info.trigger_new_tail
        new_entity_dict["ent_text"] = cur_relations[update_info.para_id].get("text")[update_info.trigger_new_head:update_info.trigger_new_tail]
        cur_relations = execute_update_on_entities_wrapper(new_entity_dict,cur_relations,update_info.para_id)
        cur_entities = execute_update_on_entities_wrapper(new_entity_dict,cur_entities,update_info.para_id)
        for trigger in cur_relations[update_info.para_id].get("events_info",{}).get("triggers",[]):
            if trigger[0] == update_info.event.trigger_id:
                trigger[2] = [[new_entity_dict["head"],new_entity_dict["tail"]]]
        action = {
            "action":"update",
            "target":"ent",
            "content": update_content
        }
        user_notes.append(action)
        update.set_user_notes(user_notes)
        update.set_entities(cur_entities)  
        update.set_relations(cur_relations)
        update = document_crud.modify_update_as_object(db,update.id,update)
    return return_formated_result(db,update_info,document,update,cur_entities)

@router.post("/delete-event")
async def delete_event(update_infor: document_schemas.DeleteEventSchema, db:Session = Depends(get_db), current_user: user_model.User = Depends(get_current_user)):
    """
    This function is used to edit the event of the document.
    Input:
        update_infor: document_schemas.UpdateEventSchema
            document_id: int
            update_id: int
            para_id: int
            event: {
                event_id: str
                trigger_id: str
                arguments: List[List[str]]
            }
    Output:
        Same output as /get-document/{document_id}
    """
    document = document_crud.get_document(db,update_infor.document_id)
    update = document_crud.get_last_update(db,update_infor.document_id,current_user.id)
    user_notes = update.get_user_notes()
    para_data = document.get_paragraphs()
    if type(para_data[0]) == str:
        paragraphs,bbox, _, _ = utils.execute_user_note_on_paragraphs(user_notes,document.get_paragraphs(),document.get_positions())
    else:
        paragraphs,bbox = utils.get_bbox_n_text_seperated(para_data)
        paragraphs,bbox, _ , para_data  = utils.execute_user_note_on_paragraphs(user_notes,paragraphs,bbox,para_data=para_data)
    
    cur_entities, cur_relations = get_cur_relations_entities(document,update,user_notes)


    cur_relations[update_infor.para_id]["events_info"]["events"] = list(filter(lambda e: e[0] != update_infor.event_id, cur_relations[update_infor.para_id].get("events_info",{}).get("events",[])))

    update_content = {
        "para_id":update_infor.para_id,
        "event_id":update_infor.event_id
    }

    action = {
            "action":"delete",
            "target":"event",
            "content":  update_content
        }
    user_notes.append(action)
    update.set_user_notes(user_notes)
    update.set_entities(cur_entities)  
    update.set_relations(cur_relations)  
    update = document_crud.modify_update_as_object(db,update.id,update)

    return return_formated_result(db,update_infor,document,update,cur_entities)
