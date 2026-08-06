import sys

import subprocess
import numpy as np
import rasterio
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QComboBox, QFileDialog,
    QVBoxLayout, QHBoxLayout, QScrollArea, QMessageBox, QSlider, QToolBar, QAction, QDialog,QShortcut
)
from PyQt5.QtGui import QPixmap, QImage, QIcon,QKeySequence
from PyQt5.QtCore import Qt, QSize
from PIL import Image, ImageEnhance
import cv2

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure





class StartupDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Welcome to RGB and Band Image Visualizer")
        self.setFixedSize(500, 300)
        self.file_path = None

        layout = QVBoxLayout(self)

        title = QLabel("<h2>RGB and Band Image Visualizer</h2>")
        title.setAlignment(Qt.AlignCenter)

        instructions = QLabel("""
        <p>This tool lets you:</p>
        <ul>
            <li>Select bands to create RGB composites</li>
            <li>View single band images</li>
            <li>Color space transformations supported</li>
            <li>Apply vegetation and water filters</li>
            <li>Adjust brightness, contrast, and sharpness</li>
            <li>Histogram viewer to analyze pixel distribution by band.</li>
        </ul>
        <p>Please upload an image to get started.</p>
        """)
        instructions.setWordWrap(True)

        upload_button = QPushButton("Upload Image")
        upload_button.setFixedSize(150, 40)
        upload_button.clicked.connect(self.upload_image)

        layout.addWidget(title)
        layout.addWidget(instructions)
        layout.addWidget(upload_button, alignment=Qt.AlignCenter)

    def upload_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", 
                        "Image Files (*.tif *.tiff *.jp2 *.jpg *.jpeg *.png *.bmp *.gif *.img)")
        if file_path:
            self.file_path = file_path
            self.accept()




class HistogramWindow(QDialog):
    def __init__(self, image_data, band_names):
        super().__init__()
        self.image_data = image_data
        self.band_names = band_names

        self.setWindowTitle("Histogram Viewer")
        self.setFixedSize(800, 600)

        layout = QVBoxLayout(self)
        self.canvas = FigureCanvas(Figure(figsize=(8, 6)))
        layout.addWidget(self.canvas)

        self.coord_label = QLabel("Hover to see coordinates")
        layout.addWidget(self.coord_label)

        self.band_selector = QComboBox()
        self.band_selector.addItem("All Bands")
        self.band_selector.addItems(band_names)
        self.band_selector.currentIndexChanged.connect(self.update_histogram)
        layout.addWidget(self.band_selector)


        self.ax = self.canvas.figure.add_subplot(111)
        self.plot_histogram(image_data, band_names)

        

        # Connect mouse motion event
        self.canvas.mpl_connect("motion_notify_event", self.on_hover)

    def plot_histogram(self, image_data, band_names, selected_band=None):

        self.ax.clear()
        self.hist_lines = []

        if selected_band is not None:
            band = image_data[selected_band]
            flat = band.flatten()
            hist, bins, patches = self.ax.hist(flat, bins=256, alpha=0.7, label=band_names[selected_band])
            self.hist_lines.append((bins, hist))
        else:
            for i, band in enumerate(image_data):
                flat = band.flatten()
                hist, bins, patches = self.ax.hist(flat, bins=256, alpha=0.5,
                                                label=band_names[i] if i < len(band_names) else f"Band {i+1}")
                self.hist_lines.append((bins, hist))

        self.ax.set_title("Histogram of Image Bands")
        self.ax.set_xlabel("Pixel Intensity")
        self.ax.set_ylabel("Frequency")
        self.ax.legend()
        self.canvas.draw()

    def update_histogram(self):
        index = self.band_selector.currentIndex()
        if index == 0:
            self.plot_histogram(self.image_data, self.band_names)
        else:
            self.plot_histogram(self.image_data, self.band_names, selected_band=index - 1)


    def on_hover(self, event):
        if event.inaxes != self.ax or event.xdata is None:
            self.coord_label.setText("Hover to see coordinates")
            return

        intensity = event.xdata
        coord_text = f"Intensity: {intensity:.2f}"

        # Optionally show nearest bin frequency for one of the bands
        for bins, hist in self.hist_lines:
            bin_idx = np.digitize(intensity, bins) - 1
            if 0 <= bin_idx < len(hist):
                frequency = hist[bin_idx]
                coord_text += f" | Frequency: {frequency:.0f}"
                break  # show only for first match

        self.coord_label.setText(coord_text)



class BandVisualizer(QWidget):
    def __init__(self, file_path):
        super().__init__()
        self.setWindowTitle("RGB and Band Image Visualizer")
        self.resize(1200, 800)

        self.file_path = file_path
        self.image_data = None
        self.current_image = None
        self.zoom_factor = 1.0
        self.undo_stack = []
        self.redo_stack = []

        self.main_layout = QVBoxLayout(self)
        self.top_controls = QHBoxLayout()
        self.middle_layout = QHBoxLayout()
        self.bottom_controls = QHBoxLayout()

        self.init_top_toolbar()

        dark_mode_action = QAction("Toggle Dark Mode", self)
        dark_mode_action.setCheckable(True)
        dark_mode_action.triggered.connect(self.toggle_dark_mode)
        self.toolbar.addAction(dark_mode_action)

        self.geo_transform = None
        self.crs = None


        self.controls_layout = QVBoxLayout()
        self.image_layout = QVBoxLayout()

        self.init_band_selectors()
        self.init_filters()
        self.init_colourspace()
        self.init_sliders()
        
        reset_btn = QPushButton("Reset Sliders")
        reset_btn.clicked.connect(self.reset_sliders)
        self.controls_layout.addWidget(reset_btn)

        self.show_composite_button = QPushButton("Show Composite RGB Image")
        self.show_composite_button.clicked.connect(self.show_rgb_image)
        self.controls_layout.addWidget(self.show_composite_button)

        self.hist_button = QPushButton("Show Histogram")
        self.hist_button.clicked.connect(self.show_histogram)
        self.controls_layout.addWidget(self.hist_button)

        self.image_label = QLabel(alignment=Qt.AlignCenter)
        scroll = QScrollArea(widgetResizable=True)
        scroll.setWidget(self.image_label)
        self.image_layout.addWidget(scroll)
        self.image_layout.addLayout(self.bottom_controls)

        self.middle_layout.addLayout(self.controls_layout, 1)
        self.middle_layout.addLayout(self.image_layout, 3)

        self.main_layout.addLayout(self.top_controls)
        self.main_layout.addLayout(self.middle_layout)

        self.load_image(self.file_path)
        self.init_bottom_controls()
        self.init_shortcuts()




    def init_top_toolbar(self):
        self.toolbar = QToolBar("Top Tools")
        self.toolbar.setIconSize(QSize(24, 24))

        save_action = QAction(QIcon.fromTheme("document-save"), "Save Image", self)
        save_action.triggered.connect(self.save_image)
        self.toolbar.addAction(save_action)

        restart_action = QAction(QIcon.fromTheme("system-reboot"), "Restart App", self)
        restart_action.triggered.connect(self.restart_app)
        self.toolbar.addAction(restart_action)

        info_action = QAction(QIcon.fromTheme("help-about"), "Band Guide", self)
        info_action.triggered.connect(self.show_info_popup)
        self.toolbar.addAction(info_action)

        meta_action = QAction(QIcon.fromTheme("document-properties"), "Image Metadata", self)
        meta_action.triggered.connect(self.show_metadata_popup)
        self.toolbar.addAction(meta_action)

        self.top_controls.addWidget(self.toolbar)

    def show_info_popup(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Sentinel vs Landsat Band Info")
        layout = QVBoxLayout(dialog)

        image_label = QLabel()
        pixmap = QPixmap(r"RGB and Band Image Visualizer/images/sentinel_landsat_band_comparison.jpg")
        if pixmap.isNull():
            image_label.setText("Failed to load image.")
        else:
            image_label.setPixmap(pixmap.scaledToWidth(700, Qt.SmoothTransformation))

        layout.addWidget(image_label)
        dialog.exec_()

    def load_image(self, file_path):
        try:
            self.src = rasterio.open(file_path)
            self.image_data = [self.src.read(i) for i in range(1, self.src.count + 1)]
            self.band_names = (
                [desc if desc and desc.strip() else f"Band {i+1}" for i, desc in enumerate(self.src.descriptions)]
                if self.src.descriptions else [f"Band {i+1}" for i in range(self.src.count)]
            )
            self.update_band_selectors()
            QMessageBox.information(self, "Success", f"Loaded image with {self.src.count} band(s).")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load image: {e}")

    def init_band_selectors(self):
        self.band_select_layout = QHBoxLayout()
        self.r_band_combo, self.g_band_combo, self.b_band_combo = QComboBox(), QComboBox(), QComboBox()
        for label, combo in zip(["Red:", "Green:", "Blue:"], [self.r_band_combo, self.g_band_combo, self.b_band_combo]):
            self.band_select_layout.addWidget(QLabel(label))
            self.band_select_layout.addWidget(combo)
        self.controls_layout.addLayout(self.band_select_layout)

        self.single_band_combo = QComboBox()
        self.single_band_combo.currentIndexChanged.connect(self.show_single_band)
        self.controls_layout.addWidget(QLabel("View Single Band:"))
        self.controls_layout.addWidget(self.single_band_combo)

    def update_band_selectors(self):
        for combo in [self.r_band_combo, self.g_band_combo, self.b_band_combo, self.single_band_combo]:
            combo.clear()
        for i, name in enumerate(self.band_names):
            for combo in [self.r_band_combo, self.g_band_combo, self.b_band_combo, self.single_band_combo]:
                combo.addItem(name, i)

    def init_filters(self):
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "None", "Vegetation Highlight", "Natural Color", "Urban/Soil",
            "Water Bodies", "Healthy Vegetation Contrast", "NDVI Enhanced",
            "SAVI (Soil-Adjusted Vegetation Index)", "EVI (Enhanced Vegetation Index)"
        ])
        self.filter_combo.currentIndexChanged.connect(self.apply_filter)
        self.controls_layout.addWidget(QLabel("Apply Filter:"))
        self.controls_layout.addWidget(self.filter_combo)

    def init_colourspace(self):
        self.color_space_combo = QComboBox()
        self.color_space_combo.addItems([
            "RGB", "HSV", "LAB", "HLS", "YCrCb", "Grayscale"
        ])
        self.color_space_combo.currentTextChanged.connect(self.update_color_space)
        self.controls_layout.addWidget(QLabel("Select Color Space:"))
        self.controls_layout.addWidget(self.color_space_combo)

    def init_sliders(self):
        self.brightness_slider = self.create_slider("Brightness", self.apply_adjustments)
        self.contrast_slider = self.create_slider("Contrast", self.apply_adjustments)
        self.sharpness_slider = self.create_slider("Sharpness", self.apply_adjustments)

    def create_slider(self, label, slot):
        self.controls_layout.addWidget(QLabel(label))
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(50)
        slider.setMaximum(150)
        slider.setValue(100)
        slider.setTickInterval(10)
        slider.valueChanged.connect(slot)
        self.controls_layout.addWidget(slider)
        return slider

    def init_bottom_controls(self):
        buttons = [
            ("zoom-in", "Zoom In", self.zoom_in),
            ("zoom-out", "Zoom Out", self.zoom_out),
            ("object-rotate-right", "Rotate", self.rotate_image),
            ("edit-undo", "Undo", self.undo),
            ("edit-redo", "Redo", self.redo),
        ]
        for icon, label, slot in buttons:
            btn = QPushButton(label)
            btn.setIcon(QIcon.fromTheme(icon))
            btn.setIconSize(QSize(24, 24))
            btn.clicked.connect(slot)
            self.bottom_controls.addWidget(btn)

    def normalize_band(self, band):
        band = band.astype(np.float32)
        return (band - band.min()) / (band.max() - band.min() + 1e-6)

    def push_undo(self):
        if self.current_image:
            self.undo_stack.append(self.current_image.copy())
            self.redo_stack.clear()

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(self.current_image.copy())
            self.current_image = self.undo_stack.pop()
            self.apply_adjustments()

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.current_image.copy())
            self.current_image = self.redo_stack.pop()
            self.apply_adjustments()

    def show_rgb_image(self):
        if not self.image_data:
            return
        indices = [combo.currentData() for combo in [self.r_band_combo, self.g_band_combo, self.b_band_combo]]
        rgb = np.stack([self.normalize_band(self.image_data[i]) for i in indices], axis=-1)
        self.push_undo()
        self.current_image = Image.fromarray((rgb * 255).astype(np.uint8))
        
        self.apply_adjustments()

    def show_single_band(self):
        if not self.image_data:
            return
        band = self.normalize_band(self.image_data[self.single_band_combo.currentData()])
        self.push_undo()
        self.current_image = Image.fromarray((band * 255).astype(np.uint8)).convert('RGB')
        
        self.apply_adjustments()

    def apply_adjustments(self):
        if not self.current_image:
            return
        img = self.current_image.copy()
        for enhancer, value in zip(
            [ImageEnhance.Brightness, ImageEnhance.Contrast, ImageEnhance.Sharpness],
            [self.brightness_slider.value(), self.contrast_slider.value(), self.sharpness_slider.value()]):
            img = enhancer(img).enhance(value / 100.0)
        if self.zoom_factor != 1.0:
            w, h = img.size
            img = img.resize((int(w * self.zoom_factor), int(h * self.zoom_factor)))
        img_qt = QImage(img.tobytes(), img.width, img.height, 3 * img.width, QImage.Format_RGB888)
        self.image_label.setPixmap(QPixmap.fromImage(img_qt))

    def apply_filter(self):
        if not self.image_data or self.filter_combo.currentText() == "None":
            self.apply_adjustments()
            return
        if len(self.image_data) < 4:
            QMessageBox.warning(self, "Filter Warning", "At least 4 bands are needed for advanced filters.")
            return

        try:
            # Map lowercase band names to their indices
            names = {name.lower(): i for i, name in enumerate(self.band_names)}

            def get_band(key, fallback_idx):
                key = key.lower()
                try:
                    return self.normalize_band(self.image_data[names[key]])
                except KeyError:
                    if fallback_idx < len(self.image_data):
                        return self.normalize_band(self.image_data[fallback_idx])
                    else:
                        QMessageBox.warning(self, "Missing Band", f"Could not find band '{key}' or fallback index {fallback_idx}.")
                        raise

            # Auto-detect satellite type
            is_sentinel = any("b8" in name.lower() for name in self.band_names)
            is_landsat = any("band4" in name.lower() or "b4" in name.lower() for name in self.band_names)

            # Sentinel-2 band mapping
            if is_sentinel:
                red = get_band("B4", 3)
                green = get_band("B3", 2)
                blue = get_band("B2", 1)
                nir = get_band("B8", 7)
            # Landsat-8 or fallback mapping
            else:
                red = get_band("SR_B4", 3)
                green = get_band("SR_B3", 2)
                blue = get_band("SR_B2", 1)
                nir = get_band("SR_B5", 4)

            filt = self.filter_combo.currentText()
            self.push_undo()

            if filt == "Vegetation Highlight":
                composite = np.stack([nir, red, green], axis=-1)
            elif filt == "Natural Color":
                composite = np.stack([red, green, blue], axis=-1)
            elif filt == "Urban/Soil":
                if is_sentinel:
                    swir = get_band("B11", 11)  # SWIR1
                else:
                    swir = get_band("SR_B6", 5)  # SWIR1 for Landsat-8
                composite = np.stack([swir, red, green], axis=-1)
            elif filt == "Water Bodies":
                water = (blue - nir)
                self.current_image = Image.fromarray((water * 255).clip(0, 255).astype(np.uint8)).convert("RGB")
            elif filt == "Healthy Vegetation Contrast":
                contrast = (nir - red)
                self.current_image = Image.fromarray((contrast * 255).clip(0, 255).astype(np.uint8)).convert("RGB")
            elif filt == "NDVI Enhanced":
                ndvi = (nir - red) / (nir + red + 1e-6)
                ndvi_color = np.stack([ndvi, ndvi ** 2, ndvi ** 3], -1)
                composite = ndvi_color
            elif filt == "SAVI (Soil-Adjusted Vegetation Index)":
                savi = ((nir - red) / (nir + red + 0.5)) * 1.5
                self.current_image = Image.fromarray((savi * 255).clip(0, 255).astype(np.uint8)).convert("RGB")
            elif filt == "EVI (Enhanced Vegetation Index)":
                evi = 2.5 * (nir - red) / (nir + 6 * red - 7.5 * blue + 1)
                self.current_image = Image.fromarray((evi * 255).clip(0, 255).astype(np.uint8)).convert("RGB")

            # Show RGB if applicable
            if filt in ["Vegetation Highlight", "Natural Color", "Urban/Soil", "NDVI Enhanced"]:
                self.current_image = Image.fromarray((composite * 255).clip(0, 255).astype(np.uint8))

            
            self.apply_adjustments()
        except Exception as e:
            QMessageBox.critical(self, "Filter Error", f"Error applying filter: {e}")


    def update_color_space(self, mode):
        
        try:
            names = {name.lower(): i for i, name in enumerate(self.band_names)}
            def get_band(key, fallback_idx):
                    key = key.lower()
                    try:
                        return self.normalize_band(self.image_data[names[key]])
                    except:
                        if fallback_idx < len(self.image_data):
                            return self.normalize_band(self.image_data[fallback_idx])
                        else:
                            QMessageBox.warning(self, "Missing Band", f"Could not find band '{key}' or fallback index {fallback_idx}.")
                            raise
            red = get_band("B4", 0)
            green = get_band("B3", 1)
            blue = get_band("B2", 2)

            rgb = np.dstack([red, green, blue])
            rgb_max = rgb.max() if rgb.max() != 0 else 1.0
            rgb_norm = rgb / rgb_max
            self.rgb_uint8 = (rgb_norm * 255).clip(0, 255).astype(np.uint8)
            self.bgr = cv2.cvtColor(self.rgb_uint8, cv2.COLOR_RGB2BGR)

            if mode == "RGB":
                img = self.rgb_uint8
            elif mode == "HSV":
                img = cv2.cvtColor(self.bgr, cv2.COLOR_BGR2HSV)
            elif mode == "LAB":
                img = cv2.cvtColor(self.bgr, cv2.COLOR_BGR2Lab)
            elif mode == "HLS":
                img = cv2.cvtColor(self.bgr, cv2.COLOR_BGR2HLS)
            elif mode == "YCrCb":
                img = cv2.cvtColor(self.bgr, cv2.COLOR_BGR2YCrCb)
            elif mode == "Grayscale":
                img = cv2.cvtColor(self.bgr, cv2.COLOR_BGR2GRAY)
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
                
            if len(img.shape) == 2:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)

            h, w, ch = img.shape
            bytes_per_line = ch * w
            q_img = QImage(img.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.image_label.setPixmap(QPixmap.fromImage(q_img).scaled(
                self.image_label.width(), self.image_label.height(), Qt.KeepAspectRatio
            ))
            
            self.current_image = Image.fromarray(img)
            self.apply_adjustments()
        except:
            QMessageBox.critical(self, "Filter Error", f"Error applying Colour Space:")
    


    def show_histogram(self):
        if not self.image_data:
            QMessageBox.warning(self, "No Image", "Please load an image first.")
            return
        hist_window = HistogramWindow(self.image_data, self.band_names)
        hist_window.exec_()

    def save_image(self):
        if self.current_image:
            path, _ = QFileDialog.getSaveFileName(self, "Save Image", "output.png", 
                            "PNG Files (*.png);;JPEG Files (*.jpg *.jpeg)")
            if path:
                self.current_image.save(path)

    def zoom_in(self):
        self.zoom_factor *= 1.25
        self.apply_adjustments()

    def zoom_out(self):
        self.zoom_factor /= 1.25
        self.apply_adjustments()
 
    def rotate_image(self):
        if self.current_image:
            self.push_undo()
            self.current_image = self.current_image.rotate(90, expand=True)
            self.apply_adjustments()

    def restart_app(self):
        python_exe = sys.executable
        subprocess.Popen([python_exe] + sys.argv)
        QApplication.quit()

    def init_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Z"), self, activated=self.undo)
        QShortcut(QKeySequence("Ctrl+Y"), self, activated=self.redo)
        QShortcut(QKeySequence("Ctrl++"), self, activated=self.zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self, activated=self.zoom_out)
        QShortcut(QKeySequence("Ctrl+R"), self, activated=self.rotate_image)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self.save_image)
        QShortcut(QKeySequence("Ctrl+H"), self, activated=self.show_histogram)
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self.restart_app)

    def toggle_dark_mode(self, checked):
        if checked:
            dark_stylesheet = """
                QWidget {
                    background-color: #2b2b2b;
                    color: #f0f0f0;
                }
                QComboBox, QPushButton, QSlider {
                    background-color: #3c3f41;
                    color: white;
                    border: 1px solid #5a5a5a;
                }
            """
            self.setStyleSheet(dark_stylesheet)
        else:
            self.setStyleSheet("")

    def reset_sliders(self):
        self.brightness_slider.setValue(100)
        self.contrast_slider.setValue(100)
        self.sharpness_slider.setValue(100)

    def show_metadata_popup(self):
        if not self.src:  # Ensure there's an image loaded
            return

        meta = self.src.meta  # Assuming 'src' holds your image
        info = f"""
        <b>File:</b> {self.file_path}<br>
        <b>Size:</b> {meta['width']} x {meta['height']}<br>
        <b>Bands:</b> {meta['count']}<br>
        <b>CRS:</b> {meta['crs']}<br>
        <b>Transform:</b> {meta['transform']}<br>
        <b>Dtype:</b> {meta['dtype']}<br>
        """

        # Create a dialog to show the metadata
        dlg = QDialog(self)
        dlg.setWindowTitle("Image Metadata")
        layout = QVBoxLayout(dlg)
        label = QLabel(info)
        label.setWordWrap(True)
        layout.addWidget(label)
        dlg.exec_()  # Display the dialog





if __name__ == '__main__':
    app = QApplication(sys.argv)

    startup = StartupDialog()
    if startup.exec_() == QDialog.Accepted and startup.file_path:
        viewer = BandVisualizer(startup.file_path)
        viewer.show()
        sys.exit(app.exec_())
