<!-- ­–––––––––––––––––––––––––––––––––––––––––––––––––––––––––– -->
# Quick‑Start Guide
Learn the basics of working with **Docora.**  
<!-- ­–––––––––––––––––––––––––––––––––––––––––––––––––––––––––– -->

---

## 1. Sign In
<p style='text-align: justify;'> To access the Docora system, you must first sign in with a valid account. Visit the [Sign-in](https://www.jaist.ac.jp/is/labs/nguyen-lab/systems/polyminder/#/signin) page, enter your username and password, and press **Sign In**.  If you have not have an account, choose [Sign Up](https://www.jaist.ac.jp/is/labs/nguyen-lab/systems/polyminder/#/signup), complete the registration form, and then return to the sign‑in page. </p>


<figure style="width:100%;margin:1.5rem auto;text-align:center;">
  <img src="./src/DocsPage/photos/signin_page.png" alt="Docora sign‑in screen" style="width:100%;border:1px solid #e0e0e0;border-radius:6px;" />
  <figcaption><em>Figure 1 — Sign‑in interface</em></figcaption>
</figure>


## 2. End‑to‑End Annotation Workflow

<!-- <p style='text-align: justify;'> After signing in, upload a PDF through the web interface. Docora `parses` the document, runs its `NER & RE models`, and overlays the `predicted entities and relations` directly on the original pages. You may then `verify` or `refine` each annotation and finally download a clean, fully annotated PDF. </p> -->


<p style='text-align: justify;'> Once signed in, you can begin annotating documents. The core workflow in Docora follows these steps:</p> 

| Step | Action | System Response |
|------|--------|-----------------|
| 1 | Users **upload** one or more PDF files. | Files are queued for processing. |
| 2 | Docora **parses** each document and runs **NER & RE** models. | Entities and relations are extracted. |
| 3 | The system **overlays** predictions on the PDF. | An interactive result page is generated. |
| 4 | Users **verify / refine** annotations and **download** the final annotation. | Clean, high‑quality annotations are saved. |

---

## 3. Manage Your Documents

<p style='text-align: justify;'> Click on **Documents** in the top navigation bar to access the management dashboard. Here, you can view all uploaded files along with their current processing status, and perform actions like renaming, deleting, or downloading the annotated results. </p>

<figure style="width:100%;margin:1.5rem auto;text-align:center;">
  <img src="./src/DocsPage/photos/document_page.png" alt="Document management page" style="width:100%;border:1px solid #e0e0e0;border-radius:6px;" />
  <figcaption><em>Figure 3 — Document management console</em></figcaption>
</figure>

---

## 4. Refine Annotations

<p style='text-align: justify;'> Click on any **processed document** to open the interactive results viewer. You can use inline tools to edit or add entities and relationships. All changes are automatically saved and can be revisited at any time. </p>

<figure style="width:100%;margin:1.5rem auto;text-align:center;">
  <img src="./src/DocsPage/photos/Result.PNG" alt="Result viewer with inline editing" style="width:100%;border:1px solid #e0e0e0;border-radius:6px;" />
  <figcaption><em>Figure 4 — Interactive result viewer</em></figcaption>
</figure>

