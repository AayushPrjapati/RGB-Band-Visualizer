import streamlit as st
import numpy as np
import rasterio
from rasterio.io import MemoryFile
from PIL import Image, ImageEnhance
import cv2
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import io

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="RGB & Band Image Visualizer",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Dark gradient background */
.stApp {
    background: linear-gradient(135deg, #0f0c29, #1a1a2e, #16213e);
    color: #e0e0e0;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    border-right: 1px solid rgba(99, 179, 237, 0.2);
}
[data-testid="stSidebar"] * {
    color: #e0e0e0 !important;
}

/* Hero banner */
.hero-banner {
    background: linear-gradient(135deg, rgba(99,179,237,0.15), rgba(159,122,234,0.15));
    border: 1px solid rgba(99, 179, 237, 0.3);
    border-radius: 16px;
    padding: 24px 32px;
    margin-bottom: 24px;
    backdrop-filter: blur(10px);
}
.hero-title {
    font-size: 2rem;
    font-weight: 700;
    background: linear-gradient(90deg, #63b3ed, #9f7aea);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
}
.hero-sub {
    font-size: 1rem;
    color: #a0aec0;
    margin-top: 6px;
}

/* Metric cards */
.metric-card {
    background: rgba(99,179,237,0.08);
    border: 1px solid rgba(99,179,237,0.2);
    border-radius: 12px;
    padding: 16px;
    text-align: center;
}
.metric-label { font-size: 0.75rem; color: #718096; text-transform: uppercase; letter-spacing: 1px; }
.metric-value { font-size: 1.5rem; font-weight: 700; color: #63b3ed; }

/* Section headers */
.section-header {
    font-size: 0.8rem;
    font-weight: 600;
    color: #9f7aea;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin: 20px 0 8px 0;
    border-bottom: 1px solid rgba(159,122,234,0.3);
    padding-bottom: 4px;
}

/* Upload zone */
.upload-zone {
    background: rgba(99,179,237,0.05);
    border: 2px dashed rgba(99,179,237,0.4);
    border-radius: 16px;
    padding: 40px;
    text-align: center;
}

/* Info box */
.info-box {
    background: rgba(159,122,234,0.1);
    border-left: 3px solid #9f7aea;
    border-radius: 0 8px 8px 0;
    padding: 12px 16px;
    margin: 8px 0;
    font-size: 0.85rem;
    color: #d0c0ff;
}

/* Streamlit component overrides */
.stSlider > div > div > div { background: linear-gradient(90deg, #63b3ed, #9f7aea) !important; }
div[data-testid="stMetric"] { background: rgba(99,179,237,0.08); border-radius: 12px; padding: 12px; border: 1px solid rgba(99,179,237,0.2); }
.stSelectbox label, .stSlider label, .stFileUploader label { color: #a0aec0 !important; font-size: 0.85rem !important; }
.stButton > button {
    background: linear-gradient(135deg, #63b3ed, #9f7aea);
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.3s;
}
.stButton > button:hover { opacity: 0.85; transform: translateY(-1px); }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def normalize_band(band):
    band = band.astype(np.float32)
    mn, mx = band.min(), band.max()
    return (band - mn) / (mx - mn + 1e-6)


def apply_enhancements(img_pil, brightness, contrast, sharpness):
    img = ImageEnhance.Brightness(img_pil).enhance(brightness)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    img = ImageEnhance.Sharpness(img).enhance(sharpness)
    return img


def pil_to_bytes(img_pil, fmt="PNG"):
    buf = io.BytesIO()
    img_pil.save(buf, format=fmt)
    return buf.getvalue()


def get_band(band_names, image_data, key, fallback_idx):
    names = {n.lower(): i for i, n in enumerate(band_names)}
    k = key.lower()
    if k in names:
        return normalize_band(image_data[names[k]])
    elif fallback_idx < len(image_data):
        return normalize_band(image_data[fallback_idx])
    else:
        return normalize_band(image_data[0])


def apply_filter(filter_name, band_names, image_data):
    is_sentinel = any("b8" in n.lower() for n in band_names)

    if is_sentinel:
        red   = get_band(band_names, image_data, "B4",  3)
        green = get_band(band_names, image_data, "B3",  2)
        blue  = get_band(band_names, image_data, "B2",  1)
        nir   = get_band(band_names, image_data, "B8",  7)
    else:
        red   = get_band(band_names, image_data, "SR_B4", 3)
        green = get_band(band_names, image_data, "SR_B3", 2)
        blue  = get_band(band_names, image_data, "SR_B2", 1)
        nir   = get_band(band_names, image_data, "SR_B5", 4)

    composite = None

    if filter_name == "Vegetation Highlight":
        composite = np.stack([nir, red, green], axis=-1)
    elif filter_name == "Natural Color":
        composite = np.stack([red, green, blue], axis=-1)
    elif filter_name == "Urban / Soil":
        swir = get_band(band_names, image_data, "B11" if is_sentinel else "SR_B6", 5)
        composite = np.stack([swir, red, green], axis=-1)
    elif filter_name == "Water Bodies":
        water = np.clip(blue - nir, 0, 1)
        composite = np.stack([water, water * 0.5, blue], axis=-1)
    elif filter_name == "Healthy Vegetation Contrast":
        c = np.clip(nir - red, 0, 1)
        composite = np.stack([c * 0.2, c, c * 0.4], axis=-1)
    elif filter_name == "NDVI Enhanced":
        ndvi = (nir - red) / (nir + red + 1e-6)
        ndvi = np.clip(ndvi, -1, 1)
        # Colormap: red=low, yellow=mid, green=high
        cmap = plt.cm.RdYlGn
        colored = cmap((ndvi + 1) / 2)[:, :, :3]
        composite = colored
    elif filter_name == "SAVI":
        savi = ((nir - red) / (nir + red + 0.5)) * 1.5
        savi = np.clip(savi, 0, 1)
        composite = np.stack([savi * 0.2, savi, savi * 0.3], axis=-1)
    elif filter_name == "EVI":
        evi = 2.5 * (nir - red) / (nir + 6 * red - 7.5 * blue + 1)
        evi = np.clip(evi, 0, 1)
        composite = np.stack([evi * 0.2, evi, evi * 0.4], axis=-1)

    if composite is not None:
        img_arr = (np.clip(composite, 0, 1) * 255).astype(np.uint8)
        return Image.fromarray(img_arr)
    return None


def apply_colorspace(rgb_uint8, mode):
    bgr = cv2.cvtColor(rgb_uint8, cv2.COLOR_RGB2BGR)
    if mode == "RGB":
        img = rgb_uint8
    elif mode == "HSV":
        img = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    elif mode == "LAB":
        img = cv2.cvtColor(bgr, cv2.COLOR_BGR2Lab)
    elif mode == "HLS":
        img = cv2.cvtColor(bgr, cv2.COLOR_BGR2HLS)
    elif mode == "YCrCb":
        img = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
    elif mode == "Grayscale":
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        img = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
    else:
        img = rgb_uint8
    if len(img.shape) == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    return img


def plot_histogram(image_data, band_names, selected_idx=None):
    fig, ax = plt.subplots(figsize=(8, 3.5))
    fig.patch.set_facecolor('#0f1117')
    ax.set_facecolor('#1a1a2e')

    colors = ['#63b3ed', '#68d391', '#fc8181', '#f6ad55', '#9f7aea', '#76e4f7', '#fbd38d']

    if selected_idx is not None:
        band = image_data[selected_idx].flatten()
        ax.hist(band, bins=256, color=colors[selected_idx % len(colors)], alpha=0.85,
                label=band_names[selected_idx])
    else:
        for i, band in enumerate(image_data):
            flat = band.flatten()
            ax.hist(flat, bins=256, alpha=0.55,
                    color=colors[i % len(colors)],
                    label=band_names[i] if i < len(band_names) else f"Band {i+1}")

    ax.set_title("Pixel Intensity Distribution", color='#e0e0e0', fontsize=12, pad=10)
    ax.set_xlabel("Pixel Intensity", color='#a0aec0')
    ax.set_ylabel("Frequency", color='#a0aec0')
    ax.tick_params(colors='#718096')
    ax.spines['bottom'].set_color('#2d3748')
    ax.spines['left'].set_color('#2d3748')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.legend(facecolor='#1a1a2e', edgecolor='#2d3748', labelcolor='#e0e0e0', fontsize=8)
    fig.tight_layout()
    return fig


# ─────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────
for key in ["image_data", "band_names", "meta", "current_img", "filename"]:
    if key not in st.session_state:
        st.session_state[key] = None


# ─────────────────────────────────────────────
# HERO BANNER
# ─────────────────────────────────────────────
st.markdown("""
<div class="hero-banner">
  <p class="hero-title">🛰️ RGB & Band Image Visualizer</p>
  <p class="hero-sub">Professional satellite imagery analysis · Sentinel-2 & Landsat-8 · Spectral indices & color space transforms</p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SIDEBAR — FILE UPLOAD + CONTROLS
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p class="section-header">📁 Upload Image</p>', unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "Supported: GeoTIFF, JP2, PNG, JPG",
        type=["tif", "tiff", "jp2", "jpg", "jpeg", "png", "bmp", "img"],
        help="Upload a multi-band satellite image to begin"
    )

    if uploaded:
        try:
            raw = uploaded.read()
            with MemoryFile(raw) as mf:
                with mf.open() as src:
                    image_data = [src.read(i) for i in range(1, src.count + 1)]
                    meta = src.meta.copy()
                    band_names = (
                        [d if d and d.strip() else f"Band {i+1}" for i, d in enumerate(src.descriptions)]
                        if src.descriptions else [f"Band {i+1}" for i in range(src.count)]
                    )
            st.session_state.image_data = image_data
            st.session_state.band_names = band_names
            st.session_state.meta = meta
            st.session_state.filename = uploaded.name
            st.success(f"✅ Loaded {src.count} band(s)")
        except Exception as e:
            st.error(f"❌ Failed to load: {e}")

    # ── Show controls only if image loaded ──
    if st.session_state.image_data:
        band_names = st.session_state.band_names
        image_data = st.session_state.image_data
        n_bands = len(image_data)

        # ── Metadata Card ──
        st.markdown('<p class="section-header">📊 Image Info</p>', unsafe_allow_html=True)
        m = st.session_state.meta
        col1, col2 = st.columns(2)
        col1.metric("Bands", m.get("count", n_bands))
        col2.metric("Dtype", m.get("dtype", "—"))
        col1.metric("Width", m.get("width", "—"))
        col2.metric("Height", m.get("height", "—"))
        crs = str(m.get("crs", "N/A"))
        st.caption(f"CRS: {crs[:40]}")

        st.divider()

        # ── Visualization Mode ──
        st.markdown('<p class="section-header">🎨 Visualization Mode</p>', unsafe_allow_html=True)
        mode = st.radio("Mode", ["RGB Composite", "Single Band", "Spectral Filter", "Color Space"],
                        horizontal=False)

        st.divider()

        # ── Mode-specific controls ──
        if mode == "RGB Composite":
            st.markdown('<p class="section-header">🔴🟢🔵 Band Assignment</p>', unsafe_allow_html=True)
            r_idx = st.selectbox("Red Channel",   band_names, index=min(2, n_bands-1), key="r")
            g_idx = st.selectbox("Green Channel", band_names, index=min(1, n_bands-1), key="g")
            b_idx = st.selectbox("Blue Channel",  band_names, index=min(0, n_bands-1), key="b")

        elif mode == "Single Band":
            st.markdown('<p class="section-header">📡 Band Selection</p>', unsafe_allow_html=True)
            sb = st.selectbox("Select Band", band_names, key="single_band")
            cmap_choice = st.selectbox("Colormap", ["Grayscale", "Viridis", "Plasma", "Inferno", "Hot", "Cool"])

        elif mode == "Spectral Filter":
            st.markdown('<p class="section-header">🌿 Spectral Index</p>', unsafe_allow_html=True)
            if n_bands < 4:
                st.warning("⚠️ Need ≥ 4 bands for spectral filters")
            filt = st.selectbox("Filter", [
                "Vegetation Highlight", "Natural Color", "Urban / Soil",
                "Water Bodies", "Healthy Vegetation Contrast",
                "NDVI Enhanced", "SAVI", "EVI"
            ])
            is_s2 = any("b8" in n.lower() for n in band_names)
            st.markdown(f'<div class="info-box">🛰️ Detected: {"Sentinel-2" if is_s2 else "Landsat-8 / Generic"}</div>', unsafe_allow_html=True)

        elif mode == "Color Space":
            st.markdown('<p class="section-header">🌈 Color Space</p>', unsafe_allow_html=True)
            cs = st.selectbox("Color Space", ["RGB", "HSV", "LAB", "HLS", "YCrCb", "Grayscale"])

        st.divider()

        # ── Image Adjustments ──
        st.markdown('<p class="section-header">⚙️ Adjustments</p>', unsafe_allow_html=True)
        brightness = st.slider("☀️ Brightness", 0.5, 2.0, 1.0, 0.05)
        contrast   = st.slider("🔲 Contrast",   0.5, 2.0, 1.0, 0.05)
        sharpness  = st.slider("✨ Sharpness",  0.5, 3.0, 1.0, 0.05)

        st.divider()

        # ── Histogram ──
        st.markdown('<p class="section-header">📈 Histogram</p>', unsafe_allow_html=True)
        show_hist = st.checkbox("Show Histogram")
        if show_hist:
            hist_band = st.selectbox("Histogram Band", ["All Bands"] + band_names)


# ─────────────────────────────────────────────
# MAIN CONTENT
# ─────────────────────────────────────────────
if not st.session_state.image_data:
    # ── Welcome / Upload prompt ──
    st.markdown("""
    <div class="upload-zone">
        <div style="font-size:4rem">🛰️</div>
        <h3 style="color:#63b3ed; margin:12px 0 8px">Upload a Satellite Image to Begin</h3>
        <p style="color:#718096">Supports GeoTIFF (.tif/.tiff), JPEG2000 (.jp2), PNG, JPG</p>
        <p style="color:#718096; font-size:0.85rem">Works with Sentinel-2, Landsat-8, and generic multi-band imagery</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🔬 What This Tool Can Do")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        **🎨 RGB Compositing**
        Assign any satellite band to the Red, Green, Blue channels to create custom composites.
        """)
        st.markdown("""
        **📡 Single Band View**
        Visualize any individual band with multiple scientific colormaps.
        """)
    with c2:
        st.markdown("""
        **🌿 Spectral Indices**
        NDVI, EVI, SAVI, Water Bodies, Vegetation Highlight, Urban/Soil composites.
        """)
        st.markdown("""
        **🌈 Color Spaces**
        View imagery in RGB, HSV, LAB, HLS, YCrCb, or Grayscale.
        """)
    with c3:
        st.markdown("""
        **⚙️ Image Adjustments**
        Real-time brightness, contrast, and sharpness enhancement.
        """)
        st.markdown("""
        **📊 Histogram Analysis**
        Per-band pixel intensity distribution for radiometric analysis.
        """)

else:
    image_data = st.session_state.image_data
    band_names = st.session_state.band_names
    n_bands = len(image_data)
    result_img = None

    try:
        # ── Generate Image Based on Mode ──
        if mode == "RGB Composite":
            ri = band_names.index(r_idx)
            gi = band_names.index(g_idx)
            bi = band_names.index(b_idx)
            rgb = np.stack([
                normalize_band(image_data[ri]),
                normalize_band(image_data[gi]),
                normalize_band(image_data[bi])
            ], axis=-1)
            arr = (rgb * 255).astype(np.uint8)
            result_img = Image.fromarray(arr)

        elif mode == "Single Band":
            si = band_names.index(sb)
            band_norm = normalize_band(image_data[si])
            cmap_map = {
                "Grayscale": "gray", "Viridis": "viridis", "Plasma": "plasma",
                "Inferno": "inferno", "Hot": "hot", "Cool": "cool"
            }
            cmap = plt.colormaps[cmap_map[cmap_choice]]
            colored = (cmap(band_norm)[:, :, :3] * 255).astype(np.uint8)
            result_img = Image.fromarray(colored)

        elif mode == "Spectral Filter":
            if n_bands >= 4:
                result_img = apply_filter(filt, band_names, image_data)
            else:
                st.warning("Need at least 4 bands for spectral filters.")

        elif mode == "Color Space":
            # Build default RGB from first 3 bands
            r = normalize_band(image_data[min(2, n_bands-1)])
            g = normalize_band(image_data[min(1, n_bands-1)])
            b = normalize_band(image_data[min(0, n_bands-1)])
            rgb_arr = (np.dstack([r, g, b]) * 255).astype(np.uint8)
            cs_arr = apply_colorspace(rgb_arr, cs)
            result_img = Image.fromarray(cs_arr)

        # ── Apply Adjustments ──
        if result_img:
            result_img = apply_enhancements(result_img, brightness, contrast, sharpness)

    except Exception as e:
        st.error(f"Error generating image: {e}")

    # ── Display ──
    if result_img:
        col_img, col_info = st.columns([3, 1])

        with col_img:
            st.image(result_img, use_container_width=True, caption=f"📍 {st.session_state.filename} — {mode}")

            # Download button
            img_bytes = pil_to_bytes(result_img)
            st.download_button(
                "⬇️ Download Image",
                data=img_bytes,
                file_name="visualized_output.png",
                mime="image/png",
                use_container_width=True
            )

        with col_info:
            st.markdown("#### 🗂️ Active Settings")
            st.markdown(f"**Mode:** {mode}")
            if mode == "RGB Composite":
                st.markdown(f"**R:** {r_idx}")
                st.markdown(f"**G:** {g_idx}")
                st.markdown(f"**B:** {b_idx}")
            elif mode == "Single Band":
                st.markdown(f"**Band:** {sb}")
                st.markdown(f"**Colormap:** {cmap_choice}")
            elif mode == "Spectral Filter":
                st.markdown(f"**Filter:** {filt}")
            elif mode == "Color Space":
                st.markdown(f"**Space:** {cs}")

            st.markdown("---")
            st.markdown("**Adjustments**")
            st.markdown(f"☀️ Brightness: `{brightness:.2f}x`")
            st.markdown(f"🔲 Contrast: `{contrast:.2f}x`")
            st.markdown(f"✨ Sharpness: `{sharpness:.2f}x`")

            st.markdown("---")
            st.markdown("**Image Size**")
            w, h = result_img.size
            st.markdown(f"`{w} × {h} px`")

    # ── Histogram ──
    if show_hist:
        st.markdown("---")
        st.markdown("### 📊 Band Histogram")
        sel_idx = None if hist_band == "All Bands" else band_names.index(hist_band)
        fig = plot_histogram(image_data, band_names, sel_idx)
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

    # ── Band Info Table ──
    with st.expander("🔍 Band Details", expanded=False):
        import pandas as pd
        rows = []
        for i, (name, bd) in enumerate(zip(band_names, image_data)):
            rows.append({
                "Band #": i+1,
                "Name": name,
                "Min": f"{bd.min():.2f}",
                "Max": f"{bd.max():.2f}",
                "Mean": f"{bd.mean():.2f}",
                "Std Dev": f"{bd.std():.2f}",
                "Shape": f"{bd.shape[0]}×{bd.shape[1]}"
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

    # ── Full Metadata ──
    with st.expander("📋 Full Image Metadata", expanded=False):
        meta = st.session_state.meta
        for k, v in meta.items():
            st.markdown(f"**{k}:** `{v}`")
