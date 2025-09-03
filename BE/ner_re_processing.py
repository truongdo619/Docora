import json
from config import DEBUG, nlp
from utils import utils
def convert_to_NER_model_input_format(paragraphs):
    json_list = []
    counters = []
    for idx, paragraph_text in enumerate(paragraphs):
        output = nlp.annotate(paragraph_text, properties={
            'annotators': 'tokenize',
            'outputFormat': 'json'
        })
        if DEBUG:
            print(output)
        
        if type(output) == str:
            output = json.loads(output)
        
        sent_id = 0
        
        for sentence in output['sentences']:
            sent_id += 1
            json_item = {}
            json_item_tokens = []
            text = []
            for token in sentence['tokens']:
                text.append(token['word'])

            json_item_tokens = text

            json_item['sentence'] = json_item_tokens
            json_item['ner'] = []
            json_item['doc_ID'] = idx + 1
            json_item['sent_ID'] = sent_id

            json_list.append(json_item)
    # print("000"*50)
    # print(len(paragraphs))
    # print("000"*50)
    # print(len(json_list))
    # print("000"*50)
    return json_list


def convert_to_RE_model_input_format(ner_output_paragraphs):
    count_multi_span = 0
    json_list = []
    for idx, paragraph in enumerate(ner_output_paragraphs):
        entities = []
        for entity in paragraph["entities"]:
            entity_id, entity_type, entity_loc, entity_text = entity[0], entity[1], entity[2], entity[3]
            ent = {}
            ent['standoff_id'] = int(entity_id[1:])
            if len(entity_loc) > 1:
                count_multi_span += 1
            else:
                ent['entity_type'] = entity_type
                ent['offset_start'] = int(entity_loc[0][0])
                ent['offset_end'] = int(entity_loc[0][1])
                ent['word'] = entity_text
                entities.append(ent)

        output = nlp.annotate(paragraph["text"], properties={
            'annotators': 'tokenize',
            'outputFormat': 'json'
        })
        
        if type(output) == str:
            output = json.loads(output)
    
        json_item = {}
        json_item_sents = []
        json_item_vertexSet = {}

        sent_id = -1
        for sentence in output['sentences']:
            sent_id += 1
            json_item_tokens = []
            text = []
            for token in sentence['tokens']:
                text.append(token['word'])
            json_item_tokens = text

            for entity in entities:
                if entity['entity_type'] == 'Material-Property':
                    continue
                start = -1
                end = -1
                token_idx = 0
                for token in sentence['tokens']:
                    offset_start = int(token['characterOffsetBegin'])
                    offset_end = int(token['characterOffsetEnd'])

                    if offset_start == entity['offset_start']:
                        start = token_idx
                    if offset_end == entity['offset_end']:
                        end = token_idx + 1
                    token_idx += 1
                    if start != -1 and end != -1:
                        separated_tokens = []
                        for i in range(start, end):
                            separated_tokens.append(sentence['tokens'][i]['word'])

                        if (' '.join(separated_tokens) + '\t' + entity['entity_type']) not in json_item_vertexSet:
                            json_item_vertexSet[' '.join(separated_tokens) + '\t' + entity['entity_type']] = [{'name': ' '.join(separated_tokens), 'sent_id': sent_id, 'pos': [start, end], 'type': entity['entity_type'], 'brat_entity_mention_id': entity['standoff_id']}]
                        else:
                            json_item_vertexSet[' '.join(separated_tokens) + '\t' + entity['entity_type']] = json_item_vertexSet.get(' '.join(separated_tokens) + '\t' + entity['entity_type']) + [{'name': ' '.join(separated_tokens), 'sent_id': sent_id, 'pos': [start, end], 'type': entity['entity_type'], 'brat_entity_mention_id': entity['standoff_id']}]
                        break
            json_item_sents.append(json_item_tokens)
        
        json_item['title'] = str(idx)
        json_item['sents'] = json_item_sents

        vertexSet = list(json_item_vertexSet.values())
        json_item['vertexSet'] = vertexSet
        json_item['labels'] = []

        if len(json_item['vertexSet']) >= 2:
            json_list.append(json_item)

    return json_list


# def build_character_mapping(model_output_text, original_text, debug = False):
#     import difflib

#     # Convert original_text to a string if it's a list of characters
#     if isinstance(original_text, list):
#         original_text = ''.join(original_text)
    
#     s = difflib.SequenceMatcher(None, original_text, model_output_text)
#     # s = difflib.SequenceMatcher(None, model_output_text, original_text)
#     mapping_dict = {}
#     o_idx = -1  # Initialize to -1 to handle insertions at the beginning

#     for tag, i1, i2, j1, j2 in s.get_opcodes():
#         print("tag, i1, i2, j1, j2: {} , {} , {} , {} , {}".format(tag, i1, i2, j1, j2))
#         if tag == 'equal':
#             # Map matching characters directly
#             for o_pos, m_pos in zip(range(i1, i2), range(j1, j2)):
#                 mapping_dict[m_pos] = o_pos
#                 o_idx = o_pos  # Update the last matched index
#         elif tag == 'replace':
#             # Map replaced characters to their counterparts
#             for o_pos, m_pos in zip(range(i1, i2), range(j1, j2)):
#                 mapping_dict[m_pos] = o_pos
#                 o_idx = o_pos
#             # If lengths differ, map remaining model_output_text indices
#             len_o = i2 - i1
#             len_m = j2 - j1
#             if len_m > len_o:
#                 # More characters in model_output_text
#                 for m_pos in range(j1 + len_o, j2):
#                     mapping_dict[m_pos] = o_idx
#         elif tag == 'insert':
#             # Map inserted characters to the last matched index
#             for m_pos in range(j1, j2):
#                 mapping_dict[m_pos] = o_idx
#         elif tag == 'delete':
#             # Deleted characters in original_text; advance o_idx
#             o_idx = i2 - 1

#     # Ensure that mapping_dict has keys for all indices in model_output_text
#     num_model_chars = len(model_output_text)
#     for idx in range(num_model_chars):
#         if idx not in mapping_dict:
#             mapping_dict[idx] = o_idx  # Map missing indices to the last known o_idx
#     if debug:
#         print("mapping dict ", mapping_dict)
#         print("model output text :",model_output_text)
#         print("len of model_output_text :", len(model_output_text))
#         print("original_text :",original_text)
#         print("len of original_text :",len(original_text))
        
#     return mapping_dict

def build_character_mapping(model_output_text, original_text, debug=False):
    import difflib

    if isinstance(original_text, list):
        original_text = ''.join(original_text)

    s = difflib.SequenceMatcher(None, model_output_text, original_text)
    mapping_dict = {}
    o_idx = -1  # last known index in original_text

    for tag, i1, i2, j1, j2 in s.get_opcodes():
        if debug:
            print(f"tag: {tag}, i1: {i1}, i2: {i2}, j1: {j1}, j2: {j2}")
        if tag == 'equal':
            for m_pos, o_pos in zip(range(i1, i2), range(j1, j2)):
                mapping_dict[m_pos] = o_pos
                o_idx = o_pos
        elif tag == 'replace':
            for m_pos, o_pos in zip(range(i1, i2), range(j1, j2)):
                mapping_dict[m_pos] = o_pos
                o_idx = o_pos
            len_m = i2 - i1
            len_o = j2 - j1
            if len_m > len_o:
                for m_pos in range(i1 + len_o, i2):
                    mapping_dict[m_pos] = o_idx
        elif tag == 'insert':
            # Inserted characters in original_text: no change to model_output
            pass  # No m_pos to map
        elif tag == 'delete':
            for m_pos in range(i1, i2):
                mapping_dict[m_pos] = o_idx

    # Ensure all model_output_text indices are mapped
    for idx in range(len(model_output_text)):
        if idx not in mapping_dict:
            mapping_dict[idx] = o_idx

    if debug:
        print("mapping dict:", mapping_dict)
        print("model output text:", model_output_text)
        print("original_text:", original_text)
        character_mapping_dict = {}
        # for key in mapping_dict:
        #     character_mapping_dict["{}_{}".format(key,model_output_text[key])]="{}_{}".format(mapping_dict[key],original_text[mapping_dict[key]])
        # print(character_mapping_dict)

    return mapping_dict


def normalize_org_text_and_bbox(model_output_item, bbox_item, org_text_item):
    normalized_bbox, normalized_org_text = [], []
    set_model_output_item = set(model_output_item)  
    # print(org_text_item)
    # print("len(org_text_item): ",len(org_text_item))
    # print("len(model_output_item): ",len(model_output_item))
    if len(bbox_item) ==0:
        return [], []
    for idx, character in enumerate(org_text_item):
        if character not in set_model_output_item:
            # continue
            normalized_org_text.append(character)
            normalized_bbox.append(bbox_item[idx])
        normalized_org_text.append(character)
        normalized_bbox.append(bbox_item[idx])
    return normalized_org_text, normalized_bbox

def brat_output_text_bb_convert(brat_output_text, bbox, character_mapping_dict, debug=False):
    output = []
    if len(bbox)==0:
        return output
    for char_idx, char in enumerate(brat_output_text):
        # if debug:
        #     print(char_idx)
        output.append(bbox[character_mapping_dict[char_idx]])
    if debug:
        print("len brat_output_text", len(brat_output_text))
        print("len bbox ",len(bbox))
    return output

def check_null(brat_format_output):
    for id, para in enumerate(brat_format_output):
        if para is None:
            print("NULL DETECTED!!!")


def create_hard_code(brat_format_output):
    for index, para in enumerate(brat_format_output):
        if "events_info" not in para:
            para["events_info"] = {
                "entities":[],
                "triggers":[],
                "events":[]
            }
        if "relations" not in para:
            para["relations"] = []
    return brat_format_output

def find_trigger_type(entity, wrapper):
    """
    This function return the type of trigger of input entity and return "none" if input entity is not a trigger
    The type of trigger is second element of the trigger object in triggers field inside the events_ifo field inside the wrapper
    """
    entity_id = entity[0]
    # trigger_ids = [tr[0] for tr in wrapper["events_info"]["triggers"]] if "events_info" in wrapper else []
    # trigger_type="PropertyInfo" if entity_id in trigger_ids else "none"
    if "events_info" in wrapper:
        matched_event = next(
            (event for event in wrapper["events_info"]["events"] if event[1]==entity_id),
            []
            )
        if len(matched_event)==0:
            trigger = ["","none",""]
        else:
            trigger = next(
                (trig for trig in wrapper["events_info"]["triggers"] if trig[0]==entity_id),
                ["","none",""]
                )
    else:
        trigger = ["","none",""]
    return trigger[1]

def find_event_info(entity, wrapper):
    """
    This function return the all the information of an event under a dict and return an empty dict if the input entity is not a trigger
    Information of arguments is mention in field events inside field event_info of wrapper
    """
    entity_id = entity[0]
    if "events_info" not in wrapper:
        return []
    event = next(
        (e for e in wrapper.get("events_info",{}).get("events",[]) if e[1]==entity_id), []   
    )
    event_info = {}
    
    if len(event)>0:
        arguments = []
        for arg in event[2]:
            arg_type, arg_id = arg
            entity_match_arg = next((e for e in wrapper.get("entities",[]) if e[0]==arg_id),[])
            if len(entity_match_arg)==0:
                continue
            else:
                ent_type, ent_id, ent_pos, _, ent_text = entity_match_arg
                arguments.append([
                    arg_id,
                    arg_type,
                    ent_pos,
                    ent_text
                ])
        event_info ={
            "event_id":event[0],
            "trigger_id":event[1],
            "arguments":arguments,
        }
    return event_info

def convert_to_output_v2(model_output, bbox, org_texts, para_data=None,full_data_mode=True):
    final_result = []
    blank_id = []
    brat_format_output = model_output.copy()
    brat_format_output = utils.init_comment_for_entity(brat_format_output)
    nomalized_org_texts, normalized_bbox_items = [], []
    # print("start debug in ner re processing")
    
    for para_id, para_output in enumerate(model_output):
        
        if "edit_status" in para_output:
            edit_status = para_output["edit_status"]
            
        else:
            edit_status = {
                "entities":[],
                "relations":[]
            }
        # if para_id==0:
        #     # print(edit_status)
        
        nomalized_org_text, normalized_bbox_item = normalize_org_text_and_bbox(para_output["text"], bbox[para_id], org_texts[para_id])
        
        
        
        if len(bbox[para_id]) ==0:
            blank_id.append(para_id)
            continue
        
        character_mapping_dict = build_character_mapping(para_output["text"], nomalized_org_text,debug=False)

        nomalized_org_texts.append(para_output["text"])
        debug=False
        if para_id == 96:
            debug=True
        normalized_bbox_items.append(brat_output_text_bb_convert(para_output["text"], normalized_bbox_item, character_mapping_dict,debug=debug))
        
        
        # print(len(para_output["entities"]))
        # Raise error if the length of the normalized text and bounding box is not the same
        
        if len(nomalized_org_text) != len(normalized_bbox_item):
            raise ValueError("The length of the normalized text and bounding box is not the same.")
        
        num_new_add_entity = 0
        paragraph_bounding_box = merge_bounding_boxes(bbox[para_id])  # Get the bounding box for the entire paragraph
        
        for entity in para_output["entities"]:
            entity_edit_status = next((obj for obj in edit_status["entities"] if obj["id"] == entity[0]), None)
            
            if entity_edit_status is None:
                entity_edit_status = "none"
            else:
                entity_edit_status = entity_edit_status["status"]
            # print("para id ",para_id)
            current_item = {
                "content": {
                    "text": entity[-1]
                },
                "id": f"para{para_id}_" + entity[0],
                "comment": entity[1],
                "position": {
                    "rects": get_span_bounding_boxes(character_mapping_dict[entity[2][0][0]], character_mapping_dict[entity[2][0][1]-1], normalized_bbox_item)
                    # "rects": get_span_bounding_boxes(entity[2][0][0], entity[2][0][1]-1, normalized_bbox_item)
                },
                "relations": [],
                "para_id": para_id,
                "trigger":find_trigger_type(entity, para_output),
                "event_infor":find_event_info(entity, para_output),
                "user_comment": entity[-2] if len(entity)==5 else "",
                "edit_status":entity_edit_status
            }
            # if para_id == 7 and entity[0]=="T1":
            #     assert find_trigger_type(entity, para_output)=="PropertyInfo"
            ############################################# DEBUG ZONE###################################################################################
            # if current_item.get("content").get("text")=="nanocomposite membranes":
                
                # print("para_id ",para_id)
                # if len(bbox[para_id])>1136:
                #     print("bbox[para_id][1136] ", bbox[para_id][1136])
                #     print("normalized_bbox_item[1136] ",normalized_bbox_item[1136])
                # print(entity[2][0][0])
                # print(character_mapping_dict[entity[2][0][0]])
                # print(entity)
                # print(current_item)
            ############################################# DEBUG ZONE###################################################################################
            current_item["position"]["boundingRect"] = []
            if len(current_item["position"]["rects"]) > 0:
                current_item["position"]["boundingRect"] = merge_bounding_boxes(current_item["position"]["rects"])
            final_result.append(current_item)
            num_new_add_entity += 1
        if full_data_mode:
            if "relations" in para_output:
                for relation in para_output["relations"]:
                    relation_edit_status = next((obj for obj in edit_status["relations"] if obj["id"] == relation[0]), None)
                    if relation_edit_status is None:
                        relation_edit_status = "none"
                    else:
                        relation_edit_status = relation_edit_status["status"]

                    arg1_id = int(relation[2][0][1][1:]) - num_new_add_entity - 1
                    arg2_id = int(relation[2][1][1][1:]) - num_new_add_entity - 1

                    final_result[arg1_id]["relations"].append({
                        "type": relation[1],
                        "arg_type": final_result[arg2_id]["comment"],
                        "arg_text": final_result[arg2_id]["content"]["text"],
                        "id": f"para{para_id}_" + relation[0],
                        "arg_id": f"para{para_id}_{relation[2][1][1]}",
                        "edit_status":relation_edit_status
                    })
        
        if para_data is not None:
            if "bounding_box" in para_data[para_id]:
                brat_format_output[para_id]["bounding_box"] = para_data[para_id]["bounding_box"]
                brat_format_output[para_id]["page_number"] = para_data[para_id]["page_number"]
        else:
            brat_format_output[para_id]["bounding_box"] = [paragraph_bounding_box ] # Add paragraph bounding box to brat_format_output
            brat_format_output[para_id]["page_number"] = [paragraph_bounding_box["pageNumber"]]
        
        if para_data is not None:
            if len(para_data) > para_id:
                if "type" in para_data[para_id]:
                    brat_format_output[para_id]["type"] = para_data[para_id]["type"]
        else:
            brat_format_output[para_id]["type"] = "text"
        check_null(brat_format_output)
    brat_format_output = create_hard_code(brat_format_output)
    return {"pdf_format_output": final_result, "brat_format_output": brat_format_output, 'blank_id':blank_id}, normalized_bbox_items, nomalized_org_texts

def get_span_bounding_boxes(start_pos, end_pos, char_bounding_boxes):
    span_bounding_boxes = []
    span_boxes = [char for idx, char in enumerate(char_bounding_boxes) if start_pos <= idx <= end_pos]

    if not span_boxes:
        return span_bounding_boxes
    
    span_boxes.sort(key=lambda x: (x['y1'], x['x1']))

    current_row = []
    current_y = span_boxes[0]['y1']

    for char in span_boxes:
        if char['y1'] != current_y:
            if current_row:
                merged_box = merge_bounding_boxes(current_row)
                span_bounding_boxes.append(merged_box)
            current_row = [char]
            current_y = char['y1']
        else:
            current_row.append(char)

    if current_row:
        merged_box = merge_bounding_boxes(current_row)
        span_bounding_boxes.append(merged_box)

    return span_bounding_boxes

def merge_bounding_boxes(boxes):
    x1 = min(box['x1'] for box in boxes)
    y1 = min(box['y1'] for box in boxes)
    x2 = max(box['x2'] for box in boxes)
    y2 = max(box['y2'] for box in boxes)
    return {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, "width": boxes[0]["width"], "height": boxes[0]["height"],"pageNumber": boxes[0]["pageNumber"]}

