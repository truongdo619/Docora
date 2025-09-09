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

1. Create a new folder under `annotators/` (e.g., `annotators/chemistry/`).  
2. Implement the following files:  
   - `__init__.py` – to register the annotator.  
   - `inference.py` – defines the `annotate(text: str) -> dict` function returning entities and relations.  
   - `config.json` – schema definition (entity/relation types).  
3. Add the new annotator to the backend `config/settings.json`.  
4. Restart the backend server and Celery worker.  

Your annotator will now be available as part of the pipeline, and the frontend will automatically display results according to the schema.


## Supported Domains and Results

Currently supported domains are:  

| Domain     | Dataset / Model | F1 Score (NER) | Notes |
|------------|-----------------|----------------|-------|
| **Material**   | PolyNERE (LREC 2024) | ~81.2 | Strong coverage for polymers, materials entities |
| **Biomedical** | SciERC / PubMed subset | ~79.5 | Robust for biomedical named entities and relations |
| **Legal**      | COLIEE corpus | ~76.0 | Focused on case law entities and legal terms |

---

🚀 With Docora backend, researchers can integrate domain-specific knowledge extraction pipelines while benefiting from a unified frontend for annotation and visualization.


## License

Distributed under the **MIT License**. See [`LICENSE`](./LICENSE) for details.  
