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

Currently, the system supports the following domains:

### Material Domain

#### Supported Entity Types
We adopt the **PolyNERE ontology** for materials science, with 14 entity types covering polymers, related materials, properties, experimental settings, and references.  

| Entity Type       | Definition | Example |
|-------------------|------------|---------|
| **POLYMER**       | Material entities that are polymers. | “Sulfonated poly(phthalazinone ether ketone nitrile)”, “polyethylene” |
| **POLYMER_FAMILY**| A class of polymers. | “bio-polyimides”, “PIs”, “epoxy”, “poly(amic acid)s”, “polyanhydride” |
| **PROP_NAME**     | Specific material property names. | “ion conductivity”, “power density”, “glass transition temperature” |
| **PROP_VALUE**    | Numeric value + unit of a property. | “9400 g/mol”, “<16 wt%”, “>100,000 g/mol” |
| **MONOMER**       | Repeat units of a polymer. | “N-isopropylacrylamide”, “4,4′-bisphenol” |
| **ORGANIC**       | Organic materials (non-polymers). | “hydroxy urea”, “divinyl benzene”, “maleic acid”, “PFSA” |
| **INORGANIC**     | Inorganic materials, often additives. | “Ag”, “indium(III) oxide”, “In₂O₃” |
| **MATERIAL_AMOUNT** | Amount of a material in a formulation. | “90%”, “5 wt.%”, “10 mass%” |
| **COMPOSITE**     | Materials formed from multiple distinct components. | “TiO₂-DA-PEI”, “GO/PVA”, “PVdF:PEMA” |
| **OTHER_MATERIAL**| Materials not fitting other categories, including mixtures. | “anion exchange membranes”, “ethanol/water”, “porous film” |
| **CONDITION**     | Condition under which property is measured. | “at 50°C”, “using air O₂”, “between 15 and 60°C” |
| **SYN_METHOD**    | Techniques for synthesizing a material. | “ring-opening polymerization”, “radical terpolymerization” |
| **CHAR_METHOD**   | Techniques for characterizing a material. | “dynamic light scattering”, “neutron transmission measurements” |
| **REF_EXP**       | Referring expressions pointing to entities. | “They”, “this polymer”, “the resulting copolymers” |


#### Supported Relation Types
Relations define how entities connect within materials science texts.  

- **synthesized_by** → (Material_Group → Syn_Method)  
- **characterized_by** → (Material_Group → Char_Method) OR (Prop_Name → Char_Method)  
- **has_property** → (Material_Group → Prop_Name)  
- **has_value** → (Prop_Name → Prop_Value)  
- **has_amount** → (Material_Group → Material_Amount)  
- **has_condition** → (Prop_Name/Prop_Value → Condition)  
- **abbreviation_of** → (Ref_Exp → Material_Group / Prop_Name / Syn_Method / Char_Method)  
- **refers_to** → (Ref_Exp → Material_Group / Prop_Name / Syn_Method / Char_Method / Ref_Exp)  

Special cases:  
1. `has_value` is used when **Prop_Name is missing or unclear**.  
2. `has_condition` is used when **Prop_Value is missing or unclear**.  
3. `characterized_by` can also link **Material_Group** when it is missing or unclear.  


#### Methods
- **Entity Detection:**  
  We use **W2NER** ([Li et al., AAAI 2022](https://doi.org/10.1609/aaai.v36i10.21344)), a span-alignment model that handles flat, overlapped, and discontinuous mentions effectively.  

- **Relation Extraction:**  
  We adopt **ATLOP** ([Zhou et al., AAAI 2021](https://doi.org/10.1609/aaai.v35i16.17717)), a document-level RE model with adaptive thresholding and attention pooling, well-suited for cross-sentence reasoning.  

Both models are trained on the **PolyNERE corpus** (750 abstracts with 14 entity types and multiple relations).


#### Performance
Evaluation was conducted on the PolyNERE test set (75 abstracts).  

| Task                   | Method  | Encoder     | Precision | Recall | F1 Score |
|------------------------|---------|-------------|-----------|--------|----------|
| Named Entity Recognition | W2NER   | MatSciBERT | 78.05     | 76.53  | 77.28    |
| Relation Extraction      | ATLOP   | MatSciBERT | 83.99     | 82.49  | 83.23    |

---

### Biomedical Domain

#### Supported Entity Types and Relations
The biomedical domain focuses on detecting diseases, chemicals, and their relations.  
- **Entity types:** `Chemical`, `Disease`  
- **Relation types:** `Chemical-Induce-Disease`


#### Methods
- **Entity Detection:**  
  We adopt the **Span-based Biaffine-NER** approach ([Yu et al., ACL 2020](https://aclanthology.org/2020.acl-main.577/)).  
  This method employs a span-based BERT model with biaffine scoring to capture entity boundaries and labels.  

- **Relation Extraction:**  
  We use **ATLOP** ([Zhou et al., AAAI 2021](https://ojs.aaai.org/index.php/AAAI/article/view/17717)), a widely used approach for document-level relation extraction.  
  The base encoder is a BERT-based model.


#### Performance
We evaluate on the **CDR test set** ([Li et al., Database 2016](https://academic.oup.com/database/article/doi/10.1093/database/baw068/2630414)).

| Task                | Method | Precision | Recall | F1 Score |
|---------------------|--------|-----------|--------|----------|
| Relation Extraction | ATLOP  | 64.61     | 75.92  | 69.74    |

---

### Legal Domain

#### Supported Entity Types and Relations
In the legal domain, we focus on **entity detection**. Relation extraction is not currently supported. The supported entity types are listed below:

| Entity Type  | Extracted From       | Description |
|--------------|----------------------|-------------|
| **COURT**        | Preamble, Judgment | Name of the court delivering the current judgment (from Preamble) or any court mentioned (from judgment sentences). |
| **PETITIONER**   | Preamble, Judgment | Petitioners / appellants / revisionists in the current case. |
| **RESPONDENT**   | Preamble, Judgment | Respondents / defendants / opposition parties in the current case. |
| **JUDGE**        | Preamble, Judgment | Judges of the current case (from Preamble) and judges of current/previous cases (from judgment sentences). |
| **LAWYER**       | Preamble           | Lawyers representing both parties. |
| **DATE**         | Judgment           | Any date mentioned in the judgment. |
| **ORG**          | Judgment           | Organizations apart from courts, e.g., banks, PSUs, private companies, police stations, state government, etc. |
| **GPE**          | Judgment           | Geopolitical entities such as countries, states, cities, districts, and villages. |
| **STATUTE**      | Judgment           | Names of acts or laws cited in the judgment. |
| **PROVISION**    | Judgment           | Sections, sub-sections, articles, orders, or rules under a statute. |
| **PRECEDENT**    | Judgment           | Past cases cited as precedent (party names + citation or case number). |
| **CASE_NUMBER**  | Judgment           | Case numbers mentioned in the judgment (excluding precedent references). |
| **WITNESS**      | Judgment           | Names of witnesses in the current case. |
| **OTHER_PERSON** | Judgment           | Persons not classified as petitioner, respondent, judge, or witness. |

#### Methods
We use an AI model based on a **transition-based dependency parser** built on top of the `roberta-base` architecture.  
The model is trained with **spaCy-Transformers** and is available here: [opennyaiorg/en_legal_ner_trf](https://huggingface.co/opennyaiorg/en_legal_ner_trf).

#### Performance

We evaluate on the **Indian court judgment** ([Prathamesh et al., nllp 2024](https://aclanthology.org/2022.nllp-1.15.pdf)).

| Metric      | Score   |
|-------------|---------|
| **F1-Score**   | 91.08  |
| **Precision**  | 91.98  |
| **Recall**     | 90.19  |



## License

Distributed under the **MIT License**. See [`LICENSE`](./LICENSE) for details.  
