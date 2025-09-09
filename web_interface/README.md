# Docora Frontend <!-- omit in toc -->

The **Docora Frontend** is a modular React-based application for parsing, annotating, and visualizing knowledge directly from scientific PDFs.  
It supports **domain-agnostic schemas**, automated annotation assistance, and synchronized multi-view visualizations (PDF, text, and graph).  

---

## Table of Contents
1. [Project Structure](#project-structure)  
2. [Key Techniques & Libraries](#key-techniques--libraries)  
3. [Installation](#installation)  
4. [Running Locally](#running-locally)  
5. [Building for Production](#building-for-production)  
6. [Typed API Docs](#typed-api-docs)  
7. [License](#license)  

---

## Project Structure

```text
.
├── src/
│   ├── pdf_highlighter/   # Reusable PDF highlighting/annotation module
│   └── ...                # Main React frontend source (components, views, state)
├── dist/                  # Build artifacts (ESM + CJS)
├── public/                # Static assets (docs, icons, etc.)
├── package.json           # Project metadata and scripts
├── tsconfig.json          # TypeScript configuration
└── vite.config.ts         # Vite build configuration
```

### Directory Notes
- **`src/pdf_highlighter/`** – Independent NPM-ready module for precise PDF text positioning and overlays.  
- **`src/`** – Main React frontend for annotation, visualization, and schema-based workflows.  
- **`dist/`** – Output directory created by `npm run build`.  

---

## Key Techniques & Libraries

| Area | Highlights |
|------|------------|
| **PDF Parsing & Rendering** | [`pdfjs-dist`](https://github.com/mozilla/pdfjs-dist) for rendering; backend integration with [`PyMuPDF`](https://pymupdf.readthedocs.io). |
| **Automated Annotations** | Rule-based, Transformer-based, or LLM-based extractors integrated via backend API. |
| **Multi-View Visualization** | PDF highlights, Brat-style text view, and interactive graphs with [`reactflow`](https://reactflow.dev/). |
| **Annotation UI** | Drag-and-drop with [`react-beautiful-dnd`](https://github.com/atlassian/react-beautiful-dnd) and resizing with [`react-rnd`](https://github.com/bokuweb/react-rnd). |
| **Tables** | Metadata browsing with MUI X [`DataGridPro`](https://mui.com/x/react-data-grid/). |
| **State Management** | React Context + Reducers with dynamic schema configuration. |
| **Build Tools & Docs** | Built with **Vite 4** for fast HMR; **TypeDoc** for API docs. |

---

## Installation

```bash
# Clone the repository
git clone https://github.com/truongdo619/Docora.git
cd Docora

# Install dependencies
npm install
```

---

## Running Locally

1. **Configure API Endpoints**

   ```bash
   cp .env.example .env
   # Edit the .env file to set VITE_BACKEND_URL and VITE_PDF_BACKEND_URL
   ```

2. **Start Development Server**

   ```bash
   npm start  # runs vite dev server
   ```

   Open <http://localhost:3001> in your browser for live development with hot reload.

---

## Building for Production

```bash
npm run build
```

- Bundled frontend assets appear in `dist/`.  

To clean build artifacts and docs:

```bash
npm run clean
```

---

## Typed API Docs

Generate TypeScript API documentation (e.g., for `src/pdf_highlighter`):

```bash
npm run build:docs
```

Docs are generated in `public/docs` and can be hosted on any static server.

---

## License

Distributed under the **MIT License**. See [`LICENSE`](./LICENSE) for details.  

---

✨ **Docora Website:** [https://www.jaist.ac.jp/is/labs/nguyen-lab/systems/docora](https://www.jaist.ac.jp/is/labs/nguyen-lab/systems/docora)
