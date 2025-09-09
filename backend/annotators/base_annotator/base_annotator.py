from dataclasses import dataclass, field, asdict
from abc import ABC, abstractmethod
@dataclass
class BaseAnnotator:
    def __init__(self):
        self.type="base_annotator"
    
    @abstractmethod
    def load_model(self,config, model_path):
        raise NotImplementedError
    
    @abstractmethod
    def annotate(self,input_string):
        raise NotImplementedError
    
    @abstractmethod
    def _predict_entity(self,input_string):
        raise NotImplementedError
    
    @abstractmethod
    def _predict_relation(self,input_string):
        raise NotImplementedError
    
    # @abstractmethod
    # def _predict(self,input_string):
    #     raise NotImplementedError