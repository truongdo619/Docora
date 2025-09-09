
# Named Entity Recognition (NER) Models for the Materials Science Domain <!-- omit in toc -->

The **Named Entity Recognition (NER)** system identifies and classifies entity mentions within scientific texts in the materials science domain.  
This project adapts the approach from the [W2NER paper](https://github.com/ljynlp/W2NER) and uses the [PolyNERE](https://aclanthology.org/2024.lrec-main.1126/) corpus for training.  
This repository focuses on detailed instructions for performing inference.

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Environment Setup](#environment-setup)
3. [Download Pretrained Models](#download-pretrained-models)
4. [Inference Instructions](#inference-instructions)
5. [Docker Setup for Celery and PostgreSQL](#docker-setup-for-celery-and-postgresql)
6. [Running the System](#running-the-system)

---

## Project Overview

The system uses pretrained NER models specialized for materials science text extraction.  
It requires a running Stanford CoreNLP server for sentence splitting and tokenization during inference.

---

## Environment Setup

```bash
conda create --name py38_W2NER-main python=3.8
conda activate py38_W2NER-main

conda install pytorch==1.10.0 torchvision torchaudio cudatoolkit=11.3 -c pytorch
pip install numpy==1.20.0 gensim==4.1.2 transformers==4.13.0 pandas==1.3.4 scikit-learn==1.0.1 prettytable==2.4.0
pip install opt-einsum==3.3.0 ujson
pip install fastapi uvicorn
git clone https://github.com/cat-lemonade/PDFDataExtractor
cd PDFDataExtractor
cd ..
python setup.py install
# pip install chemdataextractor pymupdf
pip install pymupdf pycorenlp ipdb
pip install "celery[redis,amqp]" sqlalchemy psycopg2-binary
pip install passlib python-jose
pip install -U "magic-pdf[full]"
pip install python-multipart
```

## Download Pretrained Models

Navigate to the `PDF` directory.  
A pretrained NER model is required for inference.

Download it from this [URL](https://drive.google.com/drive/folders/1dsoae6AOPXOV0tLwK3t2gya6Sf7Zi6rd?usp=sharing) and place the model files inside the `./NER` folder.

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
