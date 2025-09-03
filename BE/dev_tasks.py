import re
import json
import copy
import traceback
from datetime import datetime
from collections import defaultdict

from celery_app import app

from fastapi import  HTTPException
from pydantic import BaseModel
import httpx
from httpx import Client
import asyncio

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from ner_re_processing import convert_to_NER_model_input_format, convert_to_RE_model_input_format, convert_to_output_v2
from pdf_processing import convert_pdf_to_text_and_bounding_boxes, processing_pdf_using_mineru_and_pymupdf, update_bbox_n_text_after_normalize, extract_table_data_from_pdf

# from NER.main_predict import inference, load_ner_model
# from RE.main_predict import predict_re, load_re_model

# from EAE.predict_EAE import predict as eae_predict

from crud.psql import user as user_crud
from crud.psql import document as document_crud
# from models.psql import user as user_model
# from models.psql import document as document_model

from utils import utils
from database import get_dev_db as get_db
from annotators.polymer.annotator import PolymerAnnotator

import importlib



ANNOTATOR_REGISTRY = {
    "material": ("annotators.polymer.annotator", "PolymerAnnotator"),
    "legal":   ("annotators.legal.annotator", "LegalAnnotator"),
    "biomedical":  ("annotators.biomedical.annotator", "BiomedicalAnnotator"),
}

def load_annotator(module_name: str, class_name: str):
    """
    Dynamically import an annotator by module and class name.
    """
    module = importlib.import_module(module_name)
    return getattr(module, class_name)

def get_annotator(domain: str):
    module_name, class_name = ANNOTATOR_REGISTRY[domain]
    return load_annotator(module_name, class_name)()

def send_email(to_email,user ,document):
    # Set up the SMTP server
    with open("configs/email_config.json",'r',encoding='utf-8') as f:
        email_config = json.load(f)
    smtp_host = email_config.get("smtp_host")  # Replace with your SMTP server
    smtp_port = email_config.get("smtp_port")   # Port for TLS
    from_email = email_config.get("from_email")   # Replace with your email
    gmail_app_password = email_config.get("gmail_app_password")  # Replace with your email password

    email_title ="[Polyminder] Document Processing Notification"
    # Create the email message
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = email_title
    current_infor = document.get_infor()
    # Attach the body with the msg instance
    filename = current_infor["filename"]
    upload_time = current_infor["upload_time"]
    entities = current_infor["entities"]
    relations = current_infor["relations"]
    pages = current_infor["pages"]
    status = current_infor["status"]
    
    html_content = f"""
    <html>
    <body>
        <p>Dear Mr/Mrs <b>{user.username}</b>,</p>
        <p>The processing of document with id : {document.id} has been completed . Please go check the result at you home page.</p>
        <h3>Document Details:</h3>
            <ul>
                <li><strong>Document ID:</strong> {document.id}</li>
                <li><strong>File name:</strong> {filename}</li>
                <li><strong>Submitted on:</strong> {upload_time}</li>
                <li><strong>Number of extracted Entities:</strong> {entities}</li>
                <li><strong>Number of extracted Relations:</strong> {relations}</li>
                <li><strong>Number of pages:</strong> {pages}</li>
                <li><strong>Status:</strong> {status}</li>
            </ul>
        <p> Thank you for using service of Polyminder!</P>
        <p>Best regards</p>
    </body>
    </html>
    """
    msg.attach(MIMEText(html_content, 'html'))

    # Connect to the SMTP server
    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()  # Use TLS for security
        server.login(from_email, gmail_app_password)  # Login with your email and password

        # Send the email
        server.sendmail(from_email, to_email, msg.as_string())
        print("Email sent successfully!")

    except Exception as e:
        print(f"Failed to send email. Error: {str(e)}")

    finally:
        server.quit()

def process_pdf(file_path,doc_id,db,domain,new_model=False):
    current_doc = document_crud.get_document(db,doc_id)
    print(file_path)
    print("start parsing pdf")
    # all_pages_text_data, all_pages_bb_data = convert_pdf_to_text_and_bounding_boxes(file_location)
    all_pages_text_data, all_pages_bb_data, para_data = processing_pdf_using_mineru_and_pymupdf(file_path)
    print("parsed {} paragraphs".format(len(all_pages_text_data)))
    print(all_pages_text_data)
    print("done parsing pdf")
    
    print("start ner pdf")
    # if new_model:
    #     model_output, ner_model_output = process_text(all_pages_text_data,new_ner_model,new_ner_logger,new_ner_config,re_tokenizer,re_base_model, re_config,re_args)
    # else:
    #     model_output, ner_model_output = process_text(all_pages_text_data,ner_model,ner_logger,ner_config,re_tokenizer,re_base_model, re_config,re_args)
    annotator = get_annotator(domain)
    model_output, ner_model_output = annotator._annotate(all_pages_text_data)
    # Save data before adding event extraction
    current_doc.set_paragraphs(para_data)
    current_doc.set_relations(model_output)
    current_doc.set_entities(ner_model_output)
    print("done save re and ner, ")
    print("start count num_rel ")
    num_ent, num_rel = utils.count_ent_and_rel(model_output)
    page_num = 0
#### use loop to avoid the last element is empty list
    for box in all_pages_bb_data:
        if box == []:
            continue
        else:
            ##### in the case that did normalize text and bbox
            page_num = box[-1]["pageNumber"]
            ##### in the case that did not normalize text and bbox
            # page_num = box[-1][-1]["pageNumber"]
    print("done count num_rel ")
    info_obj = {
        "id": current_doc.id,
        "filename": current_doc.FileName,
        "upload_time": utils.serialize(current_doc.UploadTime),
        "entities": num_ent,
        "relations": num_rel,
        "pages": page_num,
        "status": "completed",
        "domain":domain
    }
    current_doc.set_infor(info_obj)
    document_crud.update_document(db, current_doc.id, current_doc)

    # Start to extract event information
    # model_output = add_event(model_output)
    # ner_model_output = add_event(ner_model_output)
    
    
    output, normalized_bb, normalized_text = convert_to_output_v2(model_output, all_pages_bb_data, all_pages_text_data, para_data=para_data)
    
    para_data = update_bbox_n_text_after_normalize(para_data,normalized_text,normalized_bb)
    current_doc.set_positions(normalized_bb)
    current_doc.set_paragraphs(para_data)
    current_doc.set_relations(model_output)
    current_doc.set_entities(ner_model_output)
    print("start update document ")
    document_crud.update_document(db, current_doc.id, current_doc)

def exception_handler(db,doc_id,user,domain):
    print(traceback.format_exc())
    current_doc = document_crud.get_document(db,doc_id)
    info_obj = current_doc.get_infor()
    info_obj["status"]="Failed"
    info_obj["domain"]=domain
    current_doc.set_infor(info_obj)
    document_crud.update_document(db, current_doc.id, current_doc)
    send_email(user.email,user,current_doc)
    return info_obj

def wrap_prop_name_tags(obj):
    text = obj["text"]
    entities = obj["entities"]

    # 1. Collect and merge all PROP_NAME spans
    spans = []
    for ent in entities:
        print(ent)
        if len(ent) > 4:
            _id, ent_type, positions, _c ,_txt = ent
        else:    
            _id, ent_type, positions, _txt = ent
        if ent_type != "PROP_NAME":
            continue
        starts = [h for h, t in positions]
        ends   = [t for h, t in positions]
        spans.append((min(starts), max(ends)))

    # 2. Remove spans fully contained within others
    spans.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    merged = []
    for s in spans:
        if not any(s[0] >= m[0] and s[1] <= m[1] for m in merged):
            merged.append(s)

    # 3. Build gap‐based markers
    n = len(text)
    opens  = defaultdict(list)  # opens at gap i (before text[i])
    closes = defaultdict(list)  # closes at gap i (before text[i])
    for start, end in merged:
        opens[start].append("<PROP_NAME>")
        closes[end].append("</PROP_NAME>")

    # 4. Assemble result by walking gaps 0..n
    out = []
    for gap in range(n + 1):
        # first close any tags ending here
        for tag in closes[gap]:
            out.append(tag)
        # then open any tags starting here
        for tag in opens[gap]:
            out.append(tag)
        # then emit the character at this gap (if any)
        if gap < n:
            out.append(text[gap])

    return "".join(out)



def add_char_positions(event_obj: dict, relation_obj: dict) -> dict:
    """
    For each trigger/argument in event_obj["events"], find its character span in relation_obj["text"]
    using a resilient whitespace‐and‐subword matching strategy, then update:
      - trigger["char_start"], trigger["char_end"]
      - trigger["text"] to the exact substring in relation_obj["text"]
      - same for each argument
    """
    text = relation_obj["text"]
    out = copy.deepcopy(event_obj)

    # Precompute whitespace‐stripped text + index map
    nospace, idx_map = [], []
    for i, ch in enumerate(text):
        if not ch.isspace():
            nospace.append(ch)
            idx_map.append(i)
    nospace = "".join(nospace)

    def find_span(phrase: str) -> tuple[int,int]:
        norm = phrase.strip()
        # 1) Flexible whitespace regex
        esc = re.escape(norm)
        pattern = esc.replace(r"\ ", r"\s+")
        m = re.search(pattern, text)
        if m:
            return m.start(), m.end()
        # 2) Collapsed‐spaces fallback
        collapsed = re.sub(r"\s+", "", norm)
        idx2 = nospace.find(collapsed)
        if idx2 != -1:
            start = idx_map[idx2]
            end   = idx_map[idx2 + len(collapsed) - 1] + 1
            return start, end
        # 3) Token‐by‐token
        tokens = re.split(r"\s+", norm)
        search_pos = 0
        for tok in tokens:
            i = text.find(tok, search_pos)
            if i < 0:
                raise ValueError(f"Cannot find subtoken {tok!r} of {phrase!r}")
            if tok is tokens[0]:
                start = i
            search_pos = i + len(tok)
        end = search_pos
        return start, end

    for ev in out["events"]:
        # Trigger
        s, e = find_span(ev["trigger"]["text"])
        ev["trigger"]["char_start"] = s
        ev["trigger"]["char_end"]   = e
        # Update trigger text to exact substring
        ev["trigger"]["text"] = text[s:e]

        # Arguments
        for arg in ev.get("arguments", []):
            s, e = find_span(arg["text"])
            arg["char_start"] = s
            arg["char_end"]   = e
            # Update argument text too
            arg["text"] = text[s:e]

    return out


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

def reformat_events(event_obj: dict, relation_obj: dict) -> tuple[dict, dict]:
    """
    1) Adds missing triggers into relation_obj["entities"] (as T#).
    2) Builds new_events_obj:
       - entities: [all triggers as ETx, then all arguments as ETx]
       - triggers: [T#, event_type, [span]]
       - events: [E#, T#, [[role, ETx], …]]
    3) Returns (new_events_obj, adjusted_relation_obj).
    """
    # 1) Deep-copy inputs
    rel = copy.deepcopy(relation_obj)
    ev_list = copy.deepcopy(event_obj)["events"]
    text = rel["text"]

    # helper to get next T# for triggers
    def next_T_id():
        nums = [int(m.group(1)) for ent in rel["entities"]
                         if (m := re.match(r"T(\d+)$", ent[0]))]
        return max(nums, default=0) + 1

    # ensure a trigger exists in rel["entities"], return its T#
    def find_or_add_trigger(span, snippet):
        for ent in rel["entities"]:
            if ent[1] == "PROP_NAME" and span in ent[2]:
                return ent[0]
        new_id = f"T{next_T_id()}"
        rel["entities"].append([new_id, "PROP_NAME", [span], "", snippet])
        return new_id

    # 2) First pass: collect
    flat_triggers   = []  # list of [T#, event_type, [span]]
    argument_entries = []  # list of (role, span, snippet) in order seen

    for ev in ev_list:
        # Trigger
        t0, t1 = ev["trigger"]["char_start"], ev["trigger"]["char_end"]
        tsp = [t0, t1]
        tsn = text[t0:t1]
        tid = find_or_add_trigger(tsp, tsn)
        flat_triggers.append([tid, ev["event_type"], [tsp]])

        # Arguments
        for arg in ev.get("arguments", []):
            a0, a1 = arg["char_start"], arg["char_end"]
            asp = [a0, a1]
            snip = text[a0:a1]
            key = (arg["role"], tuple(asp), snip)
            if key not in argument_entries:
                argument_entries.append(key)

    # 3) Assign ETx IDs
    et_map = {}
    new_entities = []
    idx = 1

    # 3a) Triggers first
    for tid, _, spans in flat_triggers:
        if tid not in et_map:
            et_map[tid] = tid
            # retrieve its entity record from rel
            for ent in rel["entities"]:
                if ent[0] == tid:
                    new_entities.append([
                        et_map[tid],      # new ETx
                        ent[1],           # PROP_NAME
                        [ent[2][0]],      # span
                        ent[3] if len(ent)>4 else "",           # comment
                        ent[-1]            # text
                    ])
                    break
            idx += 1

    # 3b) Then arguments
    for role, span, snip in argument_entries:
        # use span as a tuple for uniqueness
        key = (role, tuple(span), snip)
        if key not in et_map:
            new_ent = [
                "",
                role.upper(),
                [list(span)],
                "",
                snip
            ]
            id = next(
                (ent[0] for ent in rel.get("entities",[]) if (ent[1]==new_ent[1] and ent[2]==new_ent[2])),
                f"T{utils.decide_new_ent_number_on_1_paragraph(rel)}"
                )
            
            new_ent[0] = id
            et_map[key] = id
            rel.get("entities",[]).append(new_ent)
            new_entities.append(new_ent)
            idx += 1
            
    # 4) Build the final new_events_obj
    new_events_obj = {
        "text": text,
        "entities": new_entities,
        "triggers": flat_triggers,
        "events": []
    }

    for i, ev in enumerate(ev_list, start=1):
        # trigger ID stays T#
        t0, t1 = ev["trigger"]["char_start"], ev["trigger"]["char_end"]
        tid = find_or_add_trigger([t0, t1], text[t0:t1])
        # argument role→ETx
        role_pairs = []
        for arg in ev.get("arguments", []):
            key = (arg["role"], tuple([arg["char_start"], arg["char_end"]]), text[arg["char_start"]:arg["char_end"]])
            role_pairs.append([arg["role"], et_map[key]])
        new_events_obj["events"].append([f"E{i}", tid, role_pairs])

    # 5) adjusted_relation_obj: only updated by added triggers
    adjusted_relation = {**relation_obj, "entities": rel["entities"]}

    return new_events_obj, adjusted_relation

# def add_event(entities_wrapper):
#     for index, para in enumerate(entities_wrapper):
#         text_for_eae=wrap_prop_name_tags(para)
#         try:
#             event_output = eae_predict(text_for_eae)
            
#         except:
#             print(traceback.format_exc())
#             event_output = []
#         if len(event_output) >0:
#             new_events = add_char_positions(event_output[0], para)
#             new_events_obj, new_para = reformat_events(new_events, para)
#         else:
#             new_events_obj = {
#                 "entities":[],
#                 "triggers":[],
#                 "events":[]
#             }
#             new_para = para
#         new_para["events_info"] = new_events_obj
#         entities_wrapper[index] = new_para
    
#     return entities_wrapper

@app.task
def process_pdf_task(file_path, user_id, doc_id, domain):
    
    # setup_model()
    db = next(get_db())
    try:
        user = user_crud.get_user(db,user_id)
        process_pdf(file_path, doc_id, db,domain,new_model=False)
        print("done update document ")
        current_doc = document_crud.get_document(db,doc_id)
        send_email(user.email,user,current_doc)
        info_obj = current_doc.get_infor()
        return info_obj
    except:
        return exception_handler(db,doc_id,user,domain)
    finally:
        db.close()  

    # def process_text(text,ner_model,ner_logger,ner_config,re_tokenizer,re_base_model, re_config,re_args):
    #     ner_model_output = inference(ner_model, ner_logger,ner_config,convert_to_NER_model_input_format(text))
    #     re_model_input = convert_to_RE_model_input_format(ner_model_output)
    #     model_output = predict_re(re_args, re_tokenizer, re_base_model,re_config, re_model_input, ner_model_output)  
        
    #     return model_output, ner_model_output

# @app.task
# def process_text_task(user_id, doc_id,ner_model_text,re_model_text,event_extract=False):
    
#     is_use_ner_new_model= False if ner_model_text == "v1" else True
#     is_use_re_new_model= False if re_model_text == "v1" else True
#     print(is_use_ner_new_model, is_use_re_new_model)
#     # setup_model(use_new_ner_model=is_use_ner_new_model, use_new_re_model=is_use_re_new_model)
#     db = next(get_db())
#     try:
#         user = user_crud.get_user(db,user_id)
#         document = document_crud.get_document(db,doc_id)
#         text = document.get_paragraphs()
#         # if is_use_ner_new_model:
#         #     print("used new ner model")
#         #     cur_ner_model, cur_ner_config, cur_ner_logger = new_ner_model, new_ner_config, new_ner_logger
#         # else :
#         #     print("used old re model")
#         #     cur_ner_model, cur_ner_config, cur_ner_logger = ner_model, ner_config, ner_logger 
#         # if is_use_re_new_model:
#         #     print("used new re model")
#         #     cur_re_tokenizer, cur_re_base_model, cur_re_config, cur_re_args = new_re_tokenizer, new_re_base_model, new_re_config, new_re_args
#         # else: 
#         #     print("used old re model")
#         #     cur_re_tokenizer, cur_re_base_model, cur_re_config, cur_re_args = re_tokenizer, re_base_model, re_config, re_args  
#         # print(type(cur_re_base_model).__name__)
#         # model_output, ner_model_output = process_text(text,cur_ner_model,cur_ner_logger,cur_ner_config,cur_re_tokenizer,cur_re_base_model, cur_re_config,cur_re_args)
#         document.set_entities(ner_model_output)
#         document.set_relations(model_output)
#         document = document_crud.update_document(db, doc_id, document)
#         if event_extract:
#             # model_output = add_event(model_output)
#             # ner_model_output = add_event(ner_model_output)    
#             document.set_entities(ner_model_output)
#             document.set_relations(model_output)
#             document = document_crud.update_document(db, doc_id, document)

#         return model_output
#     except:
#         exception_handler(db,doc_id,user)
#     finally:
#         db.close()  

# @app.task
# def process_text_task_full_pipeline(user_id, doc_id,ner_model_text,re_model_text):
    
#     use_ner_new_model= False if ner_model_text == "v1" else True
#     use_re_new_model= False if re_model_text == "v1" else True
#     print(use_ner_new_model, use_re_new_model)
#     # setup_model(use_new_ner_model=use_ner_new_model, use_new_re_model=use_re_new_model)
#     db = next(get_db())
#     try:
#         user = user_crud.get_user(db,user_id)
#         document = document_crud.get_document(db,doc_id)
#         text = document.get_paragraphs()
#         if use_ner_new_model:
#             print("used new ner model")
#             cur_ner_model, cur_ner_config, cur_ner_logger = new_ner_model, new_ner_config, new_ner_logger
#         else :
#             print("used old re model")
#             cur_ner_model, cur_ner_config, cur_ner_logger = ner_model, ner_config, ner_logger 
#         if use_re_new_model:
#             print("used new re model")
#             cur_re_tokenizer, cur_re_base_model, cur_re_config, cur_re_args = new_re_tokenizer, new_re_base_model, new_re_config, new_re_args
#         else: 
#             print("used old re model")
#             cur_re_tokenizer, cur_re_base_model, cur_re_config, cur_re_args = re_tokenizer, re_base_model, re_config, re_args  
#         print(type(cur_re_base_model).__name__)
#         model_output, ner_model_output = process_text(text,cur_ner_model,cur_ner_logger,cur_ner_config,cur_re_tokenizer,cur_re_base_model, cur_re_config,cur_re_args)
#         # model_output = add_event(model_output)
#         # ner_model_output = add_event(ner_model_output)
#         print(model_output)
#         document.set_entities(ner_model_output)
#         document.set_relations(model_output)
#         document = document_crud.update_document(db, doc_id, document)
#         return model_output
#     except:
#         exception_handler(db,doc_id,user)
#     finally:
#         db.close()  

@app.task
def process_pdf_task_with_json(file_path,json_file_path, user_id, doc_id):
    db = next(get_db())
    try:
        user = user_crud.get_user(db,user_id)
        all_pages_text_data, all_pages_bb_data, para_data = processing_pdf_using_mineru_and_pymupdf(file_path)
        with open(json_file_path,'r',encoding='utf-8') as f:
            relations = json.load(f)
        # output, normalized_bb, normalized_text = convert_to_output_v2(relations, all_pages_bb_data, all_pages_text_data, para_data=para_data)
        current_doc = document_crud.get_document(db,doc_id)
        current_doc.set_positions(all_pages_bb_data)
    # current_doc.set_paragraphs(normalized_text)
        current_doc.set_paragraphs(para_data)
        current_doc.set_relations(relations)
        current_doc.set_entities(relations)
        num_ent, num_rel = utils.count_ent_and_rel(relations)
        for box in all_pages_bb_data:
            if box == []:
                continue
            else:
                ##### in the case that did normalize text and bbox
                page_num = box[-1]["pageNumber"]
        info_obj = {
            "id": current_doc.id,
            "filename": current_doc.FileName,
            "upload_time": utils.serialize(current_doc.UploadTime),
            "entities": num_ent,
            "relations": num_rel,
            "pages": page_num,
            "status": "completed"
        }
        current_doc.set_infor(info_obj)
        document_crud.update_document(db, current_doc.id, current_doc)
        send_email(user.email,user,current_doc)
        # info_obj = current_doc.get_infor()
        return info_obj
    except:
        exception_handler(db,doc_id,user)
    finally:
        db.close()  

@app.task
def re_run_re(update_id, user_id, document_id, use_new_ner_model=False, use_new_re_model=True):
    db = next(get_db())
    try:
        update = document_crud.get_current_temporary_update(db,user_id,update_id,document_id)
        entities = update.get_entities()
        new_re_model_input = convert_to_RE_model_input_format(entities)
        info_obj = update.get_infor()
        domain = info_obj.get("domain","polymer")
        annotator = get_annotator(domain)
        new_relation = annotator._predict_relation(new_re_model_input,entities)
        # new_relation = predict_re(cur_re_args, cur_re_tokenizer, cur_re_base_model,cur_re_config,new_re_model_input, entities)

        new_relation = utils.execute_user_note_on_relations(update.get_user_notes(),new_relation)
        update.set_relations(new_relation)
        update = document_crud.modify_update_as_object(db,update.id,update)
    finally:
        db.close()  

@app.task
def re_run(update_id, user_id, document_id, run_ner, use_new_ner_model=False, use_new_re_model=False):
    # setup_model(use_new_ner_model=use_new_ner_model,use_new_re_model=use_new_re_model)
    db = next(get_db())
    try:
        document = document_crud.get_document(db,document_id)
        update = document_crud.get_current_temporary_update(db,user_id,update_id,document_id)
        # update = document_crud.get_last_update(db,document_id,current_user.id)
        
        info_obj = document.get_infor()
        domain = info_obj.get("domain","polymer")
        annotator = get_annotator(domain)
        
        user_notes = update.get_user_notes()
        para_data = document.get_paragraphs()

        # if use_new_ner_model:
        #     cur_ner_model, cur_ner_logger, cur_ner_config = new_ner_model, new_ner_logger, new_ner_config
        # else:
        #     cur_ner_model, cur_ner_logger, cur_ner_config = ner_model, ner_logger, ner_config

        # if use_new_re_model:
        #     cur_re_tokenizer, cur_re_base_model, cur_re_config, cur_re_args = new_re_tokenizer ,new_re_base_model ,new_re_config,new_re_args
        # else:
        #     cur_re_tokenizer, cur_re_base_model, cur_re_config, cur_re_args = re_tokenizer ,re_base_model ,re_config,re_args


        if type(para_data[0]) == str:
            paragraphs, old_bboxs = para_data, document.get_positions()
        else:
            paragraphs, old_bboxs = utils.get_bbox_n_text_seperated(para_data)

        if run_ner:
            # ner_model_output = inference(cur_ner_model, cur_ner_logger,cur_ner_config,convert_to_NER_model_input_format(paragraphs))
            # # cur_entities = utils.execute_user_note_on_entities(user_notes,ner_model_output)
            cur_entities = annotator._predict_entities(paragraphs)
            # cur_entities = ner_model_output
        else:
            cur_entities = update.get_entities()

        re_model_input = convert_to_RE_model_input_format(cur_entities)
        # model_output = predict_re(cur_re_args, cur_re_tokenizer, cur_re_base_model,cur_re_config,re_model_input, cur_entities)
        model_output = annotator._predict_relation(re_model_input,cur_entities)
        # cur_relations = utils.execute_user_note_on_relations(user_notes,model_output)

        new_para, new_bbox, cur_entities, cur_relations, change_ids, para_data = utils.execute_user_note_on_all_data(user_notes, paragraphs, old_bboxs, cur_entities, model_output,para_data=para_data)
        update.set_relations(cur_relations)
        update.set_entities(cur_entities)
        update = document_crud.modify_update_as_object(db,update.id,update)
    finally:
        db.close()  

@app.task
def re_run_for_changed_para(update_id, user_id, document_id):
    # setup_model()
    db = next(get_db())
    try:
        update = document_crud.get_current_temporary_update(db,user_id,update_id,document_id)
        document = document_crud.get_document(db,document_id)
        user_notes = update.get_user_notes()
        old_entity = document.get_entities()
        old_relations = document.get_relations()

        changed_ids, changed_para, changed_old_text, changed_old_pos = [], [], [], []
        
        para_data = document.get_paragraphs()
        # old_bboxs =document.get_positions()


        # new_para , new_bbox, change_ids = utils.execute_user_note_on_paragraphs(user_notes,old_para, old_bboxs)
        if type(para_data[0]) == str:
            old_bboxs = document.get_positions()
            old_para = para_data
            new_para , new_bbox, change_ids, _ = utils.execute_user_note_on_paragraphs(user_notes, old_para, old_bboxs)
        else:
            old_para,old_bboxs = utils.get_bbox_n_text_seperated(para_data)
            new_para , new_bbox, change_ids, para_data = utils.execute_user_note_on_paragraphs(user_notes, old_para, old_bboxs,para_data=para_data)

        for index, para in enumerate(new_para):
            if para != old_para[index]:
                changed_ids.append(index)
                changed_para.append(para)
                changed_old_text.append(old_para[index])
                changed_old_pos.append(old_bboxs[index])
                print("----------------------------------")
                print(old_para[index])
                print(para)
        print("changed_ids", changed_ids)

        # new_ner = inference(ner_model, ner_logger,ner_config,convert_to_NER_model_input_format(changed_para))
        # new_re_model_input = convert_to_RE_model_input_format(new_ner)
        # new_model_output = predict_re(re_args, re_tokenizer, re_base_model,re_config,new_re_model_input, new_ner)
        info_obj = document.get_infor()
        domain = info_obj.get("domain","polymer")
        annotator = get_annotator(domain)
        new_model_output, new_ner = annotator._annotate(changed_para)

        for id,index in enumerate(changed_ids):
            old_entity[index] = new_ner[id]
            old_relations[index] = new_model_output[id]
        # new_ner = utils.execute_one_note_on_entities(user_notes,new_ner)
        # new_model_output = utils.execute_user_note_on_relations(user_notes,new_model_output)
        update.set_entities(old_entity)
        update.set_relations(old_relations)
        update = document_crud.modify_update_as_object(db,update.id,update)
    finally:
        db.close()  

TARGET_URL = "http://192.168.10.2:8000/process"
# TARGET_URL= "http://192.168.10.7:8000/v1/completions"
class TextRequest(BaseModel):
    model: str="Qwen/Qwen2.5-14B-Instruct"
    prompt: str
    max_tokens: int=2048
    temperature: float=0.8


# class TextRequest(BaseModel):
#     text: str 

async def forward_text(request):
    # 1. Configure a longer timeout on the HTTP client
    timeout = httpx.Timeout(
        connect=10.0,   # wait up to 10s to establish connection
        read=180.0,      # wait up to 60s for a server response
        write=10.0,
        pool=5.0
    )
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            # 2. Optionally also pass a per-request timeout
            resp = await client.post(
                TARGET_URL,
                json=request,
                timeout=timeout
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            # if the upstream call fails (timeout or other), return a 502
            print("Upstream HTTP error:", repr(e))
            raise HTTPException(status_code=502, detail=str(e))
            # raise HTTPException(status_code=502, detail=str(e))
        return resp.json()

def sync_forward_text_sync(request):
    timeout = httpx.Timeout(connect=10.0, read=180.0, write=10.0, pool=5.0)
    with Client(timeout=timeout) as client:
        resp = client.post(TARGET_URL, json=request)
        resp.raise_for_status()
        return resp.json()

@app.task
def extract_table_from_PDF(file_path,base_prompt, user_id, doc_id):
    # setup_model()
    db = next(get_db())
    try:
        user = user_crud.get_user(db,user_id)
        current_doc = document_crud.get_document(db,doc_id)
        new_table_data = extract_table_data_from_pdf(file_path)
        current_doc.set_events(new_table_data)
        info_obj = current_doc.get_infor()
        document_crud.update_document(db,doc_id,current_doc)
        return info_obj
    except:
        return exception_handler(db,doc_id,user)
    finally:
        db.close()      


# @app.task
# def parse_table_content(file_path,base_prompt, user_id, doc_id):
#     setup_model()
#     db = next(get_db())
#     try:
#         user = user_crud.get_user(db,user_id)
#         current_doc = document_crud.get_document(db,doc_id)
#         new_table_data = extract_table_data_from_pdf(file_path)
#         new_table_data = [build_prompt(table,base_prompt) for table in new_table_data]
        
#         for table in new_table_data:
#             prompt=table["prompt"]
#             # coro = asyncio.wait_for(forward_text({"text":prompt}),timeout=240)
#             # response = asyncio.run(coro)
#             # request = TextRequest(prompt=prompt)
#             # response = sync_forward_text_sync(request.dict())

#             response = sync_forward_text_sync({"text": prompt})
            
#             table["answer"]=response
#             # print(response)
#         current_doc.set_events(new_table_data)
#         info_obj = current_doc.get_infor()
#         document_crud.update_document(db,doc_id,current_doc)
#         return info_obj
#     except:
#         return exception_handler(db,doc_id,user)
#     finally:
#         db.close()      




# curl http://192.168.10.7:8000/v1/completions \
#     -H "Content-Type: application/json" \
#     -d '{
#         "model": "Qwen/Qwen2.5-14B-Instruct",
#         "prompt": "San Francisco is a",
#         "max_tokens": 7,
#         "temperature": 0
#     }'

# smaller  than  100  μ m
# μ