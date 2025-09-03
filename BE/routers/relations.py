from fastapi import APIRouter
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from sqlalchemy.orm import Session

from crud.psql import document as document_crud
from models.psql import user as user_model

from schemas import document as document_schemas

from ner_re_processing import convert_to_output_v2

from utils import utils

from .dependencies import get_current_user, format_output, get_db, load_para

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
dev_account_id = 2335
HIGHLIGHTED_DOCUMENT_FOLDER_PATH="highlighted_documents"
DOCUMENTS_DIR="uploads"
log_folder = "dev_logs"
router = APIRouter()


@router.post("/update-relations")
async def update_relation(entity:document_schemas.UpdateRelationSchema,
                          current_user: user_model.User = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    # TODO: add user note and synchronize with 1 update only
    # update,document = collect_update(db,current_user,entity)

    document = document_crud.get_document(db,entity.document_id)
    update = document_crud.get_current_temporary_update(db,current_user.id,entity.update_id,entity.document_id)
    user_notes = update.get_user_notes()

    # id = entity.entity_id
    # para_id = int(id.split("_")[0].replace("para",""))
    # entity_id = id.split("_")[1]

    para_id, entity_id = document_schemas.UpdateEntitySchema.parse_id(entity.entity_id)

    new_relations = entity.relations 
    converted_relations = []
    for n_rel in new_relations:

        if n_rel.id is None:
            r_id = " "
        elif "para" in n_rel.id:
            para_id_, r_id = document_schemas.Relation.parse_id(n_rel.id) #n_rel.id.split("_")[1]
            assert para_id_ == para_id
        else:
            raise ValueError("malformed relation id")
            # r_id = n_rel.id

        rel_type = n_rel.type
        para_id_, arg2_id = document_schemas.UpdateEntitySchema.parse_id(n_rel.arg_id) #n_rel.arg_id.split("_")[1]
        assert para_id_ == para_id
        converted_relations.append([r_id,rel_type,[["Arg1",entity_id],["Arg2",arg2_id]]])


    print("new rel ",converted_relations) ######


    # cur_relations = update.get_relations()
    # if cur_relations == []:
    #     cur_relations = document.get_relations() #######
    #     # cur_relations = utils.execute_user_note_on_entities(user_notes,cur_relations)
    #     cur_relations = utils.execute_user_note_on_relations(user_notes,cur_relations)
    # FIXME: usernote or relation is not updated

    cur_relations = update.get_relations() or utils.execute_user_note_on_relations(user_notes,document.get_relations())
    original_relations = cur_relations[para_id].get("relations",[]) 
    new_relations, user_notes = utils.update_relations(original_relations,converted_relations,entity_id,user_notes,para_id)
    cur_relations[para_id]["relations"] = new_relations

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
    update.set_relations(cur_relations)
    
    paragraphs, old_bboxs, change_ids, para_data = load_para(document,user_notes)

    # if type(para_data[0]) == str:
    #     new_output, _, _ = convert_to_output_v2(cur_relations, old_bboxs, paragraphs)
    # else:
    #     new_output, _, _ = convert_to_output_v2(cur_relations, old_bboxs, paragraphs, para_data=para_data)

    new_output, _, _ = convert_to_output_v2(cur_relations, old_bboxs, paragraphs, 
                            para_data=para_data if type(para_data[0]) != str else None)

    update = document_crud.modify_update_as_object(db,update.id,update)
    # new_output["document_id"] = entity.document_id
    # new_output["update_id"] = update.id
    # new_output["filename"] = document.FileName
    # user_notes = update.get_user_notes()
    # v_list = utils.collect_visible_list(user_notes)
    # new_output = utils.apply_visibility_to_result(new_output,v_list)
    new_output = format_output(new_output,entity.document_id,document.FileName,update.id,update.get_user_notes(),apply_visibility=True)

    return new_output
