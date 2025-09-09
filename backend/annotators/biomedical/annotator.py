from typing import List, Dict

from kapipe import (
    triple_extraction
)

from ..base_annotator import BaseAnnotator
from .dependencies import kapipe_to_brat

class BiomedicalAnnotator(BaseAnnotator):
    def __init__(self,identifier="biaffinener_blink_blink_atlop_cdr",**kwagrs):
        super()
        self.type="biomedical_annotator"
        self.identifier = identifier
        self.pipe = triple_extraction.load(
            identifier=self.identifier,
            gpu_map={"ner": 0, "ed_retrieval": 0, "ed_reranking": 0, "docre": 0}
        )
        
    def _annotate(self,text: List[str]):
        outputs= []
        for index,paragraph in enumerate(text):
            input_object = {
                "doc_key":f"P{index}",
                "sentences":[paragraph]
            }
            document = self.pipe(input_object)
            outputs.append(document)
        final_output = kapipe_to_brat(outputs)
        return final_output,final_output

    
    def _predict_entity(self,text):
        outputs= []
        for index,paragraph in enumerate(text):
            input_object = {
                "doc_key":f"P{index}",
                "sentences":[paragraph]
            }
           
        
            document = self.pipe(input_object)
            outputs.append(document)
        final_output = kapipe_to_brat(outputs)
        return final_output
    
    
    def _predict_relation(self,text):
        outputs= []
        for index,paragraph in enumerate(text):
            input_object = {
                "doc_key":f"P{index}",
                "sentences":[paragraph]
            }
           
        
            document = self.pipe(input_object)
            outputs.append(document)
        final_output = kapipe_to_brat(outputs)
        return final_output