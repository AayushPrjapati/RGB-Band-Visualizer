# 🛰️ RGB & Band Image Visualizer

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://band-visualizer.streamlit.app)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A professional web-based and desktop tool for multi-band satellite imagery analysis. Built specifically for **Sentinel-2**, **Landsat-8**, and generic multi-band GeoTIFFs, this tool allows for intuitive RGB compositing, spectral index calculation, and radiometric exploration.

---

## 🌟 Key Features

* **🎨 Custom RGB Compositing:** Assign any specific satellite band to Red, Green, or Blue channels to visualize custom band combinations.
* **🌿 Built-in Spectral Indices:** Instantly apply pre-configured filters like NDVI (Normalized Difference Vegetation Index), SAVI, EVI, Water Bodies highlight, and Urban/Soil composites.
* **🌈 Color Space Transforms:** View single bands or multi-band combinations in RGB, HSV, LAB, HLS, YCrCb, or Grayscale.
* **📈 Radiometric Histograms:** Per-band pixel intensity distribution charts for radiometric analysis.
* **⚙️ Real-time Adjustments:** Tweak brightness, contrast, and sharpness dynamically.
* **🚀 Ready-to-use Samples:** Includes real bundled Landsat 8 sample scenes to test the tool instantly without downloading large datasets.

## 🚀 Live Web Application

The easiest way to use the visualizer is via the live Streamlit cloud deployment.

👉 **[Launch RGB & Band Visualizer](https://band-visualizer.streamlit.app)**

## 💻 Local Installation

If you prefer to run the application locally or work with massive, high-resolution TIFF files that exceed cloud limits, follow these steps:

### 1. Clone the repository
```bash
git clone https://github.com/AayushPrjapati/RGB-Band-Visualizer.git
cd RGB-Band-Visualizer
```

### 2. Install dependencies
Ensure you have Python installed, then run:
```bash
pip install -r requirements.txt
```
*(Note: Windows users may need to install GDAL/rasterio binaries via conda if pip fails)*

### 3. Run the web app locally
```bash
streamlit run app.py
```

## 📁 Repository Structure

* `app.py` — The main Streamlit web application.
* `samples/` — Bundled multi-band sample GeoTIFFs (Landsat 8) for quick testing.
* `desktop_app_source/` — Legacy PyQt5 desktop application source code prototypes.
* `requirements.txt` — Python dependencies for the Streamlit app.
* `packages.txt` — System-level dependencies (GDAL) required for Streamlit Cloud deployment.

## 🛠️ Built With
* [Streamlit](https://streamlit.io/) - The web framework
* [Rasterio](https://rasterio.readthedocs.io/) - Geospatial data processing
* [OpenCV](https://opencv.org/) - Computer Vision & Color Spaces
* [Matplotlib](https://matplotlib.org/) - Data visualization & Histograms
* [Pillow (PIL)](https://pillow.readthedocs.io/) - Image rendering
