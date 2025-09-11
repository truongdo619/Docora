# Docora Backend <!-- omit in toc -->

The **Docora Backend** provides PDF parsing, automated annotation, and data management services for the Docora system.  
It exposes APIs via **FastAPI**, coordinates annotation pipelines, and integrates with **Celery** and **PostgreSQL** for task management and storage.


## Table of Contents
1. [Project Overview](#project-overview)  
2. [Project Structure](#project-structure)  
3. [Environment Setup](#environment-setup)  
4. [Download Pretrained Models](#download-pretrained-models)  
5. [Inference Instructions](#inference-instructions)  
6. [Docker Setup](#docker-setup)  
7. [Running the System](#running-the-system)  
8. [Adding New Domain Annotators](#adding-new-domain-annotators)  
9. [Supported Domains and Results](#supported-domains-and-results)  


## Project Overview

The backend is responsible for:  
- Parsing PDFs and extracting layout + text.  
- Running **automatic annotators** for different scientific domains.  
- Storing structured entities, relations, and metadata in a PostgreSQL database.  
- Providing APIs to the Docora frontend for visualization and editing.  


## Project Structure

```text
backend/
├── app/             # FastAPI app entry point
├── annotators/      # Domain-specific automatic annotators
│   ├── material/
│   ├── biomedical/
│   └── legal/
├── docker/          # Docker configs for Celery, PostgreSQL, Redis
├── models/          # Pretrained NER/RE models
├── tasks/           # Celery task definitions
└── utils/           # Helper scripts
```


## Environment Setup

```bash
conda create --name docora_backend python=3.9
conda activate docora_backend

# Core dependencies
conda install pytorch==1.10.0 torchvision torchaudio cudatoolkit=11.3 -c pytorch
pip install numpy==1.20.0 gensim==4.1.2 transformers==4.13.0 pandas==1.3.4 scikit-learn==1.0.1 prettytable==2.4.0
pip install opt-einsum==3.3.0 ujson
pip install fastapi uvicorn
pip install pymupdf pycorenlp ipdb
pip install "celery[redis,amqp]" sqlalchemy psycopg2-binary
pip install passlib python-jose
pip install -U "magic-pdf[full]"
pip install python-multipart
```


## Download Pretrained Models

Place pretrained models in the `backend/models/` directory.  
Download links are available here: [Google Drive](https://drive.google.com/drive/folders/1dsoae6AOPXOV0tLwK3t2gya6Sf7Zi6rd?usp=sharing).


## Inference Instructions
(Note: A CoreNLP server, such as stanford-corenlp-4.5.4, needs to be running to perform sentence splitting and tokenization.

```bash
java -mx4g -cp "*" edu.stanford.nlp.pipeline.StanfordCoreNLPServer -port 9000 -timeout 15000
```
Refer [this URL](https://stanfordnlp.github.io/CoreNLP/download.html) for more instructions)

## Docker Setup for Celery and PostgreSQL

Go to the `./docker` directory and start the containers:

```bash
docker-compose up -d
```

## Running the System

For celery server, run the following command:
```bash
# celery -A tasks worker --pool=solo --loglevel=info
python -m celery -A dev_tasks worker --pool=solo --loglevel=info
```

For inference, run the system:
```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```


## Adding New Domain Annotators

Docora’s backend is designed for **extensibility**. To add a new domain:  

1. Create a new folder under `annotators/` (e.g., `annotators/biomedical/`).  
```     
      annotators/
      └── biomedical/
            ├── init.py
            ├── annotator.py
            └── resources/
                  └── setting.json
```
2. Implement the following files inside the newly added folder:  
   - `__init__.py` – to register the annotator.  
   - `annotator.py` 
            - defines the `_predict_entity(text: List[str]) -> List[Dict]` function returning entities.  
            - defines the `_predict_relation(text: List[str]) -> List[Dict]` function returning relations.  
            - defines the `annotate(text: List[str]) -> Tuple(List[Dict],List[Dict])` function returning entities and relations.  
            - The input of each function is a list of paragraphs or sentences. 
            - The Dict in output of all 3 function must follow the format below:
      ```
                  {
                        "text": <content of the single input paragraph/sentence>,
                        "entities":[
                              [
                                    "T#" <ID of entity>,
                                    <Entity type>,
                                    [
                                          [
                                                <Start position>,
                                                <End position>,
                                          ]
                                    ],
                                    <Comment about the entity>,
                                    <Plain text of the entity>
                              ]
                        ],
                        "relations":[
                              [
                                    "R#" <ID of the relation>,
                                    <Relation type>,
                                    [
                                          [
                                                <role of the first argument>,
                                                <ID of the first argument>
                                          ],
                                          [
                                                <role of the second argument>,
                                                <ID of the second argument>
                                          ]
                                    ]
                              ]
                        ]
                  }
      ```
            - The ID of an entity must have the format "T#" where # is a natural number.
            - The ID of a relation must have the format "R#" where # is a natural number.
   - `resources/setting.json` – schema definition (entity/relation types).  
            - The setting must have structure below:
      ```
                  {
                        "domain": "biomedical", # the name of domain
                        "setting": {
                              "entity_types": [ # define of entity types and color of each entity on the UI
                                    { 
                                          "type": "DISEASE",
                                          "labels": ["DISEASE"],
                                          "bgColor": "#ff6b6b",
                                          "borderColor": "darken" 
                                    },
                                    { 
                                          "type": "CHEMICAL",
                                          "labels": ["CHEMICAL"],
                                          "bgColor": "#1e90ff",
                                          "borderColor": "darken" 
                                    },
                                    
                              ],
                              "relation_types": [ # define of relation types
                                    {
                                          "type": "CID",
                                          "labels": ["CID"],
                                          "dashArray": "3,3",
                                          "color": "black",
                                          "args": [
                                                { "role": "Arg1", "targets": ["DISEASE"] },
                                                { "role": "Arg2", "targets": ["CHEMICAL"] }
                                          ]
                                    }
                              ]
                        }
                  }
      ```
3. Add the new annotator to the backend `configs/annotators.yaml`.  
      The new information of annotator added to file `configs/annotators.yaml` must have the format below:   
```
      - domain: biomedical      # match the domain field in file `annotators/biomedical/resources/setting.json`
        module: annotators.biomedical.annotator    # path of file that define the function `annotate`
        class: BiomedicalAnnotator                 # name of the class of the newly added annotator
        enabled: true           
        kwargs: {}
```


4. Restart the backend server and Celery worker.  

Your annotator will now be available as part of the pipeline, and the frontend will automatically display results according to the schema.


## Supported Domains and Results

Currently supported domains are:  

### Biomedical domain
#### Dataset:
Named Entity Recognition (NER)
- [ACE 20042](https://catalog.ldc.upenn.edu/LDC2005T09)
- [ACE 20053](https://catalog.ldc.upenn.edu/LDC2006T06)
- [GENIA](https://academic.oup.com/bioinformatics/article/19/suppl_1/i180/227927)

Entity Disambiguation Retrieval (ED Retrieval)
- MeSH 2015

Document-level Relation Extraction
- DocRE
#### Method:
- Named Entity Recognition (NER): Biaffine-NER [(Yu et al., 2020)](https://aclanthology.org/2020.acl-main.577/), Span-based BERT model using biaffine scoring
- Document-level Relation Extraction (DocRE): ATLOP [(Zhou et al., 2021)](https://ojs.aaai.org/index.php/AAAI/article/view/17717) BERT-based model for DocRE

#### Performance
| Component | F1 Score | Dataset |
|-----------|----------|---------|
| NER | 93.5 | CoNLL-2003 (English) |
|     | 91.3 | OntoNotes |
|     | 85.4 | ACE2005 (nested NER) |
|     | 80.5 | GENIA |
| DocRE | 63.4 | DocRED (general domain) |

### Legal domain
#### Dataset:
- publish in the paper "[Named Entity Recognition in Indian court judgments](https://aclanthology.org/2022.nllp-1.15/)"

#### Method:
- Baseline model was trained using spacy-transformers. Detail of model is shown in [https://github.com/Legal-NLP-EkStep/legal_NER ](https://github.com/Legal-NLP-EkStep/legal_NER)

#### Result:
| Component | F1 Score |
|-----------|----------|
| NER | 91.076 | 
---

🚀 With Docora backend, researchers can integrate domain-specific knowledge extraction pipelines while benefiting from a unified frontend for annotation and visualization.


## License

Distributed under the **MIT License**. See [`LICENSE`](./LICENSE) for details.  
