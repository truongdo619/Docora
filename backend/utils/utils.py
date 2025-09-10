import os
import copy
import json
import re
from typing import Optional
from pathlib import Path
import pymupdf 
# from pymupdf import Rect
# import fitz
import numpy as np
from schemas.document import Rect
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


gmail_app_password="goir ptrm pzau pikb"
SECRET_KEY = "2147483647"
REFRESH_SECRET_KEY = "2147483629"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 900
RESET_TOKEN_EXPIRE_MINUTES = 300
REFRESH_TOKEN_EXPIRE_DAYS = 90

ROOT_PAGE_ADDRESS ="http://150.65.242.92:3001/#/reset-password/?token="

# https://www.jaist.ac.jp/is/labs/nguyen-lab/systems/polyminder/engine_v3.2/forget-password/

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
CONFIG_PATH = Path("configs/default_graph_config.json")
color_map = {
    "POLYMER": "#ff4500",
    "PROP_NAME": "#1e90ff",
    "CHAR_METHOD": "#A0778A",
    "POLYMER_FAMILY": "#00ff00",
    "PROP_VALUE": "#ffd700",
    "MONOMER": "#B8BDD3",
    "OTHER_MATERIAL": "#1976d2",
    "COMPOSITE": "#8400ff",
    "SYN_METHOD": "#f09bc5",
    "EVENT": "#32CD32",
    "CONDITION": "#ffe000",
    "MATERIAL_AMOUNT": "#a0522d",
    "REF_EXP": "#bd0ea5",
    "INORGANIC": "#00ffff",
    "ORGANIC": "#ff00ff"
}


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=150)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=150)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str, secret_key: str):
    try:
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def levenshtein_edit_list(text1, text2):
    len1, len2 = len(text1), len(text2)
    dp = np.arange(len2 + 1)
    prev = np.zeros(len2 + 1, dtype=int)

    for i in range(1, len1 + 1):
        prev, dp = dp, prev
        dp[0] = i
        for j in range(1, len2 + 1):
            cost = 0 if text1[i - 1] == text2[j - 1] else 1
            dp[j] = min(dp[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)

    i, j, edit_list = len1, len2, []
    while i > 0 and j > 0:
        if text1[i - 1] == text2[j - 1]:
            edit_list.append(('match', i - 1, j - 1))
            i -= 1; j -= 1
        elif dp[j] == prev[j - 1] + 1:
            edit_list.append(('replace', i - 1, j - 1))
            i -= 1; j -= 1
        elif dp[j] == prev[j] + 1:
            edit_list.append(('delete', i - 1, j))
            i -= 1
        else:
            edit_list.append(('insert', i, j - 1))
            j -= 1

    while i > 0: edit_list.append(('delete', i - 1, j)); i -= 1
    while j > 0: edit_list.append(('insert', i, j - 1)); j -= 1
    return edit_list[::-1]

def generate_bounding_boxes(text1, bbox1, text2):
    bbox2 = []
    last_bbox = None
    
    for op, idx1, _ in levenshtein_edit_list(text1, text2):
        if op != 'delete':
            if op == 'insert':
                # Default to the position of the first character's bbox (bbox1[0])
                new_bbox = {
                    "x1": bbox1[0]["x1"],
                    "y1": bbox1[0]["y1"],
                    "x2": bbox1[0]["x2"],
                    "y2": bbox1[0]["y2"],
                    "width": bbox1[0]["width"],
                    "height": bbox1[0]["height"],
                    "pageNumber": bbox1[0]["pageNumber"]
                }
            else:
                # For 'replace' or 'equal', use the bbox1 at idx1
                new_bbox = bbox1[idx1]
            
            # If we already have a bbox, adjust the x2 to extend to the current bbox
            if last_bbox:
                last_bbox["x2"] = new_bbox["x2"]  # Extend the x2 to match the current new_bbox
            
            # Add the new bounding box to bbox2
            bbox2.append(new_bbox)
            last_bbox = new_bbox  # Update the last_bbox reference

    return bbox2

def organize_new_box(old_paragraph, old_box, new_paragraph):
    return [generate_bounding_boxes(op, ob, np) if op != np else ob for op, ob, np in zip(old_paragraph, old_box, new_paragraph)]

def filter_by_arg1(input_list, arg1_value):
    # Create a list to store the matching elements
    matching_elements = []

    # Iterate over the elements in the input list
    for element in input_list:
        # Check if the element has a matching Arg1 value
        for arg in element[2]:
            if arg[0] == "Arg1" and arg[1] == arg1_value:
                matching_elements.append(element)
                break

    return matching_elements

def compare_versions(original_list, new_list):
    deleted_elements = []
    added_elements = []
    updated_elements = []

    # Convert the lists into dictionaries for easier comparison
    original_dict = {element[0]: element for element in original_list}
    new_dict = {element[0]: element for element in new_list}

    # Check for deleted and updated elements
    for key in original_dict:
        if key not in new_dict:
            deleted_elements.append(original_dict[key])
        elif original_dict[key] != new_dict[key]:
            updated_elements.append(new_dict[key])

    # Check for added elements
    for key in new_dict:
        if key not in original_dict:
            added_elements.append(new_dict[key])

    return deleted_elements, updated_elements, added_elements
    # original_list = update_relation(original_list,updated_elements)
    # original_list = add_relation(original_list,added_elements)
    # original_list = delete_relations(original_list,deleted_elements)
    # return original_list

def delete_relations(original_rels,deleted_rel,para_id):
    delete_id = []
    for rel in deleted_rel:
        delete_id.append(rel[0])
    action = {
        "action":"delete",
        "target":"rel"
    }
    action_content = []
    for rel in original_rels:
        if rel[0] in delete_id:
            action_content.append({
                "para_id":para_id,
                "rel":rel
                })
            original_rels.remove(rel)
    action["content"] = action_content
    return original_rels, action

def update_relation(original_rels,updated_rel,para_id):
    update_id = []
    # print(updated_rel)
    for rel in updated_rel:
        update_id.append(rel[0])
    
    action = {
        "action":"update",
        "target":"rel"
    }
    action_content = []
    for index,rel in enumerate(original_rels):
        if rel[0] in update_id:
            original_rels[index] = updated_rel[update_id.index(rel[0])]
            action_content.append({
                    "para_id":para_id,
                    "rel":updated_rel[update_id.index(rel[0])]
                })
            # print(updated_rel[update_id.index(rel[0])])
    # print(original_rels)
    action["content"] = action_content
    return original_rels, action

def decide_new_num_rel(original_rels, user_notes):
    extra_number = 0
    for action in user_notes:
        if action["action"]=='add' and action["target"]=="relation":
            extra_number+=1
    return len(original_rels) + extra_number

def add_relation(original_rels,added_rel,user_notes,para_id):
    action = {
        "action":"add",
        "target":"rel"
    }
    action_content=[]
    for rel in added_rel:
        id = decide_new_num_rel(original_rels, user_notes)+1
        new_id = f"R{id}"
        rel[0] = new_id
        original_rels.append(rel)
        action_content.append({
                "para_id":para_id,
                "rel":rel
                })
    action["content"] = action_content
    return original_rels, action

def update_relations(total_orginal_list,new_list,arg1_id,user_notes,para_id):
    original_list_arg1 = filter_by_arg1(total_orginal_list,arg1_id)
    deleted_elements, updated_elements, added_elements = compare_versions(original_list_arg1, new_list)
    total_orginal_list, add_action = add_relation(total_orginal_list,added_elements,user_notes,para_id)
    total_orginal_list, upd_action = update_relation(total_orginal_list,updated_elements,para_id)
    total_orginal_list, del_action = delete_relations(total_orginal_list,deleted_elements,para_id)
    user_notes.extend([add_action,upd_action,del_action])
    return total_orginal_list, user_notes

def count_ent(ent_list):
    num = 0
    for ent in ent_list:
        num += len(ent["entities"])
    return num

def count_ent_and_rel(obj_list):
    num_ent = 0
    num_rel = 0
    for obj in obj_list:
        num_ent += len(obj["entities"])
        if "relations" in obj:
            num_rel+= len(obj["relations"])
    return num_ent, num_rel

import time
import random
def generate_id():
    unique_id = int(time.time() * 1000) + random.randint(0, 999)
    print(unique_id)
    return unique_id

def reorder_all(new_order, list_object):
    copy_list_object = copy.deepcopy(list_object)
    new_list_object = []
    for index in new_order:
        new_list_object.append(copy_list_object[index])
    return new_list_object

def execute_one_note_on_entities(user_note,entities):
    actions = user_note["action"]
    for ent in user_note["content"]:
        para_id = ent["para_id"]
        ent_id = ent["ent_id"]
        ent_type = ent["ent_type"]
        ent_text = ent["ent_text"]
        user_comment=ent.get("comment","")
        if actions=="add":
            entities[para_id]["entities"].append([
                ent_id,
                ent_type,
                [[ent["head"],ent["tail"]]],
                user_comment,
                ent_text
            ])
        if actions=="delete":
            for e in entities[para_id]["entities"]:
                if e[1] == ent_type and e[-1]==ent_text and e[2][0][0]==ent["head"] and e[2][0][1]==ent["tail"] :
                    entities[para_id]["entities"].remove(e)
        
        if actions=="update":
            print(actions)
            for index, e in enumerate(entities[para_id]["entities"]):
                if e[1]==ent["old_ent_type"] and e[-1]==ent["old_ent_text"] and e[2][0][0]==ent["old_head"] and e[2][0][1]==ent["old_tail"] :
                    entities[para_id]["entities"][index] = [
                                                                ent_id,
                                                                ent_type,
                                                                [[ent["head"],ent["tail"]]],
                                                                user_comment,
                                                                ent_text
                                                            ]
        return entities
    
def execute_user_note_on_entities(user_notes, entities):
    for note in user_notes:
        if note["target"]=="ent":
            entities = execute_one_note_on_entities(note,entities)
        elif note["target"]=="all":
            entities = reorder_all(note['content'][0]['new_order'], entities)
        else:   
            continue
    return entities

def execute_one_note_on_paragraphs(user_note, paragraphs, old_bboxs, change_ids):
    new_para = copy.deepcopy(paragraphs)
    new_bbox = copy.deepcopy(old_bboxs)
    for para in user_note["content"]:
        # print(para)
        para_id = para["para_id"]
        text = para["text"]
        change_ids.append(para_id)
        changed_pos = organize_new_box([paragraphs[para_id]],[old_bboxs[para_id]],[text])
        new_bbox[para_id] = changed_pos[0]
        new_para[para_id] = text
    return new_para, new_bbox, change_ids

def execute_one_note_on_event(user_note, wrapper):
    new_wrapper = copy.deepcopy(wrapper)
    para_id = user_note["content"]["para_id"]
    event_id = user_note["content"]["event_id"]
    if user_note["action"] =="update":
        for index, event in enumerate(new_wrapper.get("events_info",{}).get("event",[])):
            event_id, trigger_id, arguments = event
            if event_id == event_id:
                new_wrapper.get("events_info",{}).get("event",[])[index][2] = user_note["content"]["new_arguments"]
                new_wrapper.get("events_info",{}).get("event",[])[index][1] = user_note["content"]["new_trigger_id"]
    if user_note["action"] =="delete":
        new_wrapper[para_id]["events_info"]["events"] = list(filter(lambda e: e[0] != event_id, wrapper[para_id]["events_info"].get("events",[])))
    return new_wrapper

def execute_user_note_on_paragraphs(user_notes, paragraphs, old_bboxs,para_data=None):
    change_ids = []
    # changed_para = []
    print(len(paragraphs))
    print(len(old_bboxs))
    new_para = copy.deepcopy(paragraphs)
    new_bbox = copy.deepcopy(old_bboxs)
    for note in user_notes:
        if note["target"]=="para":
            # for para in note["content"]:
            #     # print(para)
            #     para_id = para["para_id"]
            #     text = para["text"]
            #     change_ids.append(para_id)
            #     changed_pos = organize_new_box([paragraphs[para_id]],[old_bboxs[para_id]],[text])
            #     new_bbox[para_id] = changed_pos[0]
            #     new_para[para_id] = text
            new_para, new_bbox, change_ids = execute_one_note_on_paragraphs(note, new_para, new_bbox, change_ids)
        elif note["target"]=="all":
            print("doing reordering")
            new_para = reorder_all(note['content'][0]['new_order'], new_para)
            new_bbox = reorder_all(note['content'][0]['new_order'], new_bbox)
            if para_data is not None:
                para_data = reorder_all(note['content'][0]['new_order'], para_data)
        else:
            continue
    # if para_data is not None:
    return new_para , new_bbox, change_ids, para_data
    # else:
    #     return new_para , new_bbox, change_ids


def execute_one_note_on_relations(user_note, relations):
    action = user_note["action"]
    if action =="add":
        for packed_rel in user_note["content"]:
            para_id = packed_rel["para_id"]
            rel = packed_rel["rel"]
            relations[para_id]["relations"].append(rel)
    if action =="delete":
        for packed_rel in user_note["content"]:
            para_id = packed_rel["para_id"]
            rel = packed_rel["rel"]
            for index, relation in enumerate(relations[para_id]["relations"]):
                if relation[1] == rel[1] and relation[2] == rel[2] :
                    relations[para_id]["relations"].remove(relation)
    if action == "update":
        for packed_rel in user_note["content"]:
            para_id = packed_rel["para_id"]
            rel = packed_rel["rel"]
            r_id = rel[0]
            for index, orel in enumerate(relations[para_id]["relations"]):
                if orel[1] == rel[1] and orel[2] == rel[2] :
                    rel[0] = relations[para_id]["relations"][index][0]
                    relations[para_id]["relations"][index] = rel
    return relations

def execute_one_note_on_edit_status(user_note, relations):
    edit_status_lits = user_note["content"]
    for index, note_list in enumerate(edit_status_lits):
        try:
            relations[index]["edit_status"] = note_list
        except:
            print("+++++++++++++++++++++++++++")
            print(len(relations))
            print("+++++++++++++++++++++++++++")
            print(index)
            print("++++++++++++++++++++++++++++++")
            print(note_list)
    return relations

def execute_user_note_on_relations(user_notes, relations):
    # check if result is no longer keep the id when user make update, check both text and type
    for note in user_notes:
        if note["target"] == "relation":
            relations = execute_one_note_on_relations(note, relations)
        elif note["target"]=="edit_status":
            # edit_status_lits = note["content"]
            # for index, note_list in enumerate(edit_status_lits):
            #     try:
            #         relations[index]["edit_status"] = note_list
            #     except:
            #         print("+++++++++++++++++++++++++++")
            #         print(len(relations))
            #         print("+++++++++++++++++++++++++++")
            #         print(index)
            #         print("++++++++++++++++++++++++++++++")
            #         print(note_list)
            relations = execute_one_note_on_edit_status(note, relations)
        elif note["target"]=="all":
            relations = reorder_all(note['content'][0]['new_order'], relations)
            # new_bbox = reorder_all(note['content']['new_order'], new_bbox)
        elif note["target"] == "ent":
            print(note)
            relations = execute_one_note_on_entities(note, relations)
        elif note["target"]=="event":
            relations = execute_one_note_on_event(note, relations)
            
    return relations

# def add_init_edit_status_2_relation_list(relations):
    
def execute_user_note_on_all_data(usernotes, paragraphs, bboxs, entities, relations,para_data=None):
    new_para = copy.deepcopy(paragraphs)
    new_bbox = copy.deepcopy(bboxs)
    change_ids = []
    for note in usernotes:
        if note["target"]=="edit_status":
            relations = execute_one_note_on_edit_status(note, relations)
        elif note["target"] == "relation":
            relations = execute_one_note_on_relations(note, relations)
        elif note["target"]=="para":
            new_para, new_bbox, change_ids = execute_one_note_on_paragraphs(note, new_para, new_bbox, change_ids)
        elif note["target"]=="ent":
            # In this part, use relations along with entities because relation itself also contain "entities" information
            relations = execute_one_note_on_entities(note, relations)
            entities = execute_one_note_on_entities(note, entities)
        elif note["target"]=="all":
            relations = reorder_all(note['content'][0]['new_order'], relations)
            new_para = reorder_all(note['content'][0]['new_order'], new_para)
            new_bbox = reorder_all(note['content'][0]['new_order'], new_bbox)
            entities = reorder_all(note['content'][0]['new_order'], entities)
            if para_data is not None:
                para_data = reorder_all(note['content'][0]['new_order'], para_data)
            # This line is for edit status 
            # relations = reorder_all(note['content'][0]['new_order'], relations) 

    return new_para, new_bbox, entities, relations, change_ids, para_data

def decide_new_ent_number(entities,user_note,para_id):
    base_number = len(entities[para_id]["entities"])
    extra_number = 1 
    for action in user_note:
        if action["action"] == "add" and action["target"] == "ent":
            for ent in action["content"]:
                if ent["para_id"] == para_id:
                    extra_number +=1
    
    return base_number + extra_number

def decide_new_ent_number_on_1_paragraph(entities):
    base_number = len(entities["entities"])
    extra_number = 1 
    return base_number + extra_number

def add_edit_status(array, field_name, id):
    added = False
    for ele in array[field_name]:
        if "id" in ele:
            if ele["id"] == id:
                if ele["status"] == "none":
                    ele["status"] = "confirmed"
                else:
                    ele["status"] = "none"
                added=True
    if added:
        return array
    else:
        array[field_name].append({
            "id":id,
            "status":"confirmed"
        })
        return array

def change_para_id(new_id, object_list):
    for object in object_list:
        return 1

def decide_new_pos(new_entity,char_positions):
    """
    Calculate the relative character positions in a paragraph based on the new entity's absolute positions.
    
    :param entity: CreateEntitySchema, the new entity with absolute positions.
    :param char_positions: List of character positions in the paragraph, where each character is represented by a Rect.
    :return: List of indices representing the relative character positions covered by the new entity.
    """
    print("original entity", new_entity)
    entity_rects = new_entity.position.rects
    print("original new entity rects", entity_rects)
    found_para_id = -1
    found_idx = []
    for para_id, char_list in enumerate(char_positions):
        relative_indices = []
        # Flatten character positions for easy comparison
        # if char_list[0]["pageNumber"] != entity_rects[0].pageNumber:
        #     continue
        flattened_char_positions = [(idx, Rect(**char)) for idx, char in enumerate(char_list)]

        
        # Assume the first character rect from the server as a reference for scaling
        if not flattened_char_positions:
            return []

        _, first_server_rect = flattened_char_positions[0]
        
        # Calculate scale factors based on width and height
        width_scale = first_server_rect.width / entity_rects[0].width
        height_scale = first_server_rect.height / entity_rects[0].height

        
        # Scale the entity's rects to match the server's coordinate system
        scaled_entity_rects = [
            Rect(
                x1=rect.x1 * width_scale,
                y1=rect.y1 * height_scale,
                x2=rect.x2 * width_scale,
                y2=rect.y2 * height_scale,
                width=first_server_rect.width,
                height=first_server_rect.height,
                pageNumber=rect.pageNumber
            )
            for rect in entity_rects
        ]

        # Compare each scaled entity rectangle with character positions
        for scaled_entity_rect in scaled_entity_rects:
            for idx, char_rect in flattened_char_positions:

                if check_character_inside_bounding_rect(scaled_entity_rect,char_rect):
                    # If scaled entity rect overlaps with character rect, add index to relative indices
                    relative_indices.append(idx)

        # Remove duplicates and sort the indices
        if relative_indices != []:
            found_para_id = para_id
            found_idx = sorted(list(set(relative_indices)))
    return found_para_id, found_idx

def check_character_inside_bounding_rect(scaled_entity_rect, char_rect):

    if scaled_entity_rect.pageNumber == char_rect.pageNumber:
        if (scaled_entity_rect.x1 - char_rect.x2 <= 0.05 and
        scaled_entity_rect.x2 - char_rect.x1 >= -0.05 and
        scaled_entity_rect.y1 <= char_rect.y2 and
        scaled_entity_rect.y2 >= char_rect.y1): 
            if abs(scaled_entity_rect.y1 - char_rect.y1) <3 and abs(scaled_entity_rect.y2 - char_rect.y2) <3:
                    #case character lie totally inside the bounding box
                    return True
    return False

def check_if_rel_is_filtered(rel,entities,entity_type_filters):
    match = False
    head_ent_id = rel[2][0][1]
    tail_ent_id = rel[2][1][1]
    head_type = (ent[1] for ent in entities if ent[0]== head_ent_id)
    tail_type = (ent[1] for ent in entities if ent[0]== tail_ent_id)
    for type in entity_type_filters:
        if type == head_type or type== tail_type:
            match = True
    return match


def filter_entities_by_relations( relations_obj, ent_filters, rel_filters):
    filtered_data = []

    for paragraph in relations_obj:
        tmp_obj = copy.deepcopy(paragraph)
        del tmp_obj["edit_status"]
        filtered_entities = []
        filtered_relations = []
        if "relations" not in paragraph:
            tmp_obj["entities"] = filtered_entities
            tmp_obj["relations"] = filtered_relations
            filtered_data.append(tmp_obj)
            continue
        # Filter relations based on rel_filters
        # for relation in paragraph["relations"]:
        #     if relation[1] in rel_filters:
        #         # print(relation)
        #         filtered_relations.append(relation)

        if "None" in rel_filters or "none" in rel_filters:
            exist_relation_entity_ids = {
                role[1]
                for relation in tmp_obj["relations"]
                for role in relation[2]
            }
        else:
            exist_relation_entity_ids = {
                entity[0] for entity in tmp_obj["entities"]
            }
        # Find relevant relations based on rel_filters
        relevant_relations = [
            relation for relation in tmp_obj["relations"] if relation[1] in rel_filters
        ]
        
        # Collect IDs of entities involved in relevant relations
        related_entity_ids = {
            role[1]
            for relation in relevant_relations
            for role in relation[2]
        }
        # print(related_entity_ids)
        # Filter entities based on ent_filters and their involvement in relevant relations
        
        filter_ent_id = []
        for entity in tmp_obj["entities"]:
            if entity[1] == ent_filters and entity[0] in related_entity_ids:
                filtered_entities.append(entity)
                filter_ent_id.append(entity[0])
            if entity[0] not in exist_relation_entity_ids:
                filtered_entities.append(entity)
        # Add paragraph with filtered entities if any entities remain
        # if filtered_entities:
        #     filtered_data.append({
        #         "text": paragraph["text"],
        #         "entities": filtered_entities
        #     })
        filtered_relations = []
        for relations in relevant_relations:
            satify_filter = False
            if relations[2][0][1] in filter_ent_id or relations[2][1][1] in filter_ent_id:
                satify_filter = True
            if satify_filter:
                filtered_relations.append(relations)

        tmp_obj["entities"] = filtered_entities
        tmp_obj["relations"] = filtered_relations
        filtered_data.append(tmp_obj)
    return filtered_data

def merge_ents(ent_list1, ent_list2):
    for ent in ent_list2:
        duplicated = False
        for ori_ent in ent_list1:
            if ent[0] == ori_ent[1]:
                duplicated= True
        if duplicated != True:
            ent_list1.append(ent)
    return ent_list1

def merge_filtered_entities(merge_container, filtered_entities):
    if merge_container == []:
        return filtered_entities
    else:
        # print(merge_container)
        for index, para in enumerate(merge_container):
            m_ents = para["entities"]
            f_ents = filtered_entities[index]["entities"]

            m_rels = para["relations"]
            f_rels = filtered_entities[index]["relations"]

            m_ents = merge_ents(m_ents,f_ents)
            m_rels = merge_ents(m_rels,f_rels)
            # print(m_ents)
            para["entities"] = m_ents
            para["relations"] = m_rels
        # print(filtered_entities)
        return merge_container


def filter_relations_by_entities(
    relations_obj,
    rel_filters,
    ents_filters
):
    filtered_data = []

    for paragraph in relations_obj:
        tmp_obj =  copy.deepcopy(paragraph)
        del tmp_obj["edit_status"]
        filtered_entities = []
        filtered_relations = []
        if "relations" not in tmp_obj:
            tmp_obj["entities"] = filtered_entities
            tmp_obj["relations"] = filtered_relations
            filtered_data.append(tmp_obj)
            continue
        # Collect IDs of entities that match the ents_filters
        filtered_entity_ids = {
            entity[0]
            for entity in tmp_obj["entities"]
            if entity[1] in ents_filters
        }
        related_entity_ids = []
        # Filter relations based on rel_filters and involvement of filtered entities
        for relation in tmp_obj["relations"]:
            if relation[1] == rel_filters:
                # Check if any entity in the relation roles is in the filtered_entity_ids
                if any(role[1] in filtered_entity_ids for role in relation[2]):
                    filtered_relations.append(relation)
                    related_entity_ids.append(relation[2][0][1])
                    related_entity_ids.append(relation[2][1][1])
        # Add paragraph with filtered relations if any relations remain
        # if filtered_relations:
        #     filtered_data.append({
        #         "text": paragraph["text"],
        #         "relations": filtered_relations
        #     })
        for entity in tmp_obj["entities"]:
            if entity[0] in filtered_entity_ids and entity[0] in related_entity_ids:
                filtered_entities.append(entity)

        tmp_obj["entities"] = filtered_entities
        tmp_obj["relations"] = filtered_relations
        filtered_data.append(tmp_obj)

    return filtered_data

def filter_entities(relations_obj, filtering_entity_types):
    
    ent_result = []
    if len(filtering_entity_types)==0:
        filtered_data = []
        for para in relations_obj:
            tmp_obj = copy.deepcopy(para)
            del tmp_obj["edit_status"]
            tmp_obj["entities"] = []
            tmp_obj["relations"] = []
            filtered_data.append(tmp_obj)
        return filtered_data

    for entity_type in filtering_entity_types:
        filtered_ent = filter_entities_by_relations(relations_obj,entity_type.type,entity_type.sub_type)
        # print(filtered_ent)
        ent_result = merge_filtered_entities(ent_result, filtered_ent)
        
    return ent_result

def filter_relations(relations_obj, filtering_relation_types):
    
    rel_result = []
    if len(filtering_relation_types)==0:
        rel_result = []
        for para in relations_obj:
            tmp_obj = copy.deepcopy(para)
            # del tmp_obj["edit_status"]
            tmp_obj["entities"] = []
            tmp_obj["relations"] = []
            rel_result.append(tmp_obj)
        return rel_result
    for relation_type in filtering_relation_types:
        filtered_rel = filter_relations_by_entities(relations_obj,relation_type.type,relation_type.sub_type)
        rel_result = merge_filtered_entities(rel_result, filtered_rel)

    return rel_result

def filter_non_para(para, bbox):
    return para, bbox


def compose_password_reset_email(reset_link: str, recipient_email: str, username: str) -> dict:
    """
    Compose a subject and body for the password-reset email.
    Returns a dictionary with 'subject' and 'body_text' (and optionally 'body_html').
    """
    
    subject = "[Polyminder] Reset your password"
    
    body_text = f"""\
        Hello,

        We received a request to reset the password for your account ({recipient_email}). 
        If you did not request a password reset, please ignore this email.

        To reset your password, please click the link below (or copy and paste it into your browser):
        {reset_link}

        This link will expire in 30 minutes.

        Best regards,
        Your Company Name
        """

            # (Optional) HTML version of the email
    body_html = f"""\
        <html>
        <body>
            <p>Hello,</p>
            <p>We received a request to reset the password for your account {username} ({recipient_email}). 
            If you did not request a password reset, please ignore this email.</p>
            <p>To reset your password, please click 
            <a href="{reset_link}">here</a> 
            (or copy and paste the URL below into your browser):</p>
            <p>{reset_link}</p>
            <p>This link will expire in 30 minutes.</p>
            <p>Best regards,<br>[Polyminder]</p>
        </body>
        </html>
        """

    return {
        "subject": subject,
        "body_text": body_text,
        "body_html": body_html
    }

def compose_question_reminder_email(user_name: str, user_email: str, questions: str) -> dict:
    """
    Compose an email to remind the server admin that a user has questions for them.

    :param admin_email: The email address of the server admin.
    :param user_name: The name/username of the user who has questions.
    :param user_email: The email address of the user who has questions.
    :param questions: The user's questions or message.
    :return: A dictionary with 'subject', 'body_text', and 'body_html'.
    """

    subject = "[Polyminder] User questions pending"

    body_text = f"""\
        Hello,

        This is a reminder that user "{user_name}" ({user_email}) has questions for you:

        {questions}

        Please reach out to them at your earliest convenience.

        Best regards,
        Polyminder Team
        """

            # Optional HTML version
    body_html = f"""\
        <html>
        <body>
            <p>Hello,</p>
            <p>This is a reminder that user <strong>{user_name}</strong> 
            (<a href="mailto:{user_email}">{user_email}</a>) has questions for you:</p>
            <blockquote>
            {questions}
            </blockquote>
            <p>Please respond as soon as possible.</p>
            <p>Best regards,<br>Polyminder Team</p>
        </body>
        </html>
    """

    return {
        "subject": subject,
        "body_text": body_text,
        "body_html": body_html
    }


def send_reset_password_email(to_email,reset_link, username ):
    # Set up the SMTP server
    smtp_host = 'smtp.gmail.com'  # Replace with your SMTP server
    smtp_port = 587  # Port for TLS
    from_email = 'polyminder.no.reply@gmail.com'  # Replace with your email
    password = gmail_app_password  # Replace with your email password
    email_title ="[Polyminder] Document Processing Notification"
    # Create the email message
    mail_obj = compose_password_reset_email(reset_link, to_email, username)
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = mail_obj['subject']
    
    msg.attach(MIMEText(mail_obj['body_html'], 'html'))
    result = False
    # Connect to the SMTP server
    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()  # Use TLS for security
        server.login(from_email, password)  # Login with your email and password

        # Send the email
        server.sendmail(from_email, to_email, msg.as_string())
        print("Email sent successfully!")
        result = True
    except Exception as e:
        print(f"Failed to send email. Error: {str(e)}")
        result = False
    finally:
        server.quit()
    
    return result

def send_contact_support_email(user_email,name, content ):
    # Set up the SMTP server
    smtp_host = 'smtp.gmail.com'  # Replace with your SMTP server
    smtp_port = 587  # Port for TLS
    from_email = 'polyminder.no.reply@gmail.com'  # Replace with your email
    to_emails = [
        'trieuhoangan1012@gmail.com',
        'truongdo619@gmail.com'
        ]
    password = gmail_app_password  # Replace with your email password

    # Create the email message
    for to_email in to_emails:
        mail_obj = compose_question_reminder_email(name, user_email, content)
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = mail_obj['subject']
        
        msg.attach(MIMEText(mail_obj['body_html'], 'html'))
        result = False
        # Connect to the SMTP server
        try:
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()  # Use TLS for security
            server.login(from_email, password)  # Login with your email and password
            # Send the email
            server.sendmail(from_email, to_email, msg.as_string())
            print("Email sent successfully!")
            result = True
        except Exception as e:
            print(f"Failed to send email. Error: {str(e)}")
            result = False
        finally:
            server.quit()
    
    return result


def decide_log_file():
    current_date = datetime.now()
    filename=f"{current_date.day}_{current_date.month}_{current_date.year}.txt"
    return filename

def logging(folder_path, content):
    path = os.path.join(folder_path,decide_log_file())
    with open(path, 'a', encoding='utf-8') as f:
        f.write(content)
        f.write("\n")

def h_log(folder_path):
    path = os.path.join(folder_path,decide_log_file())
    with open(path, 'a', encoding='utf-8') as f:
        f.write("=="*1000)
        f.write("\n")

def log_position(folder_path, position):
    
    state = {
        "position":{
            "rects":[

            ],
            "boundingRect":{
                "x1": position.boundingRect.x1,
                "y1": position.boundingRect.y1,
                "x2": position.boundingRect.x2,
                "y2": position.boundingRect.y2,
                "width": position.boundingRect.width,
                "height": position.boundingRect.height,
                "pageNumber": position.boundingRect.pageNumber,
            }
        }
    }
    for rect in position.rects:
        state["position"]["rects"].append(
            {
                "x1": rect.x1,
                "y1": rect.y1,
                "x2": rect.x2,
                "y2": rect.y2,
                "width": rect.width,
                "height": rect.height,
                "pageNumber": rect.pageNumber,
            }
        )
    logging(folder_path,json.dumps(state))

def log_relation(folder_path, relations):
    state = {
        "relations":[

        ]
    }
    for relation in relations:
        state["relations"].append({
            "type": relation.type,
            "arg_type": relation.arg_type,
            "arg_id": relation.arg_id,
            "arg_text": relation.arg_text,
            "id": relation.id,
        })
    logging(folder_path,json.dumps(state))

def get_bbox_n_text_seperated(para_data):
    block_texts_data = []
    block_bb_data = []
    for para in para_data:
        block_texts_data.append(para["text"])
        block_bb_data.append(para["bbox"])
    return block_texts_data, block_bb_data


def generate_graphs(entities, relations):
    from collections import defaultdict

    # Map entity ID to entity details
    entity_map = {e[0]: e for e in entities}

    # Build reverse and forward lookup of relations for each entity
    parents_map = defaultdict(list)
    children_map = defaultdict(list)
    for rel in relations:
        rel_id, rel_type, args = rel
        src = args[0][1]
        tgt = args[1][1]
        children_map[src].append((tgt, rel_type))
        parents_map[tgt].append((src, rel_type))

    # Set to track all entities we need to include in the graph
    all_graphs = {}

    # Function to collect all entities related to a given entity
    def collect_all_related_entities(entity_id, visited_entities):
        # Add current entity to visited set
        visited_entities.add(entity_id)
        # Collect parents and children
        for parent_id, _ in parents_map[entity_id]:
            if parent_id not in visited_entities:
                collect_all_related_entities(parent_id, visited_entities)
        for child_id, _ in children_map[entity_id]:
            if child_id not in visited_entities:
                collect_all_related_entities(child_id, visited_entities)

    for root_id in entity_map.keys():
        # Initialize visited set to avoid duplicates
        visited_entities = set()
        # Collect all related entities for the current root
        collect_all_related_entities(root_id, visited_entities)

        nodes = []
        edges = []

        id_map = {}  # maps entity ID to node ID in the graph
        node_positions = {}  # entity ID -> (x, y)
        node_counter = 1

        # Function to add nodes
        def add_node(entity_id, x, y):
            nonlocal node_counter
            if entity_id in id_map:
                return id_map[entity_id]
            ent = entity_map[entity_id]
            node_id = str(node_counter)
            node_counter += 1
            id_map[entity_id] = node_id
            node_positions[entity_id] = (x, y)
            nodes.append({
                "id": node_id,
                "type": "myCustomNode",
                "data": {"label": f"{ent[1]}: {ent[3]}"},
                "position": {"x": x, "y": y},
                "className": ent[1]
            })
            return node_id

        # Root node at (800, 800)
        root_node_id = add_node(root_id, 800, 800)

        # Define the offset for positioning nodes around the root
        horizontal_offset = 400  # The horizontal distance between root and its immediate children
        vertical_offset = 150    # The vertical distance between nodes

        # Add relations for all parent nodes that are part of the visited entities
        for parent_id in visited_entities:
            for i, (parent_rel, rel_type) in enumerate(parents_map[parent_id]):
                if parent_id in visited_entities:
                    parent_y = 800 + (i + 1) * vertical_offset  # position parent below root
                    parent_node_id = add_node(parent_id, 800 - horizontal_offset, parent_y)
                    edges.append({
                        "id": f"e{parent_node_id}-{root_node_id}-left",
                        "source": parent_node_id,
                        "sourceHandle": "source-right",
                        "target": root_node_id,
                        "targetHandle": "target-left",
                        "type": "floating",
                        "label": rel_type
                    })

        # Add relations for all child nodes that are part of the visited entities
        child_ids = set()
        for i, (child_id, rel_type) in enumerate(children_map[root_id]):
            if child_id in visited_entities:
                child_ids.add(child_id)
                child_y = 800 + (i + 1) * vertical_offset  # position child below root
                child_node_id = add_node(child_id, 800 + horizontal_offset, child_y)
                edges.append({
                    "id": f"e{root_node_id}-{child_node_id}-right",
                    "source": root_node_id,
                    "sourceHandle": "source-right",
                    "target": child_node_id,
                    "targetHandle": "target-left",
                    "type": "floating",
                    "label": rel_type
                })

        # Adjust the position of subnodes (child and their descendants)
        def position_subnodes(entity_id, x_offset, y_offset):
            """ Recursive function to adjust the position of subnodes for visualization """
            nonlocal node_counter
            children = children_map.get(entity_id, [])
            for i, (child_id, _) in enumerate(children):
                if child_id in visited_entities:
                    # If directly connected to root, set x_offset to 400
                    if entity_id == root_id:
                        child_x = 800 + horizontal_offset
                    else:
                        # Otherwise, set x_offset to 200
                        child_x = x_offset + 200

                    # Distribute child nodes along y-axis
                    child_y = y_offset + (i + 1) * vertical_offset
                    child_node_id = add_node(child_id, child_x, child_y)

                    # Create edge between parent and child
                    edges.append({
                        "id": f"e{entity_id}-{child_node_id}-subnode",
                        "source": entity_id,
                        "sourceHandle": "source-right",
                        "target": child_node_id,
                        "targetHandle": "target-left",
                        "type": "floating",
                        "label": "subnode"
                    })
                    # Recursively position descendants
                    position_subnodes(child_id, child_x, child_y)

        # Recursively position child nodes and subnodes
        for child_id in child_ids:
            position_subnodes(child_id, 800 + horizontal_offset, 800)

        all_graphs[root_id] = {
            "nodes": nodes,
            "edges": edges
        }

    return all_graphs

def find_id_pos(nodes,id):
    for index, node in enumerate(nodes):
        if node["ent_id"] == id:
            return index
    return -1


def generate_graphs_manual(entities, relations):
    from collections import defaultdict

    # ----------------------------
    # 1. Background color mapping
    # ----------------------------
    color_map = {
        "POLYMER": "#ff4500",
        "PROP_NAME": "#1e90ff",
        "CHAR_METHOD": "rgb(160, 119, 138)",
        "POLYMER_FAMILY": "#00ff00",
        "PROP_VALUE": "#ffd700",
        "MONOMER": "#B8BDD3",
        "OTHER_MATERIAL": "#1976d2",
        "COMPOSITE": "#8400ff",
        "SYN_METHOD": "#f09bc5",
        "EVENT": "#32CD32",
        "CONDITION": "#ffe000",
        "MATERIAL_AMOUNT": "#a0522d",
        "REF_EXP": "#bd0ea5",
        "INORGANIC": "#00ffff",
        "ORGANIC": "#ff00ff"
    }

    # ----------------------------
    # 2. Entity map for easy lookup
    # ----------------------------
    entity_map = {e[0]: e for e in entities}

    # Relationship mappings
    parents_map = defaultdict(list)
    children_map = defaultdict(list)

    for rel in relations:
        rel_id, rel_type, args = rel
        src = args[0][1]  # source node ID
        tgt = args[1][1]  # target node ID
        children_map[src].append((tgt, rel_type))
        parents_map[tgt].append((src, rel_type))

    # ----------------------------------------------------------------
    # Helper: safely add (source_id, direction, edge_label)
    #         under adjacency[target_id] without duplicates
    # ----------------------------------------------------------------
    def add_node(node_id, connected_id, direction_of_connection, connect_type, adjacency):
        """Store (node_id, direction_of_connection, connect_type) in adjacency[connected_id], if not already present."""
        if node_id == connected_id:
            return adjacency
        if connected_id not in adjacency:
            adjacency[connected_id] = []

        triple = (node_id, direction_of_connection, connect_type)
        if triple not in adjacency[connected_id]:
            adjacency[connected_id].append(triple)

        return adjacency

    # ----------------------------
    # 3. Shared options structure
    # ----------------------------
    shared_options = {
        "layout": { "improvedLayout": True },
        "physics": {
            "enabled": True,
            "solver": "forceAtlas2Based",
            "forceAtlas2Based": {
                "gravitationalConstant": -50,
                "centralGravity": 0.005,
                "springLength": 140,
                "springConstant": 0.08,
                "damping": 0.4,
                "avoidOverlap": 1,
            },
            "stabilization": { "iterations": 200 },
        },
        "interaction": {
            "hover": True,
            "zoomView": True,
            "dragView": True,
            "dragNodes": True,
        },
        "nodes": {
            "shape": "box",
            "borderRadius": 6,
            "font": { "face": "Roboto", "size": 14 },
            "color": {
                "border": "#2B7CE9",
                "background": "#97C2FC",
                "highlight": { "border": "#2B7CE9", "background": "#D2E5FF" },
                "hover": { "border": "#2B7CE9", "background": "#D2E5FF" },
            },
        },
        "edges": {
            "arrows": { "to": { "enabled": True, "scaleFactor": 0.7 } },
            "smooth": { "type": "cubicBezier", "roundness": 0.4 },
            "color": { "color": "#848484", "highlight": "#343434", "hover": "#343434" },
            "font": { "align": "middle" },
        }
    }

    # Dictionary of graphs keyed by root_id
    all_graphs = {}

    # -------------------------------------------
    # 4. Build a graph for each 'root' entity
    # -------------------------------------------
    for root_id in entity_map:
        adjacency = {}
        waiting_list = [(root_id, root_id, "r", "")]  # (node_id, connected_id, direction, edge_label)
        traversed_list = []

        # BFS-like build of adjacency
        while waiting_list:
            node_id, connected_id, direction, rel_label = waiting_list.pop(0)

            # Build adjacency
            adjacency = add_node(node_id, connected_id, direction, rel_label, adjacency)

            # Expand to parents
            if node_id in parents_map:
                for (p_id, p_rel) in parents_map[node_id]:
                    if p_id not in traversed_list:
                        waiting_list.append((p_id, node_id, "p", p_rel))

            # Expand to children
            if node_id in children_map:
                for (c_id, c_rel) in children_map[node_id]:
                    if c_id not in traversed_list:
                        waiting_list.append((c_id, node_id, "c", c_rel))

            # Mark visited
            traversed_list.append(node_id)
        traversed_list = list(set(traversed_list))
        
        # Build the node list (only root gets x=0,y=0)
        nodes_list = []
        for node_id in traversed_list:
            ent = entity_map[node_id]
            entity_type = ent[1]
            label_text = f"{entity_type}: {ent[-1]}"
            bg_color = color_map.get(entity_type, "#ffffff")

            node_data = {
                "id": node_id,
                "label": label_text,
                "shape": "box",
                "color": {
                    "background": bg_color,
                    "border": bg_color
                },
                "font": {
                    "size": 18,
                    "bold": True
                }
            }

            # Only root node at position (0,0)
            if node_id == root_id:
                node_data["x"] = 0
                node_data["y"] = 0

            nodes_list.append(node_data)

        # Build the edge list ( normal direction: source -> target )
        # adjacency = { target_id: [(source_id, direction, edge_label), ...], ... }
        # So final edge is from source_id --> target_id
        edges_list = []
        for node_id, conn_list in adjacency.items():
            for (branch_id, connection_direction, edge_label) in conn_list:

                if connection_direction=='c':
                    source_id = node_id
                    target_id = branch_id
                elif connection_direction=='p':
                    source_id = branch_id
                    target_id = node_id
                edges_list.append({
                    "from": source_id,
                    "to": target_id,
                    "label": edge_label,
                    "arrows": "to"
                })
        if root_id=="T5":
            print(traversed_list)
            print(adjacency)
        # Add 'options' to each graph
        all_graphs[root_id] = {
            "nodes": nodes_list,
            "edges": edges_list,
            "options": shared_options
        }

    return all_graphs



def apply_visibility_to_result(result, visible_list):
    # Step 1: Add 'visible' to brat_format_output based on visible_list
    

    # brat_outputs = result.get("brat_format_output", [])
    # pdf_outputs = result.get("pdf_format_output", [])
    brat_outputs = result['brat_format_output']
    pdf_outputs = result['pdf_format_output']
    # print(pdf_outputs)
    if visible_list==[]:
        visible_list = [True for i in range(len(brat_outputs))]
    id_to_visibility = {}  # Maps entity IDs (e.g., T1, T2, ...) to their visibility

    for idx, brat_item in enumerate(brat_outputs):
        is_visible = visible_list[idx] if idx < len(visible_list) else False
        brat_item["visible"] = is_visible
        for entity in brat_item.get("entities", []):
            entity_id = entity[0]  # e.g., "T1"
            entity_id = f"para{idx}_{entity_id}"
            id_to_visibility[entity_id] = is_visible

    # Step 2: Add 'visible' to pdf_format_output based on ID match
    for pdf_item in pdf_outputs:
        entity_id = pdf_item.get("id", "")  # e.g., "para0_T1"
        # entity_id_parts = entity_id.split("_")
        # short_id = entity_id_parts[-1] if len(entity_id_parts) > 1 else entity_id  # extract "T1" from "para0_T1"
        pdf_item["visible"] = id_to_visibility.get(entity_id, False)
    # result['brat_format_output'] = brat_outputs 
    # result['pdf_format_output'] = pdf_outputs
    return result

def collect_visible_list(user_notes):
    v_list  = []
    for note in user_notes:
        if note["target"]=="visible":
            v_list = note["content"]['visible_list']
    return v_list

def filter_with_visible_list(object_list, visible_list):
    result = []
    if visible_list==[]:
        return object_list
    print(visible_list)
    
    for index, state in enumerate(visible_list):
        if state:
            result.append(object_list[index])
    return result

def compose_position_object_from_Position(position):
    rects = []
    
    for rect in position.rects:
        rects.append({
                "x1": rect.x1,
                "y1": rect.y1,
                "x2": rect.x2,
                "y2": rect.y2,
                "width": rect.width,
                "height": rect.height,
                "pageNumber": rect.pageNumber
        })
    boundingRect = {
        "x1": position.boundingRect.x1,
        "y1": position.boundingRect.y1,
        "x2": position.boundingRect.x2,
        "y2": position.boundingRect.y2,
        "width": position.boundingRect.width,
        "height": position.boundingRect.height,
        "pageNumber": position.boundingRect.pageNumber
    }
    position_object = {
        "rects": rects,
        "boundingRect": boundingRect
    }
    return position_object

def load_graph_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def parse_id(combined_id):

    match = re.match(r"^para(\d+)_(\S+)$", combined_id)
    para_id = int(match.group(1))
    entity_id = match.group(2)
    return para_id, entity_id

def cast_dict_to_rect(rect_dict):
    x1 = rect_dict.get("x1",0)
    x2 = rect_dict.get("x2",0)
    y1 = rect_dict.get("y1",0)
    y2 = rect_dict.get("y2",0)
    rect = pymupdf.Rect(x1,y1,x2,y2)
    # rect = Rect(x1,y1,x2,y2)
    return rect

def hex_to_rgb(hex_color):
    """Convert hex color to RGB."""
    # Remove the '#' if it exists
    hex_color = hex_color.lstrip('#')
    
    # Convert the hex string to RGB using int with base 16
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    
    return r, g, b
def rgb_to_color_format(r, g, b):
    """Convert RGB values to the format described in the documentation."""
    stroke_color = [r / 255.0, g / 255.0, b / 255.0]
    return stroke_color

def get_color_for_entity_type(entity_type):
    r, g, b = hex_to_rgb(color_map.get(entity_type,"#ffffff"))
    stroke_color = rgb_to_color_format(r, g, b)
    return stroke_color, stroke_color

def check_long_boudingrect(rect):
    return abs(rect.get("x2",0)-rect.get("x1",0)) < 10

def compose_relation(relations):
    simplied_rel = ["{} \n \t {} : {}".format(rel.get("type"),rel.get("arg_type"),rel.get("arg_text")) for rel in relations]
    return "\n".join(simplied_rel)

def create_highlighted_pdf_file(file_path,output,output_filepath):
    pdf_format_output = output.get("pdf_format_output",[])
    doc = pymupdf.open(file_path)
    
    for annotator in pdf_format_output:
        # para_id, entity_id = parse_id(annotator.get("id",""))
        entity_id = annotator.get("id","")

        rects_list = annotator.get("position",{}).get("rects",[])
        entity_type= annotator.get("comment")
        content = annotator.get("content",{}).get("text","")
        relations = compose_relation(annotator.get("relations",[]))
        boundingRect = annotator.get("position",{}).get("boundingRect")
        breakable = False
        for rect in rects_list:
            if len(rects_list) >= 5 and check_long_boudingrect(boundingRect):
                rect = boundingRect
                breakable = True
            stroke_color, fill_color = get_color_for_entity_type(entity_type)
            pageNumber = rect.get("pageNumber",1) - 1
            page = doc[pageNumber]
            highlight = page.add_rect_annot(cast_dict_to_rect(rect))
            
            highlight.set_info(info={"content": f"Entity {entity_id}\nContent: '{content}' \nType: {entity_type} \n\n {relations}" })
            highlight.set_colors(stroke=stroke_color, fill=fill_color)
            highlight.set_opacity(0.6)
            highlight.update()
            if breakable:
                break
    
    doc.save(output_filepath)
    doc.close()

def init_comment_for_entity(entities_wrapper):
    for para in entities_wrapper:
        for ent in para.get("entities",[]):
            if len(ent)<5:
                ent.append("")
                ent[-1],ent[-2] = ent[-2],ent[-1]
    return entities_wrapper

def convert_entity_from_list_to_dict(entity):
    '''
        original entity format:
            [
                id,
                entity type,
                [
                    [
                        head,
                        tail
                    ]
                ],
                comment (optional),
                entity text
            ]

        new format:
            {
            "id",
            "entity_type",
            "head",
            "tail",
            "comment",
            "entity_text"
            }

    '''
    return {
        "entity_id":entity[0],
        "entity_type":entity[1],
        "head":entity[2][0][0],
        "tail":entity[2][0][1],
        "comment":entity[-2] if len(entity) > 4 else "",
        "entity_text":entity[-1]
    }

def convert_entity_from_dict_to_list(entity):
    '''
        original entity format:
            {
            "id",
            "entity_type",
            "head",
            "tail",
            "comment",
            "entity_text"
            }

        new format:
            [
                id,
                entity type,
                [
                    [
                        head,
                        tail
                    ]
                ],
                comment (optional),
                entity text
            ]

    '''
    return [
        entity.get("entity_id"),
        entity.get("entity_type"),
        [
            [
                entity.get("head"),
                entity.get("tail")
            ]
        ],
        entity.get("comment"),
        entity.get("entity_text")
    ]
    
def get_cur_relations_entities(document,update,user_notes):
    """
    This function is used to get the current entities and relations of the document.
    Input:
        document: Document
        update: Update
        user_notes: list
    Output:
        cur_entities: list
        cur_relations: list
    """
    cur_entities = update.get_entities()
    if cur_entities ==[]:
        cur_entities = document.get_entities()
        cur_entities = execute_user_note_on_entities(user_notes,cur_entities)
    
    cur_relations = update.get_relations()
    if cur_relations == []:
        cur_relations = document.get_relations()
        cur_relations = execute_user_note_on_relations(user_notes,cur_relations)
    return cur_entities, cur_relations

def compose_update_event_content(update_schema,old_event):
    """
    This function is used to compose the event update content for the user note.
    """
    
    para_id = update_schema.para_id

    object_for_user_note = {
        "para_id":para_id,
        "event_id":update_schema.event.event_id,
        "new_trigger_id": update_schema.event.trigger_id,
        "new_arguments": json.dumps(update_schema.event.arguments),

        "old_trigger_id": old_event[1],
        "old_arguments": json.dumps(old_event[2])
    }
        
    
    return object_for_user_note

def convert_output_to_full_pdf_creating(output, original_wrapper):
    """
    This function is used to insert the blank paragraphs to the filtered relations and entities.
    """
    if len(output)==len(original_wrapper):
        return output

    new_output = []
    for para in original_wrapper:
        keep_text_only=True
        for output_para in output:
            if para["text"]==output_para["text"]:
                new_output.append(copy.deepcopy(output_para))
                keep_text_only=False
        if keep_text_only:
            new_para = copy.deepcopy(para)
            new_para["entities"]=[]
            new_para["relations"]=[]
            new_para["events_info"]={
                "events":[],
                "entities":[],
                "triggers":[]
            }
            new_output.append(new_para)
    return new_output

def serialize(value):
    if isinstance(value, datetime):
        return value.strftime("%Y/%m/%d, %H:%M:%S")
    return value

def build_prompt(data_point,base_prompt):
    # prompt = f"""Please convert the following HTML table into a detailed natural language paragraph. Use the additional context provided to enrich and clarify the description. Present the information row by row, clearly articulating the content of each cell within each row so that named entity recognition (NER) models can easily identify and extract all individual data points. Ensure that the resulting text distinctly expresses the data from every column for each row, maintaining a structure that preserves the granularity and traceability of the original table.\n\n"""
    prompt = f"""{base_prompt}\n\n"""
    if data_point.get("context"):
        prompt += "Surrounding text:\n"
        # for context in data_point["context"]:
        #     prompt += f"{context.strip()}\n"
        prompt += data_point["context"].strip()+"\n"
        prompt += "\n"
        
    if data_point.get("table_caption"):
        prompt += "Caption:\n"
        # for caption in data_point["table_caption"]:
        prompt += data_point["table_caption"].strip()+"\n"
        prompt += "\n"
        
    if data_point.get("table_footnote"):
        prompt += "Table footnote:\n"
        # for footnote in data_point["table_footnote"]:
        #     prompt += f"{footnote.strip()}\n"
        prompt += data_point["table_footnote"].strip()+"\n"
        prompt += "\n"
        
    prompt += f'HTML table:\n{data_point["table_body"].strip()}\n'
    data_point["prompt"]=prompt
    return data_point

def load_settings_from_domain():
    settings = []
    domain_path="annotators"
    for domain_dir in os.listdir(domain_path):
        if domain_dir=="base_annotator" or os.path.isdir(os.path.join(domain_path,domain_dir))==False:
            continue
        else:

            domain_child_dirs = os.listdir(os.path.join(domain_path,domain_dir))
            for d_c_dir in domain_child_dirs:
                if os.path.isdir(os.path.join(domain_path,domain_dir,d_c_dir))==False:
                    continue
                if d_c_dir =="resources" and os.path.exists(os.path.join(domain_path,domain_dir,d_c_dir,"setting.json")):
                    print(os.path.join(domain_path,domain_dir,d_c_dir,"setting.json"))
                    with open(os.path.join(domain_path,domain_dir,d_c_dir,"setting.json"), 'r',encoding="utf-8") as f:
                        setting = json.load(f)
                    settings.append(setting)
    return settings


def serialize(value):
    if isinstance(value, datetime):
        return value.strftime("%Y/%m/%d, %H:%M:%S")
    return value

def convert_statistic_info(statistic_info):
    """
    Convert datetime objects in the dictionary to ISO 8601 strings.
    """
    return {key: serialize(value) for key, value in statistic_info.items()}
