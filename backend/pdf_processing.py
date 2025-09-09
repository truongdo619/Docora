# from pdfdataextractor import Reader
import pymupdf
from tqdm import tqdm
import fitz
from magic_pdf.data.data_reader_writer import FileBasedDataWriter, FileBasedDataReader
from magic_pdf.data.dataset import PymuDocDataset
from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from magic_pdf.config.enums import SupportedPdfParseMethod
import json
import os
import re

# def convert_pdf_to_text_v2(path, min_length):
#     file = Reader()
#     data_json = {}
#     pdf = file.read_file(path)
#     if type(pdf.abstract()) is list:
#         data_json["Abstract"] = pdf.abstract()
#     else:
#         data_json["Abstract"] = [pdf.abstract()]
#     sections = pdf.section()
#     if len(sections.keys()) == 0:
#         raise Exception("No sections found in the PDF file.")

#     def remove_references_and_acknowledge(sections):
#         for key in list(sections.keys()):
#             if "reference" in key.lower() or "acknowledge" in key.lower():
#                 sections.pop(key)
#         return sections

#     def remove_short_paragraphs(sections, min_length):
#         result = {}
#         for key in list(sections.keys()):
#             tmp = []
#             for paragraph in sections[key]:
#                 if len(paragraph) > min_length:
#                     tmp.append(paragraph)
#             result[key] = tmp
#         return result

#     data_json = remove_references_and_acknowledge(data_json)
#     data_json = remove_short_paragraphs(data_json, min_length=min_length)
#     return data_json


def convert_pdf_to_text_v1(path, min_length):
    def process_blocks(blocks, min_length):
        paragraphs = []
        for block in tqdm(blocks):
            text = block[4].replace("\n", " ")
            if len(text) > min_length:
                paragraphs.append(text)
        return paragraphs
    
    all_paragraphs = []
    with pymupdf.open(path) as doc:
        for page in doc:
            blocks = page.get_text("blocks")
            all_paragraphs += process_blocks(blocks, min_length)
    return {"Full Document": all_paragraphs}

def compare_rect(rect1, rect2):
    if rect1["x1"]!=rect2["x1"] or rect1["x2"]!=rect2["x2"] or rect1["y1"]!=rect2["y1"] or rect1["y2"]!=rect2["y2"]:
        return False
    return True

def check_if_there_is_break(sample, sample_box):
    min_x = 10000
    max_x = 0
    line_down= 0 
    break_line = 0 
    container = [[]]
    rect_container = [[]]
    container_pos = 0
    for index, rect in enumerate( sample_box):
        if rect["x1"] < min_x:
            min_x = rect["x1"]
        if rect["x2"] > max_x:
            max_x = rect["x2"]
    if len(sample)!= len(sample_box):
        print("sample:  ",sample)
        print("num sample:  ",len(sample))
        print("num pos:   ",len(sample_box))
    for index, rect in enumerate( sample_box):
        if index >= len(sample):
            continue

        container[container_pos].append(sample[index])
        rect_container[container_pos].append(rect)

        if index < len(sample_box)-1:
            if compare_rect(rect, sample_box[index-1]):
                line_down+=1
                # print(sample[index])
                if sample_box[index+1]['x1'] - min_x >6 or (max_x - rect['x2']) >11:
                    break_line+=1
                    container.append([])
                    rect_container.append([])
                    container_pos+=1
    
    # print(line_down) 
    # print(break_line) 
    for index, para in enumerate(container):
        container[index] = "".join(para)
    # for index, rect_list in enumerate(rect_container):
    #     if rect_list == []:
    #         rect_container.remove(rect_list)
    #         container.remove(container[index])
    # print(container)
    container, rect_container = remove_blank_text(container, rect_container)
    return container, rect_container

def remove_blank_text(container, rect_container):
    removed = 0
    for index, text in enumerate(container):
        if text.strip()=="":
            container.remove(container[index-removed])
            rect_container.remove(rect_container[index-removed])
    return container, rect_container


def divide_paragraphs(all_pages_text_data, all_pages_bb_data):
    container = []
    rect_container = []
    for para, para_bb in list(zip(all_pages_text_data, all_pages_bb_data)):
        new_paras, new_bb = check_if_there_is_break(para, para_bb)
        container.extend(new_paras)
        rect_container.extend(new_bb)
    container, rect_container = remove_blank_pos(container, rect_container)
    return container, rect_container

def remove_blank_pos(all_pages_text_data, all_pages_bb_data):
    blank_id = []
    for index, box in enumerate(all_pages_bb_data):
        if box == []:
            blank_id.append(index)
    removed = 0
    for id in blank_id:
        all_pages_bb_data.remove(all_pages_bb_data[id-removed])
        all_pages_text_data.remove(all_pages_text_data[id-removed])
        removed+=1
    return all_pages_text_data, all_pages_bb_data

def convert_pdf_to_text_and_bounding_boxes(path):
    document = fitz.open(path)

    def extract_text_and_bounding_boxes(page, page_number):
        text_page = page.get_textpage()
        text = text_page.extractRAWDICT()
        block_texts_data = []
        block_bb_data = []
        for block in text['blocks']:
            if 'lines' in block:
                block_text = ""
                char_bounding_boxes = []
                last_char_bbox = None
                last_char_c = ''
                for line in block['lines']:
                    for span in line['spans']:
                        for char in span['chars']:
                            c = char['c']
                            bbox = char['bbox']

                            if last_char_bbox is not None:
                                y_diff = bbox[1] - last_char_bbox[3]  # Vertical difference
                                # Adjust the threshold based on your PDF's font size and spacing
                                if y_diff > 0:  # Threshold for detecting a new line
                                    # New line detected
                                    if last_char_c == '-':
                                        # Dehyphenate: remove the hyphen and don't add space
                                        block_text = block_text + c
                                        # Remove the last bounding box (hyphen)
                                        # Add current character's bounding box
                                        char_bounding_boxes.append({
                                            "x1": bbox[0],
                                            "y1": bbox[1],
                                            "x2": bbox[2],
                                            "y2": bbox[3],
                                            "width": page.rect.width,
                                            "height": page.rect.height,
                                            "pageNumber": page_number
                                        })
                                    else:
                                        # Add a space before the new line
                                        block_text += ' ' + c
                                        # Create a placeholder bounding box for the space
                                        space_bbox = {
                                            "x1": last_char_bbox[0],
                                            "y1": last_char_bbox[1],
                                            "x2": last_char_bbox[2],
                                            "y2": last_char_bbox[3],
                                            "width": page.rect.width,
                                            "height": page.rect.height,
                                            "pageNumber": page_number
                                        }
                                        char_bounding_boxes.append(space_bbox)
                                        # Add current character's bounding box
                                        char_bounding_boxes.append({
                                            "x1": bbox[0],
                                            "y1": bbox[1],
                                            "x2": bbox[2],
                                            "y2": bbox[3],
                                            "width": page.rect.width,
                                            "height": page.rect.height,
                                            "pageNumber": page_number
                                        })
                                else:
                                    # Same line
                                    block_text += c
                                    char_bounding_boxes.append({
                                        "x1": bbox[0],
                                        "y1": bbox[1],
                                        "x2": bbox[2],
                                        "y2": bbox[3],
                                        "width": page.rect.width,
                                        "height": page.rect.height,
                                        "pageNumber": page_number
                                    })
                            else:
                                # First character
                                block_text += c
                                char_bounding_boxes.append({
                                    "x1": bbox[0],
                                    "y1": bbox[1],
                                    "x2": bbox[2],
                                    "y2": bbox[3],
                                    "width": page.rect.width,
                                    "height": page.rect.height,
                                    "pageNumber": page_number
                                })

                            # Update last_char_c and last_char_bbox
                            last_char_c = c
                            last_char_bbox = bbox

                # Ensure that block_text and char_bounding_boxes have the same length
                assert len(block_text) == len(char_bounding_boxes), "Mismatch between text and bounding boxes"

                block_texts_data.append(block_text.strip())
                block_bb_data.append(char_bounding_boxes)
        return block_texts_data, block_bb_data

    all_pages_text_data = []
    all_pages_bb_data = []
    for page_number in range(len(document)):
        page = document.load_page(page_number)
        block_texts_data, block_bb_data = extract_text_and_bounding_boxes(page, page_number + 1)
        # if block_texts_data=="":
        #     continue
        for index,block_text in enumerate(block_texts_data):
            if block_text=="":
                # all_pages_text_data[-1]+= " "
                # all_pages_bb_data[-1].append(block_bb_data[index][0])
                continue
            else:
                all_pages_text_data.append(block_text)
                all_pages_bb_data.append(block_bb_data[index])
        # all_pages_text_data += block_texts_data
        # all_pages_bb_data += block_bb_data
    all_pages_text_data, all_pages_bb_data = divide_paragraphs(all_pages_text_data, all_pages_bb_data)
    return all_pages_text_data, all_pages_bb_data


# def process_pdf_to_text(path, min_length=20):
#     try:
#         print("Processing PDF file using convert_pdf_to_text_v2 ...")
#         return convert_pdf_to_text_v2(path, min_length)
#     except Exception:
#         print("Failed to process PDF file using convert_pdf_to_text_v2!")
#         print("Processing PDF file using convert_pdf_to_txt_file_v1 ...")
#         return convert_pdf_to_text_v1(path, min_length)


def collect_text_n_bbox(block,page,page_number):
    if 'lines' in block:
        block_text = ""
        char_bounding_boxes = []
        last_char_bbox = None
        last_char_c = ''
        for line in block['lines']:
            for span in line['spans']:
                for char in span['chars']:
                    c = char['c']
                    bbox = char['bbox']

                    if last_char_bbox is not None:
                        y_diff = bbox[1] - last_char_bbox[3]  # Vertical difference
                        # Adjust the threshold based on your PDF's font size and spacing
                        if y_diff > 0:  # Threshold for detecting a new line
                            # New line detected
                            if last_char_c == '-':
                                # Dehyphenate: remove the hyphen and don't add space
                                block_text = block_text + c
                                # Remove the last bounding box (hyphen)
                                # Add current character's bounding box
                                char_bounding_boxes.append({
                                    "x1": bbox[0],
                                    "y1": bbox[1],
                                    "x2": bbox[2],
                                    "y2": bbox[3],
                                    "width": page.rect.width,
                                    "height": page.rect.height,
                                    "pageNumber": page_number
                                })
                            else:
                                # Add a space before the new line
                                block_text += ' ' + c
                                # Create a placeholder bounding box for the space
                                space_bbox = {
                                    "x1": last_char_bbox[0],
                                    "y1": last_char_bbox[1],
                                    "x2": last_char_bbox[2],
                                    "y2": last_char_bbox[3],
                                    "width": page.rect.width,
                                    "height": page.rect.height,
                                    "pageNumber": page_number
                                }
                                char_bounding_boxes.append(space_bbox)
                                # Add current character's bounding box
                                char_bounding_boxes.append({
                                    "x1": bbox[0],
                                    "y1": bbox[1],
                                    "x2": bbox[2],
                                    "y2": bbox[3],
                                    "width": page.rect.width,
                                    "height": page.rect.height,
                                    "pageNumber": page_number
                                })
                        else:
                            # Same line
                            block_text += c
                            char_bounding_boxes.append({
                                "x1": bbox[0],
                                "y1": bbox[1],
                                "x2": bbox[2],
                                "y2": bbox[3],
                                "width": page.rect.width,
                                "height": page.rect.height,
                                "pageNumber": page_number
                            })
                    else:
                        # First character
                        block_text += c
                        char_bounding_boxes.append({
                            "x1": bbox[0],
                            "y1": bbox[1],
                            "x2": bbox[2],
                            "y2": bbox[3],
                            "width": page.rect.width,
                            "height": page.rect.height,
                            "pageNumber": page_number
                        })

                    # Update last_char_c and last_char_bbox
                    last_char_c = c
                    last_char_bbox = bbox
    assert len(block_text) == len(char_bounding_boxes), "Mismatch between text and bounding boxes"
    return block_text, char_bounding_boxes
 

def parse_layout_with_mineru(pdf_file_name):

    # prepare env
    local_image_dir = "mineru_output/images"

    os.makedirs(local_image_dir, exist_ok=True)

    image_writer = FileBasedDataWriter(local_image_dir)

    # read bytes
    reader1 = FileBasedDataReader("")
    pdf_bytes = reader1.read(pdf_file_name)  # read the pdf content

    # proc
    ## Create Dataset Instance
    ds = PymuDocDataset(pdf_bytes)

    ## inference
    if ds.classify() == SupportedPdfParseMethod.OCR:
        infer_result = ds.apply(doc_analyze, ocr=True)

        ## pipeline
        pipe_result = infer_result.pipe_ocr_mode(image_writer)

    else:
        infer_result = ds.apply(doc_analyze, ocr=False)

        ## pipeline
        pipe_result = infer_result.pipe_txt_mode(image_writer)

    mineru_json_content = pipe_result.get_middle_json()
    return mineru_json_content


def collect_para(para_list, result_list, page_idx,width, height):
    '''
    This function is for collect infor of para in each list of different para, it only collect bbox, type and index.
    '''
    for para in para_list:
        # x1,y1,x2,y2 = para["bbox"]
        # rect = pymupdf.Rect(x1,y1,x2,y2)
        if "blocks" in para:
            result_list = collect_para(para["blocks"],result_list,page_idx,width, height)
        else:
            if para["type"] =="discarded":
                index = 999999
            else:
                index = para["index"]
            if para["type"] =="title":
                lines = para["lines"]
                title = lines[0]["spans"][0]["content"].lower()
                if "reference" in title:
                    para["type"]="reference_title"
            result_list.append({
                "type":para["type"],
                "width":width,
                "height":height,
                "rect":para["bbox"],
                "page_number": [page_idx],
                "index":index,
            })
    return result_list

def sort_by_page_and_index(objects):
    return sorted(objects, key=lambda obj: (obj.get("page_number", float('inf')), obj.get("index", float('inf'))))

def remove_reference(para_data):
    new_result = []
    meet_reference_title=False
    
    for para in para_data:
        if para["type"] == "reference_title":
            meet_reference_title=True
        if meet_reference_title:
            if para["type"] =="title":
                meet_reference_title = False
        else:
            new_result.append(para)
    return new_result

def extract_mineru_result(mineru_json):
    # block_texts_data = [] 
    # block_bb_data = []
    para_data = []
    pdf_info_object = mineru_json['pdf_info']
    for index, page_infor in enumerate(pdf_info_object):
        images = page_infor["images"]
        tables = page_infor["tables"]
        para_blocks = page_infor["para_blocks"]
        discarded_blocks = page_infor["discarded_blocks"]
        page_idx = int(page_infor["page_idx"]) + 1
        width, height = page_infor["page_size"]
        para_data = collect_para(para_blocks, para_data,page_idx,width, height)
        # para_data = collect_para(images, para_data,page_idx,width, height)
        # para_data = collect_para(discarded_blocks, para_data,page_idx,width, height)
        # para_data = collect_para(tables, para_data,page_idx,width, height)
    # para_data = sort_by_page_and_index(para_data)
    para_data = remove_reference(para_data)
    return para_data



def check_ignore_get_text(para_type):
    ingore_list = [
        "table_body",
        # "table",
        # "image",
        "discarded",
        "image_body",
        "image_caption",
        "table_caption"

    ]
    if para_type in ingore_list:
        return True
    else:
        return False

def extract_text_n_bbox_using_pymupdf_from_mineru_result(file_path,para_data):
    document = fitz.open(file_path)
    # block_texts_data = []
    max_x2=0
    min_x1=10000000
    # block_bb_data = []
    for page_number in range(len(document)):
        page_data = document.load_page(page_number)
        for para in para_data:
            if check_ignore_get_text(para["type"]):
                para["text"] = "@"
                x1,y1,x2,y2 = para['rect']
                para["bbox"] = [
                    {
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2,
                        "width": para["width"],
                        "height": para["height"],
                        "pageNumber": para["page_number"][0]
                    }
                ]
                para["bounding_box"] = [merge_bounding_boxes(para["bbox"])]
                continue
            if para["page_number"][0] == (page_number+1):    
                threshhold = 5
                x1,y1,x2,y2 = para['rect']
                bounding_box = {'x1': 0, 'y1': 0, 'x2': 0, 'y2': 0}
                padding =0
                loop_again = False
                while (abs(bounding_box["y1"] - y1) > threshhold or abs(bounding_box["y2"] - y2) > threshhold) and (padding <= 5):
                    new_y2 = y2-padding
                    new_y1 = y1+padding
                    padding += 1
                    rect = pymupdf.Rect(x1,new_y1,x2,new_y2)
                    text_page = page_data.get_textpage(clip=rect)
                    text = text_page.extractRAWDICT()
                    if len(text['blocks']) > 1:
                        print("WE have error during locate bounding box!!!!!!!!!!!!")
                    block_texts_data = ""
                    block_bb_data = []
                    for block in text['blocks']:
                        if 'lines' in block:
                            block_text, char_bounding_boxes = collect_text_n_bbox(block,page_data,page_number+1)
                            block_texts_data+=block_text
                            block_bb_data.extend(char_bounding_boxes)
                    if len(block_bb_data) == 0 :
                        print(rect)
                        print(text)
                        continue
                    bounding_box = merge_bounding_boxes(block_bb_data)
                max_x2=bounding_box.get("x2") if bounding_box.get("x2") > max_x2 else max_x2
                min_x1=bounding_box.get("x1") if bounding_box.get("x1") < min_x1 else min_x1
                if len(block_bb_data) != 0:
                    para["text"] = block_texts_data
                    para["bbox"] = block_bb_data
                    para["bounding_box"] = [merge_bounding_boxes(para["bbox"])]
                else:
                    para["text"] = "@"
                    x1,y1,x2,y2 = para['rect']
                    para["type"] = "discarded"
                    para["bbox"] = [
                                    {
                                        "x1": x1,
                                        "y1": y1,
                                        "x2": x2,
                                        "y2": y2,
                                        "width": para["width"],
                                        "height": para["height"],
                                        "pageNumber": para["page_number"][0]
                                    }
                                ]
                    para["bounding_box"] = [merge_bounding_boxes(para["bbox"])]
    
    return para_data, min_x1, max_x2

def get_bbox_n_text_seperated(para_data):
    block_texts_data = []
    block_bb_data = []
    for para in para_data:
        block_texts_data.append(para["text"])
        block_bb_data.append(para["bbox"])
    return block_texts_data, block_bb_data

def check_if_mergable(text_para_data, para_data):
    # print()
    merge_list = []
    for index,para_tuple in enumerate(text_para_data):
        para_index, para = para_tuple
        if index>=len(text_para_data)-1:
            continue
        if check_break_at_end(para) == False and check_break_at_head(text_para_data[index+1][1])==False and check_same_width_para(para,text_para_data[index+1][1]):
            if para_index+1 <len(para_data) and para_data[para_index+1]["type"] == "text":
                merge_list.append([para_index,text_para_data[index+1][0]])
    return merge_list

def merge_para_data(para_data, merge_list):
    # Sort merge_list by tail descending, so popping won't affect earlier indices
    merge_list_sorted = sorted(merge_list, key=lambda x: x[1], reverse=True)
    
    for head, tail in merge_list_sorted:
        # Check data consistency
        assert len(para_data[head]["text"]) == len(para_data[head]["bbox"]), \
            f"Mismatch before merge at head {head}: len text {len(para_data[head]['text'])}, len bbox {len(para_data[head]['bbox'])}"
        assert len(para_data[tail]["text"]) == len(para_data[tail]["bbox"]), \
            f"Mismatch before merge at tail {tail}: len text {len(para_data[tail]['text'])}, len bbox {len(para_data[tail]['bbox'])}"
    
        para_data[head]["bbox"].append(para_data[head]["bbox"][-1])
        para_data[head]["bbox"].extend(para_data[tail]["bbox"])
        para_data[head]["text"]+=" "
        para_data[head]["text"]+=para_data[tail]["text"]
        para_data[head]["bounding_box"].extend(para_data[tail]["bounding_box"])
        para_data[head]["page_number"].extend(para_data[tail]["page_number"])
        # Validate after merge
        assert len(para_data[head]["text"]) == len(para_data[head]["bbox"]), \
            f"Mismatch after merge at head {head}: len text {len(para_data[head]['text'])}, len bbox {len(para_data[head]['bbox'])}"
        
        # Remove the merged element at tail index
        para_data.pop(tail)
    return para_data


def merge_broken_paragraph(para_data):
    text_para_data = []
    for index, para in enumerate(para_data):
        if para["type"]=="text":
            text_para_data.append((index,para))
        print("index: {} , type: {}".format(index, para["type"]))
        # print(para["bounding_box"][0]["x2"]-para["bounding_box"][0]["x1"])
    merge_list = check_if_mergable(text_para_data,para_data)
    para_data = merge_para_data(para_data, merge_list)
    # for index, para in enumerate(para_data):
    #     print("index: {} , type: {}".format(index, para["type"]))
    return para_data


def processing_pdf_using_mineru_and_pymupdf(file_path):
    mineru_json_content = parse_layout_with_mineru(file_path)
    # # print(type(mineru_json_content))
    mineru_json = json.loads(mineru_json_content)
    para_data = extract_mineru_result(mineru_json)
    para_data,min_x1, max_x2 = extract_text_n_bbox_using_pymupdf_from_mineru_result(file_path, para_data)
    para_data = merge_broken_paragraph(para_data)
    block_texts_data, block_bb_data = get_bbox_n_text_seperated(para_data)
    return block_texts_data, block_bb_data, para_data

def update_bbox_n_text_after_normalize(para_data, normalized_text, normalized_bbox):
    for para, text, bbox in list(zip(para_data, normalized_text, normalized_bbox)):
        para["text"] = text
        para["bbox"] = bbox
    return para_data

def merge_bounding_boxes(boxes):
    x1 = min(box['x1'] for box in boxes)
    y1 = min(box['y1'] for box in boxes)
    x2 = max(box['x2'] for box in boxes)
    y2 = max(box['y2'] for box in boxes)
    return {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, "width": boxes[0]["width"], "height": boxes[0]["height"],"pageNumber": boxes[0]["pageNumber"]}

def check_break_at_head(para):
    return abs(para["bbox"][0]["x1"] - para["bounding_box"][0]["x1"]) > 3

def check_break_at_end(para):
    return abs(para["bbox"][-1]["x2"] - para["bounding_box"][0]["x2"]) > 3

def check_same_width_para(para1, para2):
    width1=abs(para1["bounding_box"][0]["x1"] - para1["bounding_box"][0]["x2"])
    width2=abs(para2["bounding_box"][0]["x1"] - para2["bounding_box"][0]["x2"])
    if abs(width1-width2) < 3:
        return True
    return False

def is_same_type_para_by_length(para1, para2):
    length1 =  abs(para1["bounding_box"][0]["x2"]-para1["bounding_box"][0]["x1"])
    length2 =  abs(para2["bounding_box"][0]["x2"]-para2["bounding_box"][0]["x1"])
    if abs(length1-length2) > 20:
        return False
    else:
        return True

def extract_table_data_from_pdf(file_path):
    mineru_json_content = parse_layout_with_mineru(file_path)
    mineru_json = json.loads(mineru_json_content)
    table_data = []
    # table_data = [table for page_infor in mineru_json['pdf_info'] for table in page_infor["tables"]]
    for page_infor in mineru_json['pdf_info']:
        for table in page_infor["tables"]:
            table_data.append(table)
    new_table_data=[]
    for index, table in enumerate(table_data):
        new_table_data_format={
            "table_body":"",
            "table_caption":"",
            "table_footnote":"",
            "table_name":"",
            "context":""
        }
        for block in table["blocks"]:
            content =''
            for line in block["lines"]:
                for span in line["spans"]:
                    if "content" in span:
                        content+= span['content']
                    elif 'html' in span:
                        content+= span['html']
            new_table_data_format[block["type"]] = content
            # elif block["type"] == "table_body":
            #     new_table_data_format["table_body"] = content
            # elif block["type"] == "table_footnote":
            #     new_table_data_format["table_footnote"] = content
            match = re.search(r"Table\s+\d+", new_table_data_format["table_caption"])

            if match:
                print("Found table name:", match.group())
                new_table_data_format["table_name"] = match.group()
            else:
                print("Table name not found.")
            if new_table_data_format["table_name"]=="":
                new_table_data_format["table_name"]=f"Table {index}"
        new_table_data.append(new_table_data_format)
    print(new_table_data)
    para_data = extract_mineru_result(mineru_json)
    para_data,min_x1, max_x2 = extract_text_n_bbox_using_pymupdf_from_mineru_result(file_path, para_data)
    para_data = merge_broken_paragraph(para_data)
    block_texts_data, block_bb_data = get_bbox_n_text_seperated(para_data)

    for table in new_table_data:
        for para in block_texts_data:
            if table["table_name"] in para:
                table["context"] = para
                break
    # print(new_table_data)
    return new_table_data