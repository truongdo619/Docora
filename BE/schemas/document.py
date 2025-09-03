from pydantic import BaseModel, field_serializer
from typing import List 
from typing import Optional
import re

from fastapi import UploadFile, File

class BaseInforSchame(BaseModel):
    document_id: Optional[int] = None
    update_id: Optional[int] = None

class ParaUpdate(BaseInforSchame):
    paragraphs: List[str]

class DeleteEntitySchema(BaseInforSchame):
    ids: List[str]

class Rect(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float
    width: float
    height: float
    pageNumber: int

class Position(BaseModel):
    rects: List[Rect]
    boundingRect: Rect


class CreateEntitySchema(BaseInforSchame):
    comment: str
    para_id: int
    position: Position
    scale_value: float
    user_comment: Optional[str]=""

class Relation(BaseModel):
    type: str
    arg_type: str
    arg_id: str
    arg_text: str
    id: Optional[str]=None

    @property
    def para_id(self):
        return int(self.id.split("_")[0].split("para")[1])

    @property
    def relation_id(self):
        return self.id.split("_")[1]
    
    @staticmethod
    def parse_id(id):
        return int(id.split("_")[0].split("para")[1]), id.split("_")[1]

    @staticmethod
    def valid_id(id):
        return re.match(r"para(\d+)_(R\d+)", id)

class Content(BaseModel):
    text: str

class CheckTextSchema(BaseModel):
    text: str
    ner_model: str="v1"
    re_model: str="v1"

class Highlight(BaseModel):
    id: str
    comment: str
    content: Content
    position: Position
    relations: List[Relation]
    para_id: int
    head_pos: int
    tail_pos: int

class UpdateIDSchema(BaseModel):
    update_id: Optional[int]

class DocIDSchema(BaseModel):
    doc_id: int

class UpdateEntitySchema(BaseInforSchame):
    id: str
    head_pos: Optional[int]=0
    tail_pos: Optional[int]=0
    type: str
    comment: Optional[str]=""
    user_comment: Optional[str]=""
    new_text: Optional[str]=""
    @property
    def para_id(self):
        return int(self.id.split("_")[0].split("para")[1])

    @property
    def entity_id(self):
        return self.id.split("_")[1]
    
    @staticmethod
    def parse_id(id):
        parts = id.split("_")
        # always grab the paragraph number
        para_num = int(parts[0].replace("para", ""))
        # if there's no "_T…" suffix, return -1 for the entity
        if len(parts) == 1:
            return para_num, -1
        # otherwise return the raw suffix (e.g. "T3")—or parse out the number if you prefer:
        return para_num, parts[1]
    
    @staticmethod
    def valid_id(id):
        return re.match(r"para(\d+)_(T\d+)", id)

class TargetEntityForUpdate(BaseModel):
    entity_id:str
    page_number:int
    para_id:int

class EntityUpdate(BaseModel):
    entity_id: str
    entity_type: str
    entity_text: str 
    para_id: int
    page_number: int

class ApplyUpdateSchema(BaseInforSchame):
    list_update:List[TargetEntityForUpdate]
    new_entity: EntityUpdate
    old_entity: EntityUpdate

class DeleteRelationSchema(BaseInforSchame):
    entity_id: str
    relation_id: int

# class Relation(BaseModel):
#     type: str
#     arg_type: str
#     arg_text: str 
#     arg_id: str
#     id: str

class UpdateRelationSchema(BaseInforSchame):  
    entity_id: str
    relations: List[Relation]

class TextUpload(BaseModel):
    text:str

class ChangeEditStatusSchema(BaseInforSchame):
    id: str

class DownloadEntity(BaseInforSchame):
    type: str

class Filtering(BaseModel):
    type: str
    sub_type: List[str]
    @field_serializer('sub_type', when_used='always')
    def rank_serialize(sub_type : List[str] ):
        result = 'sub_type : ' + " ".join(sub_type) 
        return result

class DownloadFiltering(BaseInforSchame):
    filtering_entity_types: List[Filtering]
    filtering_relation_types: List[Filtering]

class DownloadParaEntity(BaseInforSchame):
    para_id: Optional[int] = None
    
class DownloadJSONSchema(DownloadParaEntity):
    mode: str
    filtering_entity_types: Optional[List[Filtering]] = None
    filtering_relation_types: Optional[List[Filtering]] = None
    type: Optional[str] = None

class NewUpdateEntity(BaseInforSchame):
    update_name: str

class LegacyCreateEntitySchema(DownloadParaEntity):
    comment: str
    position: Optional[Position] = None
    head_pos: Optional[int]= None
    tail_pos: Optional[int]= None
    scale_value: Optional[float]= None

class ReorderPara(BaseInforSchame):
    old_para_id:Optional[int] = None
    paragraphs:List[int]

class VisibleList(BaseInforSchame):
    visible_list: List[bool]

class DownloadDocumentSchema(DownloadParaEntity):
    mode: str
    filtering_entity_types: Optional[List[Filtering]] = None
    filtering_relation_types: Optional[List[Filtering]] = None
    type: Optional[str] = None

    @field_serializer('filtering_entity_types', when_used='always')
    def rank_serialize(filtering_entity_types : List[Filtering] ):
        final_result = ""
        for filter in filtering_entity_types:
            result = "entity type :"+  filter.type
            result += "relation sub type: [{}]".format(" ".join(filter.sub_type))
            final_result+=f"{result}\n"
        return final_result
    @field_serializer('filtering_relation_types', when_used='always')
    def rank_serialize(filtering_entity_types : List[Filtering] ):
        final_result = ""
        for filter in filtering_entity_types:
            result = "relation type :"+  filter.type
            result += "entity sub type: [{}]".format(" ".join(filter.sub_type))
            final_result+=f"{result}\n"
        return final_result
    
def custom_serializer(obj):
    if isinstance(obj, Filtering):
        return {"name": obj.type, "value": "[{}]".format(" ".join(obj.sub_type))}
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

class Event(BaseModel):
    event_id:str
    trigger_id:str
    arguments: List[List[str]]

class UpdateEventSchema(DownloadParaEntity):
    trigger_new_head: Optional[int]=0
    trigger_new_tail: Optional[int]=0
    event: Event

class DeleteEventSchema(DownloadParaEntity):
    event_id: str

class ParseTableSchema(BaseModel):
    table_name: str
    table_body: str
    table_caption: str
    table_footnote: str
    context: str
    prompt: str
