
import numpy as np
import ujson as json

import torch
import torch.autograd
from torch.utils.data import DataLoader

from .utils.NER_utils import decode

import sys
sys.path.append("../../annotators")

from tqdm import tqdm

from .utils.RE_utils import collate_fn_real, convert_sentence_to_output_format

docred_rel2id = json.load(open('RE/meta/rel2id_polymer.json', 'r'))

def read_docred_real(data, tokenizer, max_seq_length=1024):
    i_line = 0
    pos_samples = 0
    neg_samples = 0
    features = []
    for sample in tqdm(data, desc="Example"):
        sents = []
        sent_map = []

        entities = sample['vertexSet']
        entity_start, entity_end = [], []
        for entity in entities:
            for mention in entity:
                sent_id = mention["sent_id"]
                pos = mention["pos"]
                entity_start.append((sent_id, pos[0],))
                entity_end.append((sent_id, pos[1] - 1,))
        for i_s, sent in enumerate(sample['sents']):
            new_map = {}
            for i_t, token in enumerate(sent):
                tokens_wordpiece = tokenizer.tokenize(token)
                if (i_s, i_t) in entity_start:
                    tokens_wordpiece = ["*"] + tokens_wordpiece
                if (i_s, i_t) in entity_end:
                    tokens_wordpiece = tokens_wordpiece + ["*"]
                new_map[i_t] = len(sents)
                sents.extend(tokens_wordpiece)
            new_map[i_t + 1] = len(sents)
            sent_map.append(new_map)

        train_triple = {}
        if "labels" in sample:
            for label in sample['labels']:
                evidence = label['evidence']
                r = int(docred_rel2id[label['r']])
                if (label['h'], label['t']) not in train_triple:
                    train_triple[(label['h'], label['t'])] = [
                        {'relations': r, 'evidence': evidence}]
                else:
                    train_triple[(label['h'], label['t'])].append(
                        {'relations': r, 'evidence': evidence})

        entity_pos = []
        for e in entities:
            entity_pos.append([])
            for m in e:
                start = sent_map[m["sent_id"]][m["pos"][0]]
                end = sent_map[m["sent_id"]][m["pos"][1]]
                entity_pos[-1].append((start, end,))

        relations, hts = [], []
        for h, t in train_triple.keys():
            relation = [0] * len(docred_rel2id)
            for mention in train_triple[h, t]:
                relation[mention["relations"]] = 1
                evidence = mention["evidence"]
            relations.append(relation)
            hts.append([h, t])
            pos_samples += 1

        for h in range(len(entities)):
            for t in range(len(entities)):
                if h != t and [h, t] not in hts:
                    relation = [1] + [0] * (len(docred_rel2id) - 1)
                    relations.append(relation)
                    hts.append([h, t])
                    neg_samples += 1
        assert len(relations) == len(entities) * (len(entities) - 1)

        sents = sents[:max_seq_length - 2]
        input_ids = tokenizer.convert_tokens_to_ids(sents)
        input_ids = tokenizer.build_inputs_with_special_tokens(input_ids)

        i_line += 1
        feature = {'input_ids': input_ids,
                   'entity_pos': entity_pos,
                   'labels': relations,
                   'hts': hts,
                   'title': sample['title'],
                   'entities': entities,
                   }
        features.append(feature)

    print("# of documents {}.".format(i_line))
    print("# of positive examples {}.".format(pos_samples))
    print("# of negative examples {}.".format(neg_samples))
    return features


def split_continuous_arrays(arr):
    result = []
    temp_array = []

    for i in range(len(arr) - 1):
        temp_array.append(arr[i])

        # Check if the next element breaks the continuity
        if arr[i] + 1 != arr[i + 1]:
            result.append(temp_array)
            temp_array = []

    # Include the last element in the last subarray
    temp_array.append(arr[-1])
    result.append(temp_array)
    return result

def model_predict(model, config, data_loader, data):
    model.eval()
    result = []
    i = 0
    with torch.no_grad():
        for data_batch in data_loader:
            sentence_batch = data[i:i+config.batch_size]
            entity_text = data_batch[-1]
            data_batch = [data.cuda() for data in data_batch[:-1]]
            bert_inputs, grid_labels, grid_mask2d, pieces2word, dist_inputs, sent_length = data_batch

            outputs = model(bert_inputs, grid_mask2d, dist_inputs, pieces2word, sent_length)
            length = sent_length

            grid_mask2d = grid_mask2d.clone()

            outputs = torch.argmax(outputs, -1)
            ent_c, ent_p, ent_r, decode_entities = decode(outputs.cpu().numpy(), entity_text, length.cpu().numpy())

            for ent_list, sentence in zip(decode_entities, sentence_batch):
                sentence = sentence["sentence"]
                instance = {"sentence": sentence, "entities": []}
                for ent in ent_list:
                    instance["entities"].append({"text": [sentence[x] for x in ent[0]],
                                                "type": config.vocab.id_to_label(ent[1]),
                                                "index": ent[0]})
                result.append(instance)
            i += config.batch_size
    return result

def report(args, model, features, ner_data):
    # for row in features:
        # with open('test_middle_output/para_length.txt','a',encoding='utf-8') as f:
        #     f.write("{}\n".format(len(row['input_ids'])))
    dataloader = DataLoader(features, batch_size=args.test_batch_size, shuffle=False, collate_fn=collate_fn_real, drop_last=False)
    preds = []
    for batch in dataloader:
        model.eval()

        inputs = {'input_ids': batch[0].to(args.device),
                  'attention_mask': batch[1].to(args.device),
                  'entity_pos': batch[3],
                  'hts': batch[4],
                  }
        
        with torch.no_grad():
            pred, *_ = model(**inputs)
            pred = pred.cpu().numpy()
            pred[np.isnan(pred)] = 0
            preds.append(pred)

    # if no relation is predicted, return ner_data
    if len(preds) == 0:
        return ner_data
    
    preds = np.concatenate(preds, axis=0).astype(np.float32)
    #preds = to_official(preds, features)

    # to_official
    #rel2id = json.load(open('meta/rel2id_polymer.json', 'r')) # polymer data
    id2rel = {value: key for key, value in docred_rel2id.items()}

    h_idx, t_idx, title, entities = [], [], [], []

    for f in features:
        hts = f["hts"]
        h_idx += [ht[0] for ht in hts]
        t_idx += [ht[1] for ht in hts]
        title += [f["title"] for ht in hts]
        entities += [f["entities"] for ht in hts]

    res = []
    rel_anns_brat_format = {}
    for i in range(preds.shape[0]):
        pred = preds[i]
        pred = np.nonzero(pred)[0].tolist()
        for p in pred:
            if p != 0:
                res.append(
                    {
                        'title': title[i],
                        'h_idx': h_idx[i],
                        'h_mention': entities[i][h_idx[i]][0]['name'], # get 1st mention of entity (one entity has several mentions, all of them are same in polymer abstract's setting)
                        # 'h_mention': entities[i][h_idx[i]]
                        't_idx': t_idx[i],
                        't_mention': entities[i][t_idx[i]][0]['name'],
                        #'t_mention': entities[i][t_idx[i]]
                        'r': id2rel[p],
                    }
                )
                min_entity_pair_dist = 1e6
                brat_head_entity_mention_id = brat_tail_entity_mention_id = -1
                for e1 in entities[i][h_idx[i]]:
                    for e2 in entities[i][t_idx[i]]:
                        #print(title[i], entities[i][h_idx[i]], entities[i][t_idx[i]], int(e1['pos'][0]), int(e2['pos'][0]))
                        #if abs(int(e1['pos'][0]) - int(e2['pos'][0])) < min_entity_pair_dist:
                            #min_entity_pair_dist = abs(int(e1['pos'][0]) - int(e2['pos'][0]))
                        if 100 * abs(int(e1['sent_id']) - int(e2['sent_id'])) + abs(int(e1['pos'][0]) - int(e2['pos'][0])) < min_entity_pair_dist: # Add 100 to penalize mentions in other sentences3
                            min_entity_pair_dist = 100 * abs(int(e1['sent_id']) - int(e2['sent_id'])) + abs(int(e1['pos'][0]) - int(e2['pos'][0]))
                            brat_head_entity_mention_id = e1['brat_entity_mention_id']
                            brat_tail_entity_mention_id = e2['brat_entity_mention_id']
                #print(brat_head_entity_mention_id, brat_tail_entity_mention_id)

                if title[i] not in rel_anns_brat_format:
                    rel_anns_brat_format[title[i]] = [id2rel[p] + ' Arg1:T' + str(brat_head_entity_mention_id) + ' Arg2:T' + str(brat_tail_entity_mention_id)]
                else:
                    rel_anns_brat_format[title[i]] = rel_anns_brat_format[title[i]] + [id2rel[p] + ' Arg1:T' + str(brat_head_entity_mention_id) + ' Arg2:T' + str(brat_tail_entity_mention_id)]

    # print(rel_anns_brat_format.keys())
    for key, value in rel_anns_brat_format.items(): # for each abstract, key: title, value: relation annotations. e.g., 'abbreviation_of Arg1:T8 Arg2:T7'
        para_id = int(key)
        ent_id_type_map = {}
        ent_id_start_offset_map = {}
        ner_data[para_id]['relations'] = []
        for entity in ner_data[para_id]['entities']:
            ent_id_type_map[entity[0]] = entity[1]
            ent_id_start_offset_map[entity[0]] = entity[2][0][0]

        for rel_id in range(len(value)):
            filter = False # focus on particular relations
            if filter:
                if abs(ent_id_start_offset_map[value[rel_id].split(' ')[1].split(':')[1]] - ent_id_start_offset_map[value[rel_id].split(' ')[2].split(':')[1]]) <= 200: # maximum distance (# of characters) between 2 entities in a relation
                    # keep only 'has_property' and 'has_value'
                    if value[rel_id].split(' ')[0] == 'has_property':
                        if ent_id_type_map[value[rel_id].split(' ')[1].split(':')[1]] in ['POLYMER', 'REF_EXP'] and ent_id_type_map[value[rel_id].split(' ')[2].split(':')[1]] in ['PROP_NAME']: # POLYMER relevent
                            ner_data[para_id]['relations'].append(convert_sentence_to_output_format('R' + str(rel_id+1) + '\t' + value[rel_id]))
                    elif value[rel_id].split(' ')[0] == 'has_value':
                        if ent_id_type_map[value[rel_id].split(' ')[1].split(':')[1]] in ['POLYMER', 'PROP_NAME', 'REF_EXP'] and ent_id_type_map[value[rel_id].split(' ')[2].split(':')[1]] in ['PROP_VALUE']: # POLYMER relevant
                            ner_data[para_id]['relations'].append(convert_sentence_to_output_format('R' + str(rel_id+1) + '\t' + value[rel_id]))
                    elif value[rel_id].split(' ')[0] == 'refers_to':
                        if ent_id_type_map[value[rel_id].split(' ')[1].split(':')[1]] in ['REF_EXP']:
                            ner_data[para_id]['relations'].append(convert_sentence_to_output_format('R' + str(rel_id+1) + '\t' + value[rel_id]))
            else:
                ner_data[para_id]['relations'].append(convert_sentence_to_output_format('R' + str(rel_id+1) + '\t' + value[rel_id]))
    return ner_data

