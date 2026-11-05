# 🌿 TaxonMap Pro

**Publication-Ready Taxonomy Map Studio for Indian Flora & Fauna**  
*100% Survey of India (SOI) Political Boundary Compliant | Camera-Ready 300 DPI, Vector SVG & PDF Output*

🌐 **Live Web Application (GitHub Pages):**  
👉 **[https://sureshmagnolia.github.io/taxonmapmaker/](https://sureshmagnolia.github.io/taxonmapmaker/)**

---

## 🌟 Overview

Taxonomic publications in premier botany and zoology journals (*Phytotaxa*, *Rheedea*, *Taxon*, *Kew Bulletin*, *Nordic Journal of Botany*, *Zootaxa*) require high-resolution distribution maps with clear topography, precise coordinates, and proper typification symbology. 

For studies within the Indian subcontinent, maps **must strictly comply with official Survey of India (SOI) political boundaries** (correct depiction of the Union Territory of Ladakh including Aksai Chin, the Union Territory of Jammu & Kashmir, and Arunachal Pradesh).

**TaxonMap Pro** provides an intuitive, web-based and desktop studio where taxonomists can generate publication-grade distribution maps in seconds—without touching complex GIS software.

---

## 🚀 Key Features

* **Multi-Taxa Support (1 to Many Plants):**
  * Manage multiple species or populations simultaneously.
  * Assign distinct colors and scientific marker symbols per taxon:
    * ★ Star | ▲ Triangle | ● Circle | ■ Square | ◆ Diamond | ✚ Cross
  * Record specimen typification status: **Holotype**, **Isotype**, **Paratype**, **Lectotype**, **Syntype**, **Topotype**, or **Voucher**.
* **Flexible Coordinate Input:**
  * **Decimal Degrees:** `11.4100°N, 76.7000°E` or `11.4100, 76.7000`
  * **Degrees Minutes Seconds (DMS):** `11°46'31.1"N 78°12'33.5"E`
  * Instant automatic conversion between DMS and Decimal Degrees.
* **Interactive Waypoint Pin Dropper:**
  * Click directly on the interactive map to place a collection waypoint.
  * Drag and reposition markers with live coordinate and elevation updates.
* **5 Cartographic Elevation Themes:**
  1. **Phytotaxa Standard:** Verdant coastal green ($0\text{--}100\text{ m}$) $\rightarrow$ ochre midlands $\rightarrow$ amber/sienna $\rightarrow$ montane burnt umber ($1500\text{--}2695\text{ m}$).
  2. **Nordic Monochromatic:** Calibrated grayscale for black-and-white print editions.
  3. **Swiss Alpine Shaded Relief:** Sunlit northwestern aspects with cool shadow accents.
  4. **Coromandel & Deccan Warm:** Earthy buff, terracotta, and olive hues.
  5. **Clean Minimalist:** Vector topography with soft contours.
* **Granular Layer Controls:**
  * Toggle **Water bodies & Rivers** on/off.
  * Toggle **Official Survey of India national boundary** (252,604-vertex precision).
  * Toggle **State / UT boundaries** (36 Indian States and UTs).
  * Toggle **Smooth Sri Lanka coastline** (10m high-resolution vector).
  * Toggle **Western Ghats mountain landmarks** (Nilgiris, Anamalais, Salem Gap).
  * Toggle **District boundaries** and highlight collection districts (e.g. Nilgiris, Salem).
* **Survey of India (SOI) National Inset Map:**
  * Toggle **On / Off**.
  * Customizable position: **Top-Right**, **Top-Left**, **Bottom-Right**, or **Bottom-Left**.
  * Dynamic red bounding box automatically tracking your collection extent.
* **Camera-Ready Publication Export:**
  * **300 DPI PNG** for manuscript figures.
  * **Vector SVG** with editable text paths for Adobe Illustrator / Inkscape.
  * **Vector PDF** with embedded TrueType fonts.
  * **Auto-Generated Figure Caption** formatted according to *Phytotaxa / Rheedea* style.
  * **Specimen Data Export (CSV / JSON)**.

---

## 💻 Local Desktop Setup (Python / Streamlit)

If you prefer running the Python studio locally with offline SRTM/GMTED DEM rendering:

### 1. Requirements
Ensure Python 3.10+ is installed:
```bash
pip install -r requirements.txt
```

### 2. Launching the Studio
On Windows, double-click:
```text
run_taxonmap.bat
```
Or run from your terminal:
```bash
streamlit run app.py
```
The studio will automatically open in your default browser at `http://localhost:8501`.

---

## 📁 Repository Structure

```text
D:\TaxonMapmaker\
├── index.html                   # Static web app for GitHub Pages
├── app.py                       # Python Streamlit studio application
├── run_taxonmap.bat             # One-click Windows desktop launcher
├── requirements.txt             # Python dependencies
├── .nojekyll                    # GitHub Pages asset serving flag
├── .github/
│   └── workflows/
│       └── deploy.yml           # Automated GitHub Pages CI/CD workflow
├── assets/
│   └── geojson/                 # High-resolution web vector layers
│       ├── india_soi_boundary.geojson
│       ├── india_states.geojson
│       ├── sri_lanka.geojson
│       └── rivers_india.geojson
├── data/                        # GIS & DEM processing datasets
│   ├── india-composite.geojson  # 252k-vertex Survey of India boundary
│   ├── india_states_clean.geojson
│   └── india_states_soi.geojson
└── figures/                     # Publication figures & outputs (PNG, SVG, PDF)
```

---

## 📜 Survey of India (SOI) Compliance Note

All national boundaries and administrative delineations strictly adhere to the official guidelines issued by the **Survey of India, Department of Science & Technology, Government of India**. The Union Territory of Ladakh (including Aksai Chin and Pakistan-administered Kashmir), Jammu & Kashmir, and Arunachal Pradesh are depicted completely and accurately within the sovereign territory of the Republic of India.

---

## ⚖️ License

Distributed under the **MIT License**. Free for academic, scientific, and taxonomic research publications.

