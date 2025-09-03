import torch
import torch.autograd
from torch.utils.data import DataLoader
from transformers import AutoConfig, AutoModel, AutoTokenizer

import json
import sys
sys.path.append("../../annotators")

from ..base_annotator import BaseAnnotator
from .models.NER_model import Config, Vocabulary, load_data_bert_predict, collate_fn
from .models.NER_model import Model as NER_Model

from .utils import NER_utils as ner_utils


# from RE.model import DocREModel
# from RE.utils import set_seed
from .models.RE_model import DocREModel
from .utils.RE_utils import set_seed, convert_to_RE_model_input_format
from .utils.NER_utils import convert_index_to_text, convert_to_NER_model_input_format, convert_text_to_index
from .models.RE_model import Config as RE_Config

from .dependencies import read_docred_real,split_continuous_arrays,model_predict, report





class PolymerAnnotator(BaseAnnotator):
    def __init__(self):
        super()
        self.type="polymer_annotator"
        
        self.ner_model = None
        self.ner_logger = None
        self.ner_config = None

        self.re_tokenizer= None
        self.re_base_model=None
        self.re_config = None
        self.re_args = None

    def load_NER_model(self,new_model=False):
        if new_model:
            config = Config("annotators/polymer/configs/NER_config/polymer_MatBERT.json")
        else:
            config = Config("annotators/polymer/configs/NER_config/polymer_MatSciBERT.json")
        logger = ner_utils.get_logger(config.dataset)    
        config.logger = logger

        # Load vocab
        vocab = Vocabulary()
        label2id = {'<pad>': 0, '<suc>': 1, 'monomer': 2, 'organic': 3, 'inorganic': 4, 'condition': 5, 'polymer_family': 6, 'syn_method': 7, 'prop_name': 8, 'prop_value': 9, 'ref_exp': 10, 'char_method': 11, 'polymer': 12, 'material_amount': 13, 'composite': 14, 'other_material': 15}
        id2label = {v:k for k,v in label2id.items()}
        vocab.label2id = label2id
        vocab.id2label = id2label
        config.label_num = len(vocab.label2id)
        print(vocab.label2id)
        config.vocab = vocab
        # Load model    
        logger.info("Building Model")
        model = NER_Model(config)
        model = model.cuda()
        model.load_state_dict(torch.load(config.save_path),  strict=False)
        model.eval()
        device = 0
        if torch.cuda.is_available():
            torch.cuda.set_device(device)
        self.ner_model = model
        self.ner_logger = logger
        self.ner_config = config
        
        # return model, logger, config


    def load_re_model(self,new_model=False):
        if new_model:
            args = RE_Config("annotators/polymer/configs/RE_config/DocRE_model_DeBERTa.json")
        else:
            args = RE_Config("annotators/polymer/configs/RE_config/DocRE_model_MatSciBERT.json")
        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        args.n_gpu = torch.cuda.device_count()
        args.device = device

        config = AutoConfig.from_pretrained(
            args.model_name_or_path,
            num_labels=args.num_class,
        )
        tokenizer = AutoTokenizer.from_pretrained(
            args.model_name_or_path,
        )
        base_model = AutoModel.from_pretrained(
            args.model_name_or_path,
            from_tf=bool(".ckpt" in args.model_name_or_path),
            config=config,
        )
        set_seed(args)
        self.re_tokenizer = tokenizer
        self.re_base_model = base_model
        self.re_config = config
        self.re_args = args

        # return tokenizer, base_model, config, args

    def check_load_model(self):
        if self.ner_model is None:
            self.load_NER_model()
        if self.re_base_model is None:
            self.load_re_model()

    def _predict_entity(self, test_data):
        """
        NER predicting function
        """
        self.check_load_model()
        # logger.info("Loading Data")
        model = self.ner_model
        config = self.ner_config
        logger = self.ner_logger
        datasets, ori_data = load_data_bert_predict(test_data, config)
        test_loader_real = DataLoader(dataset=datasets,
                    batch_size=config.batch_size,
                    collate_fn=collate_fn,
                    shuffle=False,
                    num_workers=4,
                    drop_last=False)


        print('Predicting NER ...')
        result = model_predict(model, config,test_loader_real, ori_data)
        print('Finished predicting.')
        print('Converting to Brat format...')
        assert len(result) == len(ori_data)

        raw_text = []
        abs_anns = [] # abstract/paragraph
        char_len = 0
        final_result = {}
        no_discontinuous_mentions = 0
        #print(len(ori_data))
        for i in range(len(ori_data)):
            # print(ori_data[i]["doc_ID"])
            assert ori_data[i]['sentence'] == result[i]['sentence']
            # print(len(ori_data[i]['sentence']), len(result[i]['sentence']))
            raw_text = []
            abs_anns = [] # abstract/paragraph
            if ori_data[i]['sent_ID'] == 1:
                char_len = 0    
            s = ' '.join(ori_data[i]['sentence'])
            # print(len(s))
            raw_text.append(s)
            sent_anns = result[i]['entities'] # predictions for each sentence
            #print(sent_anns)
            for ann in sent_anns: # e.g., {"text": ["in", "-", "situ", "polymerization"], "type": "syn_method", "index": [1, 2, 3, 4]}
                offsets = split_continuous_arrays(ann['index'])

                offset_string = []
                for offset in offsets:
                    w_idx_start = offset[0]
                    w_idx_end = offset[-1]
                    c_idx_start = len(' '.join(ori_data[i]['sentence'][:w_idx_start]))
                    if w_idx_start != 0:
                        c_idx_start += 1
                    c_idx_end = len(' '.join(ori_data[i]['sentence'][:w_idx_end+1]))

                    offset_string.append(str(c_idx_start + char_len) + ' ' + str(c_idx_end + char_len))
                offset_string = ';'.join(offset_string)
                if ';' in offset_string:
                    no_discontinuous_mentions += 1
                
                #if [ann[0] + char_len, ann[1] + char_len, ann[2]] not in abs_anns: # Avoid duplicates
                    #abs_anns.append([ann[0] + char_len, ann[1] + char_len, ann[2]])

                if [offset_string, ann['type'], ' '.join(ann['text'])] not in abs_anns: # Avoid duplicates
                    abs_anns.append([offset_string, ann['type'], ' '.join(ann['text'])])

            if ori_data[i]["doc_ID"] not in final_result:
                final_result[ori_data[i]["doc_ID"]] = {
                    "text": "",
                    "entities": []
                }
            final_result[ori_data[i]["doc_ID"]]["text"] += ' '.join(raw_text) + ' '
            for k in range(len(abs_anns)):
                entity_info = abs_anns[k][0].split(' ')
                entity_positions = []
                for pos in entity_info:
                    entity_positions += pos.split(';')
                # Convert to pair of two elements
                entity_positions = [[int(entity_positions[i]), int(entity_positions[i+1])] for i in range(0, len(entity_positions), 2)]
                index = len(final_result[ori_data[i]["doc_ID"]]["entities"])            
                final_result[ori_data[i]["doc_ID"]]["entities"].append([f'T{index+1}', abs_anns[k][1].upper(), entity_positions, abs_anns[k][2]])
            char_len = char_len + len(s) + 1

        # sort the result by key
        # print(final_result.keys())
        final_result = list(dict(sorted(final_result.items())).values())
        # final_result.append(tmp_cp)
        print('# of discontinuous mentions:', no_discontinuous_mentions)
        torch.cuda.empty_cache()
        print('Finished.')
        return final_result
    


    def _predict_relation(self,test_data, ner_data):
        self.check_load_model()
        args = self.re_args
        tokenizer=self.re_tokenizer
        base_model=self.re_base_model
        config=self.re_config

        test_features = read_docred_real(test_data, tokenizer, max_seq_length=args.max_seq_length)
        config.cls_token_id = tokenizer.cls_token_id
        config.sep_token_id = tokenizer.sep_token_id
        config.transformer_type = args.transformer_type
        model = DocREModel(config, base_model, num_labels=args.num_labels).to(args.device)
        model.load_state_dict(torch.load(args.load_path), strict=False)
        pred = report(args, model, test_features, ner_data)
        return pred
    
    def _annotate(self,text):
        self.check_load_model()
        ner_model_output = self._predict_entity(convert_to_NER_model_input_format(text))
        re_model_input = convert_to_RE_model_input_format(ner_model_output)
        model_output = self._predict_relation(re_model_input, ner_model_output)  
        
        return model_output, ner_model_output