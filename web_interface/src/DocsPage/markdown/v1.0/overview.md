---
title: Overview
---

# Docora – Overview

<p class="description">
Docora is a web-based, domain-agnostic system that **automatically extracts, visualizes, and lets you refine scientific entities and their relationships directly on PDFs**. By combining configurable NER/RE extractors with synchronized multi-view visualizations, Docora unifies what used to be fragmented annotation workflows into a seamless, interactive experience.
</p>

## Introduction

Scientific PDFs contain rich domain knowledge but remain difficult to transform into structured datasets due to fragmented pipelines that separate parsing, annotation, and visualization. Docora addresses this challenge by  

* parsing PDFs with [PyMuPDF](https://pymupdf.readthedocs.io/en/latest/) and [MinerU](https://github.com/opendatalab/MinerU) to preserve layout fidelity,  
* generating **automatic annotation suggestions** using rule-based, model-based, or LLM-based extractors depending on the domain, and  
* presenting results in synchronized PDF, text, and graph views where users can verify and refine annotations interactively.  

This flexibility allows Docora to adapt to diverse domains, from materials science and biomedical research to legal text analysis.

## Advantages of Docora

- **Domain flexibility** – Configurable schemas let researchers define entities and relations for any field.  
- **Faster annotation** – Users refine automatically generated annotations rather than starting from scratch.  
- **Multi-view visualization** – PDF highlights, text-based Brat-style view, and graph networks remain fully synchronized.  
- **Interactive editing** – Rich tools for correcting entity spans, labels, and relations directly on the PDF canvas.  
- **Seamless exports** – Results can be saved as structured JSON for machine use or annotated PDFs for human review.  

## Docora vs. Traditional Annotation Tools

| Feature | Doccano / Brat / INCEpTION | Grobid | **Docora** |
|---------|-----------------------------|--------|----------------|
| Works directly on PDFs | ✗ | ✔ | **✔** |
| Provides semantic annotation | ✔ (text only) | ✗ | **✔** |
| Integrated visualization | Basic | ✗ | **✔ (multi-view)** |
| Domain-configurable schemas | Limited | ✗ | **✔** |
| Automatic suggestions (rule / model / LLM) | ✗ | ✗ | **✔** |
| Open-source extensibility | ✔ | ✔ | **✔** |

## Citation

If you use this system, please cite:

```
@inproceedings{do2026docora,
  title={Docora: A Domain-Agnostic System for Interactive Knowledge Extraction and Visualization from Scientific PDFs},
  author={Do, Truong Dinh and Trieu, An Hoang and Phi, Van-Thuy and Le Nguyen, Minh and Matsumoto, Yuji},
  booktitle={Proceedings of the AAAI Conference on Artificial Intelligence},
  year={2026}
}
```

## Contact Support

For questions or assistance, please reach out to our support team:

- **Email:** [truongdo@jaist.ac.jp](mailto:truongdo@jaist.ac.jp)  
