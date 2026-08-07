# RGB & Band Image Visualizer

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://band-visualizer.streamlit.app)

A web app (and older desktop version) to easily view and play around with multi-band satellite images like Sentinel-2 and Landsat-8. Instead of opening heavy GIS software just to check a TIFF file, you can upload it here to build RGB composites, calculate spectral indices, or check histograms.

## What it does

- **RGB Composites:** Pick which bands go into the Red, Green, and Blue channels.
- **Spectral Indices:** Quick filters for NDVI, SAVI, EVI, water bodies, and more.
- **Color Spaces:** Look at bands in RGB, HSV, LAB, etc.
- **Adjustments:** Simple sliders for brightness, contrast, and sharpness.
- **Histograms:** See the pixel intensity distribution for each band.

## Try it out

The tool is hosted live on Streamlit Community Cloud. You can test it out with the built-in sample images (no download required) or upload your own `.tif` files.

👉 **[Live App: band-visualizer.streamlit.app](https://band-visualizer.streamlit.app)**

Prefer a standalone desktop app? Download the older PyQt5 Windows executable:
📥 **[Download Windows App (v1.0.0)](https://github.com/AayushPrjapati/RGB-Band-Visualizer/releases/download/v1.0.0/RGB_Visualizer_Windows.zip)**
*(Extract the zip and run `main.exe`)*

## Running it locally

If you have really massive TIFF files, it's better to run the app on your own machine rather than uploading them to the cloud.

1. Clone the repo:
   ```bash
   git clone https://github.com/AayushPrjapati/RGB-Band-Visualizer.git
   cd RGB-Band-Visualizer
   ```
2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Start Streamlit:
   ```bash
   streamlit run app.py
   ```

## Folder Structure

- `app.py`: The Streamlit web app (what runs on the cloud).
- `samples/`: A few Landsat 8 GeoTIFFs I included so you can test the app without having to hunt down your own data.
- `desktop_app_source/`: The older PyQt5 desktop version of this tool.
- `requirements.txt`: Python libraries needed.
- `packages.txt`: System libraries (GDAL) that Streamlit Cloud needs to install `rasterio`.
