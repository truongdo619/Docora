from sqlalchemy.orm import Session
from models.psql.document import Document, Update
from sqlalchemy import and_
from datetime import datetime, timedelta
import uuid
import random

def generate_unique_id(db: Session, model, id_field="id"):
    """
    Generate a unique 8-digit or longer ID for a given SQLAlchemy model.

    :param db: The SQLAlchemy session.
    :param model: The SQLAlchemy model to check uniqueness against.
    :param id_field: The name of the ID field in the model.
    :return: A unique numeric ID.
    """
    while True:
        # Generate a random 8-digit number or longer
        unique_id = random.randint(10000000, 99999999)
        
        # Check if the ID already exists in the database
        existing = db.query(model).filter(getattr(model, id_field) == unique_id).first()
        if not existing:
            return unique_id

def serialize(value):
    if isinstance(value, datetime):
        return value.strftime("%Y/%m/%d, %H:%M:%S")
    return value

def convert_statistic_info(statistic_info):
    """
    Convert datetime objects in the dictionary to ISO 8601 strings.
    """
    
    
    return {key: serialize(value) for key, value in statistic_info.items()}

def create_document(db: Session, user_id: int, paragraphs: list, file_path: str, file_name: str, entities: dict, relation: dict, event: dict, position: dict, infor: dict):
    
    document_id = generate_unique_id(db, Document)
    document = Document(
        id=document_id,  # Generate a new UUID for PostgreSQL
        UserID=user_id,
        FilePath=file_path,
        FileName=file_name,
        Paragraphs=paragraphs,  # Directly assign JSONB fields
        Entities=entities,
        Relation=relation,
        Event=event,
        Position=position,
        StatisticInfor=infor,
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    document.UploadTime = serialize(document.UploadTime)
    return document

# def update_document(db: Session, document_id: int , document_data: Document):
#     doc = db.query(Document).filter_by(id=document_id).first()
#     if doc:

#         doc.Paragraphs = document_data.Paragraphs
#         doc.Entities = document_data.Entities
#         doc.Relation = document_data.Relation
#         doc.Event = document_data.Event
#         doc.Position = document_data.Position
#         doc.StatisticInfor = convert_statistic_info(document_data.StatisticInfor)
#         db.commit()
#         db.refresh(doc)
#         doc.UploadTime = serialize(doc.UploadTime)
#         return doc

def update_document(db:Session,document_id: int,document: Document ):
    doc = db.query(Document).filter_by(id=document_id).first()
    if doc:
        print("start matching infor")
        doc.set_paragraphs(document.get_paragraphs())
        doc.set_entities(document.get_entities())
        doc.set_relations(document.get_relations())
        doc.set_events(document.get_events())
        doc.set_positions(document.get_positions())
        # doc.set_infor(document.get_infor())
        doc.set_infor(convert_statistic_info(document.get_infor()))
        doc.UploadTime = serialize(doc.UploadTime)
        print("done matching infor")
        print("start commit")
        db.commit()
        db.refresh(doc)
        return doc

def get_document(db: Session, document_id: int ):
    return db.query(Document).filter(Document.id == document_id).first()

def delete_document(db: Session, document_id: int ):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if doc:
        # Delete related updates first
        db.query(Update).filter(Update.DocumentID == document_id).delete()
        db.delete(doc)
        db.commit()
        return {"message": "Document deleted successfully"}
    else:
        return {"error": "Document not found"}

def create_update_as_object(db:Session, sample_object: Update):
    udt_id = generate_unique_id(db, Update)
    update = Update(
        id=udt_id,  
        UserID=sample_object.UserID,
        DocumentID=sample_object.DocumentID,
    )
    update.set_paragraphs(sample_object.get_paragraphs())
    update.set_entities(sample_object.get_entities())
    update.set_relations(sample_object.get_relations())
    update.set_events(sample_object.get_events())
    update.set_positions(sample_object.get_positions())
    update.set_user_notes(sample_object.get_user_notes())
    db.add(update)
    db.commit()
    db.refresh(update)
    return update


def create_update(db: Session, user_id: int, document_id: int , paragraphs: list, entities: dict, relation: dict, event: dict, position: dict, user_note: dict,infor=dict):
    
    udt_id = generate_unique_id(db, Update)
    print("infor ",type(infor))
    print("paragraphs ",type(paragraphs))
    print("entities ",type(entities))
    print("relation ",type(relation))
    print("event ",type(event))
    print("position ",type(position))
    print("user_note ",type(user_note))
    
    update = Update(
        id=udt_id,  # Generate a new UUID for PostgreSQL
        UserID=user_id,
        DocumentID=document_id,
        Paragraphs=paragraphs,
        Entities=entities,
        Relation=relation,
        Event=event,
        Position=position,
        UserNote="",
        StatisticInfor=infor
    )
    update.set_user_notes(user_note)
    db.add(update)
    db.commit()
    db.refresh(update)
    return update

def get_update_of_user(db: Session, document_id: int,update_id: int, user_id:int):
    update = db.query(Update).filter(and_(Update.DocumentID == document_id,Update.id == update_id,Update.UserID==user_id)).first()
    if update:
        return update
        # return {
        #     "id": update.id,
        #     "DocumentID": update.DocumentID,
        #     "Paragraphs": update.get_paragraphs(),
        #     "FilePath": update.FilePath,
        #     "FileName": update.FileName,
        #     "Entities": update.get_entities(),
        #     "Relation": update.get_relation(),
        #     "Event": update.get_event(),
        #     "UserNote": update.get_user_note(),
        #     "Position": update.get_position(),
        #     "UserID": update.UserID
        # }
def get_update(db: Session, update_id: int ):
    return db.query(Update).filter(Update.id == update_id).first()

def update_update(db: Session, update_id: int , paragraphs: list, entities: dict, relation: dict, event: dict, position: dict, user_note: dict):
    update_to_update = db.query(Update).filter_by(id=update_id).first()
    if update_to_update:
        update_to_update.Paragraphs = paragraphs
        update_to_update.Entities = entities
        update_to_update.Relation = relation
        update_to_update.Event = event
        update_to_update.Position = position
        update_to_update.set_user_notes(user_note)
        db.commit()
        db.refresh(update_to_update)
        return update_to_update
    
def get_update_as_doc_and_user(db: Session, document_id: int, update_id: int, user_id: int):
    update = db.query(Update).filter(and_(Update.id == update_id,Update.DocumentID == document_id, Update.UserID==user_id)).first()
    if update:
        return update

def get_update_by_doc_and_user(db: Session, document_id: int, user_id: int):
    update = db.query(Update).filter(and_(Update.DocumentID == document_id, Update.UserID==user_id)).first()
    if update:
        return update
    else:
        document = get_document(db,document_id)
        return init_quick_update(db,document,user_id,document_id )

def modify_update_as_object(db: Session, update_id: int , modified_update: Update):
    print(f"doing update at id: {update_id}")
    update_to_update = db.query(Update).filter_by(id=update_id).first()
    if update_to_update:

        update_to_update.Paragraphs = modified_update.Paragraphs
        update_to_update.Entities = modified_update.Entities
        update_to_update.Relation = modified_update.Relation
        update_to_update.Event = modified_update.Event
        update_to_update.Position = modified_update.Position
        update_to_update.UserNote = modified_update.UserNote
        
        # print("got in commit command")
        # print(update_to_update.UserNote)
        # db.commit()
        # db.refresh(update_to_update)
        # print(update_to_update.UserNote)
        # return update_to_update
        print("got in commit command")
        # print(f"Updated UserNote: {update_to_update.Paragraphs}")
        new_relations = update_to_update.get_relations()
        # print("this come from crud ", new_relations[7]['entities'])
        # print(update_to_update.Relation)
        try:
            # Commit the changes to the database
            db.merge(update_to_update)
            # db.flush() 
            db.commit()
            db.refresh(update_to_update)
            # print(f"After commit, UserNote: {update_to_update.Paragraphs}")
            new_relations = update_to_update.get_relations()
            # print("this come from crud ", new_relations[7]['entities'])
            return update_to_update
        except Exception as e:
            # Catch any errors during commit and print them
            print(f"An error occurred during commit: {e}")
            db.rollback()  # Rollback in case of error
            return None

def delete_update(db: Session, update_id: int ):
    update_to_delete = db.query(Update).filter_by(id=update_id).first()
    if update_to_delete:
        db.delete(update_to_delete)
        db.commit()

def get_user_document(db: Session, user_id: int):
    return db.query(Document).filter(Document.UserID == user_id).all()

def get_last_update(session: Session, document_id: int,user_id: int):
    """
    Fetches the last Update instance for a given DocumentID.
    
    Parameters:
        session (Session): The SQLAlchemy session to use for the query.
        document_id (int): The DocumentID to filter the Update instances.
    
    Returns:
        Update: The last Update instance for the specified DocumentID or None if not found.
    """
    document = get_document(session,document_id)
    last_update = session.query(Update).filter(Update.DocumentID == document_id).order_by(Update.UploadDate.desc()).first()
    if last_update:
        return last_update
    else:
        # count the number of paragraphs base on text (old way), cause bug because of number of paragraphs change after preparation of re_model
        new_update = init_quick_update(session, document, user_id, document_id)
        return new_update

def reformat_time(time_str, hours_to_add=9):
    # Parse the time string to a datetime object
    dt_object = datetime.fromisoformat(time_str)
    
    # Add the specified number of hours
    dt_object += timedelta(hours=hours_to_add)
    
    # Format the datetime object to the desired format
    formatted_time = dt_object.strftime('%d-%m-%Y %H:%M:%S')
    
    return formatted_time

def get_list_updates(db:Session,user_id:int, document_id:int):
    updates = db.query(Update).filter(and_(Update.DocumentID==document_id, Update.UserID==user_id))
    document = get_document(db,document_id)
    try:
        result = [{"id":0,"real_id":-1,"name":"Upload Document", "upload_time": reformat_time(document.get_infor()["upload_time"])}]
    except:
        result = [{"id":0,"real_id":-1,"name":"Upload Document", "upload_time": document.get_infor()["upload_time"]}]
    sorted_updates = sort_object(updates)
    for index, update in enumerate(sorted_updates):
        
        result.append({"id":index+1,"real_id":update.id,"name":update.Name, "upload_time": update.UploadDate})
    return result

# def sort_objects_by_id(obj_list):
#     # TODO: change to sort using UploadDate and deal with None object
#     return sorted(obj_list, key=lambda x: x.id)


def sort_object(obj_list):
    """
    Sorts a list of objects by their UploadDate attribute.
    Objects with UploadDate == None will be placed at the end.
    """
    return sorted(
        obj_list,
        key=lambda x: (
            x.UploadDate is None,              # False (has date) sorts before True (None)
            x.UploadDate or datetime.max       # For None, use a max datetime so they sort last
        )
    )

def init_quick_update(session: Session, document, user_id,document_id):
    num_para = len(document.get_entities())
        # -> solution : count number pf para base on relations or entities.
        # num_para = len(document.get_paragraphs())
    init_content = []
    for i in range(num_para):
        init_content.append({
            "entities":[],
            "relations":[]
        })
    init_user_note = [{
        "action":"update",
        "target":"edit_status",
        "content":init_content
    }]
    # current_time_lock = datetime.now()
    # #### in the case that decide to save also the paragraph, may be not neccessary
    # new_update = create_update(session, user_id,document_id,document.get_paragraphs(),document.get_entities(),[],[],[],init_user_note)
    ###### in the case that no save para
    infor = document.get_infor()
    new_update = create_update(session, user_id,document_id,[],document.get_entities(),document.get_relations(),[],[],init_user_note,infor )
    curtime = datetime.now()
    uploadtime = curtime.strftime('%d-%m-%Y %H:%M:%S')
    new_update.UploadDate = uploadtime
    new_update = modify_update_as_object(session,new_update.id,new_update)
    return new_update

def prune_branch_from_update_id(db:Session, user_id:int, update_id: int, document_id: int):
    child_updates = db.query(Update).filter(and_(Update.DocumentID==document_id, Update.UserID==user_id, Update.FatherID == update_id))
    print("pruning on update id ", update_id)
    if child_updates:
        for update in child_updates:
            prune_branch_from_update_id(db,user_id,update.id,document_id)
    # else:
    
    print("deleting on update id ", update_id)
    update = db.query(Update).filter(and_(Update.DocumentID==document_id, Update.UserID==user_id, Update.id == update_id)).first()
    db.delete(update)
    db.commit()

def get_current_temporary_update(db:Session, user_id:int, update_id: int, document_id: int):
    if update_id <0:
        updates = db.query(Update).filter(and_(Update.DocumentID==document_id, Update.UserID==user_id))
        if updates:
            prune_branch_from_update_id(db,user_id,updates[0].id,document_id)
        
        return get_last_update(db,document_id,user_id)
    else:
        cur_update = get_update_as_doc_and_user(db,document_id,update_id,user_id)
        if cur_update.checkpoint == 1:
            print("start pruning branch")
            child_updates = db.query(Update).filter(and_(Update.DocumentID==document_id, Update.UserID==user_id, Update.FatherID == update_id))
            for child_update in child_updates:
                prune_branch_from_update_id(db,user_id,child_update.id,document_id)
            # new_update = get_last_update(db,document_id,user_id)
            new_update = init_quick_update(db, cur_update, user_id, document_id)
            new_update.FatherID = update_id
            new_update.set_user_notes(cur_update.get_user_notes())
            new_update.set_entities(cur_update.get_entities())
            modify_update_as_object(db,new_update.id,new_update)
            return new_update
        else:
            return cur_update