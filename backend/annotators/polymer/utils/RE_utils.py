import json
import torch
import random
import numpy as np

from ..configs.NER_config.ner_config import nlp

def set_seed(args):
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if args.n_gpu > 0 and torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)


def collate_fn(batch):
    max_len = max([len(f["input_ids"]) for f in batch])
    input_ids = [f["input_ids"] + [0] * (max_len - len(f["input_ids"])) for f in batch]
    input_mask = [[1.0] * len(f["input_ids"]) + [0.0] * (max_len - len(f["input_ids"])) for f in batch]
    labels = [f["labels"] for f in batch]
    entity_pos = [f["entity_pos"] for f in batch]
    hts = [f["hts"] for f in batch]
    input_ids = torch.tensor(input_ids, dtype=torch.long)
    input_mask = torch.tensor(input_mask, dtype=torch.float)
    output = (input_ids, input_mask, labels, entity_pos, hts)
    #output = (input_ids, input_mask, labels, entity_pos, hts, [f["title"] for f in batch]) # DEBUG
    return output

def convert_sentence_to_output_format(sentence):
    row = sentence.split('\t')
    relation_id = row[0]
    relation_info = row[1].split(" ")
    relation_type = relation_info[0]
    arg1 = relation_info[1].split(":")
    arg2 = relation_info[2].split(":")
    return [relation_id, relation_type, [arg1, arg2]]


def collate_fn_real(batch): # For real data (prediction)
    max_len = max([len(f["input_ids"]) for f in batch])
    input_ids = [f["input_ids"] + [0] * (max_len - len(f["input_ids"])) for f in batch]
    input_mask = [[1.0] * len(f["input_ids"]) + [0.0] * (max_len - len(f["input_ids"])) for f in batch]
    labels = [f["labels"] for f in batch]
    entity_pos = [f["entity_pos"] for f in batch]
    hts = [f["hts"] for f in batch]
    input_ids = torch.tensor(input_ids, dtype=torch.long)
    input_mask = torch.tensor(input_mask, dtype=torch.float)
    #output = (input_ids, input_mask, labels, entity_pos, hts)
    output = (input_ids, input_mask, labels, entity_pos, hts, [f["entities"] for f in batch])
    #output = (input_ids, input_mask, labels, entity_pos, hts, [f["title"] for f in batch]) # DEBUG
    return output

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