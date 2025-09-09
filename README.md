# Docora

**Docora** is a domain-agnostic system for interactive knowledge extraction and visualization from scientific PDFs.  
It integrates **backend** (API, parsing, automated annotation) and **frontend** (interactive web interface) into a unified platform.

---

## Table of Contents
1. [Project Overview](#project-overview)  
2. [Project Structure](#project-structure)  
3. [Getting Started](#getting-started)  
   - [Backend](#backend)  
   - [Frontend](#frontend)  
4. [Demo Video](#demo-video)  
5. [License](#license)  
6. [Contact](#contact)  

---

## Project Overview

Docora bridges the gap between PDF parsing tools and annotation platforms by providing:  
- **PDF-aware parsing** with layout + text extraction.  
- **Automated annotation assistance** (rule-based, Transformer-based, or LLM-based extractors).  
- **Domain-agnostic schemas** for entities and relations.  
- **Multi-view visualization** (PDF highlights, Brat-style text view, graph view).  
- **Interactive editing and refinement** with immediate synchronization across all views.  

The system is designed for researchers and practitioners who need efficient creation of high-quality annotated corpora.

---

## Project Structure

```text
.
├── backend/         # FastAPI backend for parsing, annotations, storage (PostgreSQL, Celery)
├── web_interface/   # React + MUI frontend for annotation and visualization
├── LICENSE
└── README.md        # This file
```

- **`backend/`** – Handles PDF parsing, automated annotation, REST APIs, and database management.  
- **`web_interface/`** – Provides the interactive React-based frontend. (See its own README for details).  

---

## Getting Started

### Backend

For detailed instructions on installation, configuration, and running the backend server, see the [backend README](backend/README.md).  

### Frontend

For instructions on running the web interface (React + Vite), see the [web_interface README](web_interface/README.md).  

---

## Demo Video

▶️ Watch the Docora demo: [https://www.youtube.com/watch?v=DpWW2ey5qOY](https://www.youtube.com/watch?v=DpWW2ey5qOY)

---

## License

This project is distributed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

## Contact

For questions or feedback, please contact:  

📧 Truong Do – [truongdo@jaist.ac.jp](mailto:truongdo@jaist.ac.jp)  

✨ Project Website: [https://www.jaist.ac.jp/is/labs/nguyen-lab/systems/docora](https://www.jaist.ac.jp/is/labs/nguyen-lab/systems/docora)
