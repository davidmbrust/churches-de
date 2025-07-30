# Churches in Germany – Streamlit Visualization

This Streamlit application visualises the density of Christian churches across Germany on an interactive globe using the [H3 hexagonal grid system](https://h3geo.org/) and data from **OpenStreetMap**.

---

## Data Source

* **OpenStreetMap (OSM)** – Church locations are downloaded live at runtime via the Overpass API with the following query:
  ```
  area["ISO3166-1"="DE"][admin_level=2]->.searchArea;
  (
    node["amenity"="place_of_worship"]["religion"="christian"](area.searchArea);
  );
  out center;
  ```
  * Licence: © OpenStreetMap contributors, ODbL 1.0.
* **H3 indexing** – Each church coordinate is converted to an H3 cell ID (resolution selectable in the UI) allowing you to aggregate counts per hexagon.

No data are stored permanently; everything is requested on-the-fly and cached in memory for the current Streamlit session.

---

## Features

* Heatmap or 3-D stacked pillars to show the number of churches per hexagon.
* Adjustable H3 resolution (3-5), opacity, and view controls.
* CSV download of the aggregated dataset.

---

## Quick Start

1. **Clone & install dependencies**
   ```bash
   git clone https://github.com/<YOUR-USERNAME>/churches-de.git
   cd churches-de
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Run the app**
   ```bash
   streamlit run app.py
   ```
3. Open `http://localhost:8501` in your browser and explore!

---

## Deployment

The app can be deployed to Streamlit Cloud, Netlify (via Streamlit-Static), or any container platform. Ensure outbound HTTPS access is allowed so the Overpass API call succeeds.

---

## Repository Structure

```
├── app.py              # Streamlit application
├── requirements.txt    # Python dependencies
├── README.md           # This file
└── .gitignore
```

---

## Licence

This repository is released under the MIT License. OSM data is © OpenStreetMap contributors and licensed under ODbL 1.0.
