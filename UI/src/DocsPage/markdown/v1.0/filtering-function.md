<!-- ­–––––––––––––––––––––––––––––––––––––––––––––––––––––––––– -->
# Filtering Results
Focus on the information you need by limiting the viewer to a subset of **entities** or **relations**.  
<!-- ­–––––––––––––––––––––––––––––––––––––––––––––––––––––––––– -->

---

## 1. Quick Entity Filter

Click any entity type in the **setting bar**. The PDF instantly refreshes to display only that category.

<figure style="width:100%;margin:1rem auto;text-align:center;">
  <img src="./src/DocsPage/photos/filter_entity.jpeg"
       alt="Entity list in the sidebar"
       style="width:100%;border:1px solid #ddd;border-radius:6px;" />
  <figcaption><em>Figure 1 — Entity categories in the sidebar</em></figcaption>
</figure>

---

## 2. Advanced Filter Dialog

Need more granular control? Use the filter toolbar `icon`.

<figure style="width:100%;margin:1rem auto;text-align:center;">
  <img src="./src/DocsPage/photos/filter_icon.jpeg"
       alt="Filter icon in toolbar"
       style="width:100%;border:1px solid #ddd;border-radius:6px;" />
  <figcaption><em>Figure 2 — Filter icon in the PDF toolbar</em></figcaption>
</figure>

Clicking the icon opens a `dialog` where you can:

| Option | Description |
|--------|-------------|
| **Entity Type** | Choose one or more entity categories (e.g., *Polymer*, *Prop_name*, *Condition*). |
| **Relation Type** | Restrict to specific relationships (e.g., *has_property*, *has_condition*). |


<figure style="width:55%;margin:1rem auto;text-align:center;">
  <img src="./src/DocsPage/photos/filter_dialog.png"
       alt="Advanced filter dialog"
       style="width:100%;border:1px solid #ddd;border-radius:6px;" />
  <figcaption><em>Figure 3 — Advanced filter dialog</em></figcaption>
</figure>

Press **Apply** to update the viewer; the active filter badge in the toolbar shows the number of rules currently in effect.

---

## 3. Resetting Filters

Click the **All Entity Types** button in the sidebar to clear all filters and return to the full annotation view.

---

### Why Filter?

* **Reduce visual clutter** when working with densely annotated pages.  
* **Speed up validation** by isolating one entity class at a time.  
* **Spot model errors** quickly—e.g., filter to *Prop_name* entities to check unit consistency.  

Filtering is non‑destructive: it only changes what you see, never the underlying annotations.
