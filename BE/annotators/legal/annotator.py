from typing import List, Dict

import spacy

from ..base_annotator import BaseAnnotator
from .dependencies import extract_entities_from_judgment_text
import traceback

class LegalAnnotator(BaseAnnotator):
    def __init__(self,**kwagrs):
        super()
        self.type="legal_annotator"
        self.legal_nlp=spacy.load('en_legal_ner_trf')
        self.preamble_spiltting_nlp = spacy.load('en_core_web_sm')
        self.run_type='sent'
        self.do_postprocess=True 

    def _annotate(self,text: List[str]):
        outputs= []
        for paragraph in text:
            try:
                # print(paragraph)
                combined_doc = extract_entities_from_judgment_text(paragraph,self.legal_nlp,self.preamble_spiltting_nlp,self.run_type,self.do_postprocess)
                entitites = []
                for index,ent in enumerate(combined_doc.ents,start=1):
                    entitites.append(
                        [
                            f"T{index}",
                            ent.label_,
                            [
                                [
                                    ent.start_char,
                                    ent.end_char
                                ]
                            ],
                            "",
                            ent.text
                        ]
                    )
                # print(entitites)
                outputs.append({
                    "text":  combined_doc.text,
                    "entities":entitites,
                    "relations":[]
                })
            except:
                print(traceback.format_exc())
                outputs.append({
                    "text":  paragraph,
                    "entities":[],
                    "relations":[]
                })
        return outputs,outputs

    
    def _predict_entity(self,text):
        outputs= []
        for paragraph in text:
            combined_doc = extract_entities_from_judgment_text(paragraph,self.legal_nlp,self.preamble_spiltting_nlp,self.run_type,self.do_postprocess)
            entitites = []
            for index,ent in enumerate(combined_doc.ents):
                entitites.append(
                    [
                        f"T{index}",
                        ent.label_,
                        [
                            ent.start_char,
                            ent.end_char,
                        ],
                        "",
                        ent.text
                    ]
                )
            outputs.append({
              "text":  combined_doc.text,
              "entities":entitites,
              "relations":[]
            })
        
        return outputs
    
    
    def _predict_relation(self,text):
        outputs= []
        for paragraph in text:
            combined_doc = extract_entities_from_judgment_text(paragraph,self.legal_nlp,self.preamble_spiltting_nlp,self.run_type,self.do_postprocess)
            entitites = []
            for index,ent in enumerate(combined_doc.ents):
                entitites.append(
                    [
                        f"T{index}",
                        ent.label_,
                        [
                            ent.start_char,
                            ent.end_char,
                        ],
                        "",
                        ent.text
                    ]
                )
            outputs.append({
              "text":  combined_doc.text,
              "entities":entitites,
              "relations":[]
            })
        
        return outputs