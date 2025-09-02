# Result Visualization

After Docora finishes processing a PDF, click on the title of processed document, the **Result Page** will appear. This view combines an `entity‑highlighted PDF`, an interactive `sidebar`, and a `settings panel` so you can explore, filter, and export your annotations with ease.

---

## 1. Result Page Layout  

| Area | Purpose |
|------|---------|
| **Entity‑Highlighted PDF** | Shows the original pages with every entity type color‑coded. Hovering reveals a tooltip; clicking opens detail views. |
| **Sidebar** | Lists entities, relations, and paragraphs. Selecting an item scrolls the PDF to its location and opens the detail card. |
| **Settings Bar** | Provides global actions: save a checkpoint, download results, switch between modes (Entity / Relation / Paragraph), and apply filters. |

<figure style="width:100%;margin:1.25rem auto;text-align:center;">
  <img src="./src/DocsPage/photos/visualization.drawio.png"
       alt="Sign Up dialog"
       style="width:100%;border-radius:6px;" />
  <figcaption><em>Figure 1 — Result Page Layout</em></figcaption>
</figure>


### 1.1 Entity‑Highlighted PDF  

* Each entity category (e.g., **POLYMER**, **PROP_VALUE**) is rendered in a unique color.  
* Clicking a highlight synchronises the sidebar and opens advanced visualisations (see below).

### 1.2 Sidebar  

* **Entity List** — paginated cards showing entity text, page number, and quick‑action icons (edit, favourite).  
* **Relation Tree** — collapsible view of relations grouped by sentence or paragraph.  
* **Paragraphs Tab** — displays raw text blocks for context or editing.

### 1.3 Settings Bar  

* **Save Checkpoint** — store the current annotation state.  
* **Download Result** — open the export result (JSON).  
* **Mode Switcher** — toggles the sidebar between *Entity*, *Relation*, and *Paragraph* detail (see the *Change Mode* section).  
* **Filter Icon** — launch advanced filtering (by type, confidence, page range).

---

## 2. Advanced Visualization  

Docora offers two deeper inspection tools for analysing complex relationships.

### 2.1 BRAT‑Styled View  

<figure style="width:100%;margin:1.25rem auto;text-align:center;">
  <img src="./src/DocsPage/photos/brat_styled.png"
       alt="Sign Up dialog"
       style="width:100%;border:1px solid #ddd;border-radius:6px;" />
  <figcaption><em>Figure 2 — BRAT‑styled popup</em></figcaption>
</figure>


* Click any highlight in the PDF **or** any entity card in the sidebar to open `Brat Visualization` dialog.  
* A popup appears with a BRAT‑style diagram of the selected entity and its immediate relations.  
* Press **Show All Entities** to render the entire paragraph in BRAT format for full‑context review.

### 2.2 Graph View  

<figure style="width:100%;margin:1.25rem auto;text-align:center;">
  <img src="./src/DocsPage/photos/graph_visualization.png"
       alt="Graph Visualization"
       style="width:100%;border:1px solid #ddd;border-radius:6px;" />
  <figcaption><em>Figure 3 — Graph Visualization</em></figcaption>
</figure>

* Accessible from the same popup via the **Open Graph Visualization** button.  
* Displays a network graph centred on the selected entity.  
* Nodes = `entities`, edges = `relations`.  
* Both direct and indirect connections are shown, helping you trace multi‑step relationships at a glance.

---

## 3. Change Mode  

Use the **Mode Switcher** in the settings bar to tailor the sidebar to your current task:

* **Entity Mode** —  The default view that lists individual entities along with associated details such as _their position and related relations._ 

<figure style="width:100%;margin:1.25rem auto;text-align:center;">
  <img src="./src/DocsPage/photos/entity_mode.jpeg"
       alt="Graph Visualization"
       style="width:100%;border:1px solid #ddd;border-radius:6px;" />
  <figcaption><em>Figure 4 — Entity Mode</em></figcaption>
</figure>


* **Relation Mode** — Displays entities that are part of at least one relationship, helping to focus on connected information.

<figure style="width:100%;margin:1.25rem auto;text-align:center;">
  <img src="./src/DocsPage/photos/relation_mode.jpeg"
       alt="Graph Visualization"
       style="width:100%;border:1px solid #ddd;border-radius:6px;" />
  <figcaption><em>Figure 5 — Relation Mode</em></figcaption>
</figure>


* **Paragraph Mode** — Organizes content by paragraph, allowing for easier bulk editing or readability checks.

<figure style="width:100%;margin:1.25rem auto;text-align:center;">
  <img src="./src/DocsPage/photos/paragraph_mode.jpeg"
       alt="Graph Visualization"
       style="width:100%;border:1px solid #ddd;border-radius:6px;" />
  <figcaption><em>Figure 6 — Paragraph Mode</em></figcaption>
</figure>



> **Tip:** The filter icon works in sync with the selected mode, enabling precise control over what appears in both the PDF and the sidebar.
