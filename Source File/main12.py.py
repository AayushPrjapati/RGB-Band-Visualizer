# Import necessary libraries and modules
import sys
import subprocess
import numpy as np
import rasterio  # For reading satellite imagery formats
from PIL import Image, ImageEnhance  # For image processing (brightness, contrast, etc.)
import cv2  # OpenCV for advanced image operations

# Import PyQt5 widgets for GUI creation
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QComboBox, QFileDialog,
    QVBoxLayout, QHBoxLayout, QScrollArea, QMessageBox, QSlider, QToolBar, QAction, QDialog, QShortcut
)
from PyQt5.QtGui import QPixmap, QImage, QIcon, QKeySequence
from PyQt5.QtCore import Qt, QSize

# For embedding matplotlib charts into PyQt5
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


0# -------------------------------
# STARTUP DIALOG CLASS
# -------------------------------
class StartupDialog(QDialog):
    """
    A welcome dialog shown when the application starts.
    Allows the user to upload an image file to begin working with.
    """
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Welcome to RGB and Band Image Visualizer")
        self.setFixedSize(500, 300)  # Fixed size window
        self.file_path = None  # To store the selected image file path

        # Main vertical layout
        layout = QVBoxLayout(self)

        # Title label
        title = QLabel("<h2>RGB and Band Image Visualizer</h2>")
        title.setAlignment(Qt.AlignCenter)

        # Instructions for the user
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
        instructions.setWordWrap(True)  # Allow text to wrap properly

        # Upload button to select an image file
        upload_button = QPushButton("Upload Image")
        upload_button.setFixedSize(150, 40)
        upload_button.clicked.connect(self.upload_image)  # Connect button to method

        # Add widgets to layout
        layout.addWidget(title)
        layout.addWidget(instructions)
        layout.addWidget(upload_button, alignment=Qt.AlignCenter)

    def upload_image(self):
        """
        Opens a file dialog to select an image file.
        Once selected, stores the file path and closes the dialog.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            "",
            "Image Files (*.tif *.tiff *.jp2 *.jpg *.jpeg *.png *.bmp *.gif *.img)"
        )

        if file_path:
            self.file_path = file_path
            self.accept()  # Close the dialog and return to main app


# -------------------------------
# HISTOGRAM VIEWER CLASS
# -------------------------------
class HistogramWindow(QDialog):
    """
    A window to display the histogram (pixel intensity distribution) of the loaded image.
    Allows viewing all bands together or individually.
    """
    def __init__(self, image_data, band_names):
        super().__init__()

        self.image_data = image_data  # List/array of image bands
        self.band_names = band_names  # Names or labels for each band

        self.setWindowTitle("Histogram Viewer")
        self.setFixedSize(800, 600)

        layout = QVBoxLayout(self)

        # Create a matplotlib canvas for drawing the histogram
        self.canvas = FigureCanvas(Figure(figsize=(8, 6)))
        layout.addWidget(self.canvas)

        # Label to show intensity and frequency on hover
        self.coord_label = QLabel("Hover to see coordinates")
        layout.addWidget(self.coord_label)

        # Dropdown to select which band to view histogram for
        self.band_selector = QComboBox()
        self.band_selector.addItem("All Bands")  # Option to show all
        self.band_selector.addItems(band_names)  # Add individual band names
        self.band_selector.currentIndexChanged.connect(self.update_histogram)
        layout.addWidget(self.band_selector)

        # Get a reference to the plot axis
        self.ax = self.canvas.figure.add_subplot(111)

        # Draw the initial histogram (all bands)
        self.plot_histogram(image_data, band_names)

        # Enable mouse hover to show intensity and frequency
        self.canvas.mpl_connect("motion_notify_event", self.on_hover)

    def plot_histogram(self, image_data, band_names, selected_band=None):
        """
        Plots the histogram for all bands or a selected band.
        """
        self.ax.clear()  # Clear previous plots
        self.hist_lines = []  # Stores histogram bin data for hover info

        if selected_band is not None:
            # Plot only selected band
            band = image_data[selected_band]
            flat = band.flatten()  # Flatten 2D image to 1D array
            hist, bins, patches = self.ax.hist(flat, bins=256, alpha=0.7,
                                               label=band_names[selected_band])
            self.hist_lines.append((bins, hist))
        else:
            # Plot all bands
            for i, band in enumerate(image_data):
                flat = band.flatten()
                hist, bins, patches = self.ax.hist(flat, bins=256, alpha=0.5,
                                                   label=band_names[i] if i < len(band_names) else f"Band {i+1}")
                self.hist_lines.append((bins, hist))

        # Label and draw the plot
        self.ax.set_title("Histogram of Image Bands")
        self.ax.set_xlabel("Pixel Intensity")
        self.ax.set_ylabel("Frequency")
        self.ax.legend()
        self.canvas.draw()

    def update_histogram(self):
        """
        Called when the user selects a different band from the dropdown.
        """
        index = self.band_selector.currentIndex()

        if index == 0:
            # Show all bands
            self.plot_histogram(self.image_data, self.band_names)
        else:
            # Show selected band (subtract 1 because first option is "All Bands")
            self.plot_histogram(self.image_data, self.band_names, selected_band=index - 1)

    def on_hover(self, event):
        """
        Handles mouse hover event over the histogram.
        Displays the intensity value and frequency of that bin.
        """
        if event.inaxes != self.ax or event.xdata is None:
            self.coord_label.setText("Hover to see coordinates")
            return

        intensity = event.xdata
        coord_text = f"Intensity: {intensity:.2f}"

        # Optionally show frequency (how many pixels fall in that intensity bin)
        for bins, hist in self.hist_lines:
            bin_idx = np.digitize(intensity, bins) - 1
            if 0 <= bin_idx < len(hist):
                frequency = hist[bin_idx]
                coord_text += f" | Frequency: {frequency:.0f}"
                break  # Show only for first matched band

        self.coord_label.setText(coord_text)

class BandVisualizer(QWidget):
    def __init__(self, file_path):
        super().__init__()
        self.setWindowTitle("RGB and Band Image Visualizer")
        self.resize(1200, 800)  # Set window size

        # Initialize key attributes
        self.file_path = file_path
        self.image_data = None
        self.current_image = None
        self.zoom_factor = 1.0  # Initial zoom level
        self.undo_stack = []
        self.redo_stack = []

        # Create main layout and sub-layouts
        self.main_layout = QVBoxLayout(self)
        self.top_controls = QHBoxLayout()
        self.middle_layout = QHBoxLayout()
        self.bottom_controls = QHBoxLayout()

        # Setup the toolbar
        self.init_top_toolbar()

        # Add a dark mode toggle button to the toolbar
        dark_mode_action = QAction("Toggle Dark Mode", self)
        dark_mode_action.setCheckable(True)
        dark_mode_action.triggered.connect(self.toggle_dark_mode)
        self.toolbar.addAction(dark_mode_action)

        # Variables for geospatial info (used later)
        self.geo_transform = None
        self.crs = None

        # Create layouts for controls and image display
        self.controls_layout = QVBoxLayout()
        self.image_layout = QVBoxLayout()

        # Initialize various sections
        self.init_band_selectors()   # RGB & single band selector
        self.init_filters()          # NDVI/EVI/SAVI etc.
        self.init_colourspace()      # Color space selector
        self.init_sliders()          # Brightness, contrast, sharpness sliders

        # Reset sliders button
        reset_btn = QPushButton("Reset Sliders")
        reset_btn.clicked.connect(self.reset_sliders)
        self.controls_layout.addWidget(reset_btn)

        # Show RGB composite image button
        self.show_composite_button = QPushButton("Show Composite RGB Image")
        self.show_composite_button.clicked.connect(self.show_rgb_image)
        self.controls_layout.addWidget(self.show_composite_button)

        # Show histogram button
        self.hist_button = QPushButton("Show Histogram")
        self.hist_button.clicked.connect(self.show_histogram)
        self.controls_layout.addWidget(self.hist_button)

        # Image display setup using QLabel inside QScrollArea
        self.image_label = QLabel(alignment=Qt.AlignCenter)
        scroll = QScrollArea(widgetResizable=True)
        scroll.setWidget(self.image_label)
        self.image_layout.addWidget(scroll)
        self.image_layout.addLayout(self.bottom_controls)

        # Combine left-side controls and right-side image layout
        self.middle_layout.addLayout(self.controls_layout, 1)
        self.middle_layout.addLayout(self.image_layout, 3)

        # Add top toolbar and middle layout to the main layout
        self.main_layout.addLayout(self.top_controls)
        self.main_layout.addLayout(self.middle_layout)

        # Load the image and initialize bottom controls and shortcuts
        self.load_image(self.file_path)
        self.init_bottom_controls()
        self.init_shortcuts()

    # Initializes the top toolbar with useful buttons
    def init_top_toolbar(self):
        self.toolbar = QToolBar("Top Tools")
        self.toolbar.setIconSize(QSize(24, 24))

        # Save button
        save_action = QAction(QIcon.fromTheme("document-save"), "Save Image", self)
        save_action.triggered.connect(self.save_image)
        self.toolbar.addAction(save_action)

        # Restart application button
        restart_action = QAction(QIcon.fromTheme("system-reboot"), "Restart App", self)
        restart_action.triggered.connect(self.restart_app)
        self.toolbar.addAction(restart_action)

        # Show band guide image
        info_action = QAction(QIcon.fromTheme("help-about"), "Band Guide", self)
        info_action.triggered.connect(self.show_info_popup)
        self.toolbar.addAction(info_action)

        # Show image metadata
        meta_action = QAction(QIcon.fromTheme("document-properties"), "Image Metadata", self)
        meta_action.triggered.connect(self.show_metadata_popup)
        self.toolbar.addAction(meta_action)

        # Add toolbar to the top controls layout
        self.top_controls.addWidget(self.toolbar)

    # Show popup with Sentinel vs Landsat band comparison image
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

    # Load a satellite image file using rasterio
    def load_image(self, file_path):
        try:
            self.src = rasterio.open(file_path)
            # Read all bands as separate numpy arrays
            self.image_data = [self.src.read(i) for i in range(1, self.src.count + 1)]
            # Generate band names (either from file metadata or default naming)
            self.band_names = (
                [desc if desc and desc.strip() else f"Band {i+1}" for i, desc in enumerate(self.src.descriptions)]
                if self.src.descriptions else [f"Band {i+1}" for i in range(self.src.count)]
            )
            self.update_band_selectors()  # Populate dropdowns with band names
            QMessageBox.information(self, "Success", f"Loaded image with {self.src.count} band(s).")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load image: {e}")

    # Create RGB and single band selector dropdowns
    def init_band_selectors(self):
        self.band_select_layout = QHBoxLayout()

        # Create dropdowns for R, G, B band selection
        self.r_band_combo, self.g_band_combo, self.b_band_combo = QComboBox(), QComboBox(), QComboBox()
        for label, combo in zip(["Red:", "Green:", "Blue:"], [self.r_band_combo, self.g_band_combo, self.b_band_combo]):
            self.band_select_layout.addWidget(QLabel(label))
            self.band_select_layout.addWidget(combo)

        self.controls_layout.addLayout(self.band_select_layout)

        # Create dropdown for viewing a single band
        self.single_band_combo = QComboBox()
        self.single_band_combo.currentIndexChanged.connect(self.show_single_band)
        self.controls_layout.addWidget(QLabel("View Single Band:"))
        self.controls_layout.addWidget(self.single_band_combo)

    # Populate all band selection dropdowns with band names
    def update_band_selectors(self):
        for combo in [self.r_band_combo, self.g_band_combo, self.b_band_combo, self.single_band_combo]:
            combo.clear()  # Clear existing items

        for i, name in enumerate(self.band_names):
            # Add each band to all four combo boxes
            for combo in [self.r_band_combo, self.g_band_combo, self.b_band_combo, self.single_band_combo]:
                combo.addItem(name, i)

    # Initialize filter dropdown menu
    def init_filters(self):
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "None", "Vegetation Highlight", "Natural Color", "Urban/Soil",
            "Water Bodies", "Healthy Vegetation Contrast", "NDVI Enhanced",
            "SAVI (Soil-Adjusted Vegetation Index)", "EVI (Enhanced Vegetation Index)"
        ])
        self.filter_combo.currentIndexChanged.connect(self.apply_filter)  # Connect dropdown change to filter application
        self.controls_layout.addWidget(QLabel("Apply Filter:"))
        self.controls_layout.addWidget(self.filter_combo)

    # Initialize color space selection dropdown
    def init_colourspace(self):
        self.color_space_combo = QComboBox()
        self.color_space_combo.addItems([
            "RGB", "HSV", "LAB", "HLS", "YCrCb", "Grayscale"
        ])
        self.color_space_combo.currentTextChanged.connect(self.update_color_space)
        self.controls_layout.addWidget(QLabel("Select Color Space:"))
        self.controls_layout.addWidget(self.color_space_combo)

    # Initialize sliders for brightness, contrast, and sharpness
    def init_sliders(self):
        self.brightness_slider = self.create_slider("Brightness", self.apply_adjustments)
        self.contrast_slider = self.create_slider("Contrast", self.apply_adjustments)
        self.sharpness_slider = self.create_slider("Sharpness", self.apply_adjustments)

    # Helper to create a labeled horizontal slider
    def create_slider(self, label, slot):
        self.controls_layout.addWidget(QLabel(label))
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(50)
        slider.setMaximum(150)
        slider.setValue(100)  # 100% means no change
        slider.setTickInterval(10)
        slider.valueChanged.connect(slot)
        self.controls_layout.addWidget(slider)
        return slider

    # Initialize buttons for zoom, rotate, undo, redo
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

    # Normalize band values between 0 and 1
    def normalize_band(self, band):
        band = band.astype(np.float32)
        return (band - band.min()) / (band.max() - band.min() + 1e-6)

    # Save current image state for undo
    def push_undo(self):
        if self.current_image:
            self.undo_stack.append(self.current_image.copy())
            self.redo_stack.clear()

    # Undo last action
    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(self.current_image.copy())
            self.current_image = self.undo_stack.pop()
            self.apply_adjustments()

    # Redo last undone action
    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.current_image.copy())
            self.current_image = self.redo_stack.pop()
            self.apply_adjustments()

    # Display RGB composite from selected bands
    def show_rgb_image(self):
        if not self.image_data:
            return
        indices = [combo.currentData() for combo in [self.r_band_combo, self.g_band_combo, self.b_band_combo]]
        rgb = np.stack([self.normalize_band(self.image_data[i]) for i in indices], axis=-1)
        self.push_undo()
        self.current_image = Image.fromarray((rgb * 255).astype(np.uint8))
        self.zoom_factor = 1.0
        self.apply_adjustments()

    # Display a single selected band
    def show_single_band(self):
        if not self.image_data:
            return
        band = self.normalize_band(self.image_data[self.single_band_combo.currentData()])
        self.push_undo()
        self.current_image = Image.fromarray((band * 255).astype(np.uint8)).convert('RGB')
        self.zoom_factor = 1.0
        self.apply_adjustments()

    # Apply brightness, contrast, sharpness, and zoom
    def apply_adjustments(self):
        if not self.current_image:
            return
        img = self.current_image.copy()

        # Enhance image based on slider values
        for enhancer, value in zip(
            [ImageEnhance.Brightness, ImageEnhance.Contrast, ImageEnhance.Sharpness],
            [self.brightness_slider.value(), self.contrast_slider.value(), self.sharpness_slider.value()]
        ):
            img = enhancer(img).enhance(value / 100.0)

        # Apply zoom if needed
        if self.zoom_factor != 1.0:
            w, h = img.size
            img = img.resize((int(w * self.zoom_factor), int(h * self.zoom_factor)))

        # Convert to QImage and display
        img_qt = QImage(img.tobytes(), img.width, img.height, 3 * img.width, QImage.Format_RGB888)
        self.image_label.setPixmap(QPixmap.fromImage(img_qt))

    # Apply selected image filter
    def apply_filter(self):
        if not self.image_data or self.filter_combo.currentText() == "None":
            self.apply_adjustments()
            return

        if len(self.image_data) < 4:
            QMessageBox.warning(self, "Filter Warning", "At least 4 bands are needed for advanced filters.")
            return

        try:
            names = {name.lower(): i for i, name in enumerate(self.band_names)}

            def get_band(key, fallback_idx):
                key = key.lower()
                try:
                    return self.normalize_band(self.image_data[names[key]])
                except KeyError:
                    if fallback_idx < len(self.image_data):
                        return self.normalize_band(self.image_data[fallback_idx])
                    else:
                        QMessageBox.warning(self, "Missing Band", f"Could not find band '{key}'.")
                        raise

            # Determine satellite type for band mapping
            is_sentinel = any("b8" in name.lower() for name in self.band_names)
            is_landsat = any("band4" in name.lower() or "b4" in name.lower() for name in self.band_names)

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

            if filt in ["Vegetation Highlight", "Natural Color", "Urban/Soil", "NDVI Enhanced"]:
                self.current_image = Image.fromarray((composite * 255).clip(0, 255).astype(np.uint8))

            self.zoom_factor = 1.0
            self.apply_adjustments()

        except Exception as e:
            QMessageBox.critical(self, "Filter Error", f"Error applying filter: {e}")

    # Update image with selected color space
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
                        QMessageBox.warning(self, "Missing Band", f"Could not find band '{key}'.")
                        raise

            # Get RGB bands
            red = get_band("B4", 0)
            green = get_band("B3", 1)
            blue = get_band("B2", 2)

            # Stack RGB and normalize to 0-255
            rgb = np.dstack([red, green, blue])
            rgb_max = rgb.max() if rgb.max() != 0 else 1.0
            rgb_norm = rgb / rgb_max
            self.rgb_uint8 = (rgb_norm * 255).clip(0, 255).astype(np.uint8)

            # Convert to BGR for OpenCV
            self.bgr = cv2.cvtColor(self.rgb_uint8, cv2.COLOR_RGB2BGR)

            # Apply selected color space
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

            # Make sure image is 3-channel RGB
            if len(img.shape) == 2:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)

            # Display using PyQt
            h, w, ch = img.shape
            bytes_per_line = ch * w
            q_img = QImage(img.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.image_label.setPixmap(QPixmap.fromImage(q_img).scaled(
                self.image_label.width(), self.image_label.height(), Qt.KeepAspectRatio
            ))

            self.zoom_factor = 1.0
            self.current_image = Image.fromarray(img)
            self.apply_adjustments()

        except:
            QMessageBox.critical(self, "Color Space Error", "Error applying Colour Space:")



    # Show histogram for the current image
    def show_histogram(self):
        if not self.image_data:
            QMessageBox.warning(self, "No Image", "Please load an image first.")
            return
        # Open a histogram window showing pixel value distributions
        hist_window = HistogramWindow(self.image_data, self.band_names)
        hist_window.exec_()

    # Save the current image to a file
    def save_image(self):
        if self.current_image:
            # Open a file dialog to choose save location and format
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Image", "output.png",
                "PNG Files (*.png);;JPEG Files (*.jpg *.jpeg)"
            )
            if path:
                self.current_image.save(path)  # Save the image to the chosen path

    # Zoom in on the image
    def zoom_in(self):
        self.zoom_factor *= 1.25  # Increase zoom factor
        self.apply_adjustments()  # Re-apply image display updates

    # Zoom out of the image
    def zoom_out(self):
        self.zoom_factor /= 1.25  # Decrease zoom factor
        self.apply_adjustments()

    # Rotate the image by 90 degrees clockwise
    def rotate_image(self):
        if self.current_image:
            self.push_undo()  # Save current state to undo stack
            self.current_image = self.current_image.rotate(90, expand=True)  # Rotate image
            self.apply_adjustments()

    # Restart the entire application
    def restart_app(self):
        python_exe = sys.executable  # Get path to Python executable
        subprocess.Popen([python_exe] + sys.argv)  # Start a new process with same script
        QApplication.quit()  # Quit the current app

    # Set up keyboard shortcuts for common actions
    def init_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Z"), self, activated=self.undo)          # Undo
        QShortcut(QKeySequence("Ctrl+Y"), self, activated=self.redo)          # Redo
        QShortcut(QKeySequence("Ctrl++"), self, activated=self.zoom_in)       # Zoom in
        QShortcut(QKeySequence("Ctrl+-"), self, activated=self.zoom_out)      # Zoom out
        QShortcut(QKeySequence("Ctrl+R"), self, activated=self.rotate_image)  # Rotate image
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self.save_image)    # Save image
        QShortcut(QKeySequence("Ctrl+H"), self, activated=self.show_histogram)  # Show histogram
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self.restart_app)   # Restart app

    # Toggle dark mode theme on and off
    def toggle_dark_mode(self, checked):
        if checked:
            # Apply dark theme styles
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
            # Reset to default (light) theme
            self.setStyleSheet("")

    # Reset brightness, contrast, and sharpness sliders to default (100%)
    def reset_sliders(self):
        self.brightness_slider.setValue(100)
        self.contrast_slider.setValue(100)
        self.sharpness_slider.setValue(100)

    # Show a popup window with metadata info about the loaded image
    def show_metadata_popup(self):
        if not self.src:  # Make sure an image is loaded
            return

        meta = self.src.meta  # Retrieve metadata from the image source
        # Format metadata as HTML for display
        info = f"""
        <b>File:</b> {self.file_path}<br>
        <b>Size:</b> {meta['width']} x {meta['height']}<br>
        <b>Bands:</b> {meta['count']}<br>
        <b>CRS:</b> {meta['crs']}<br>
        <b>Transform:</b> {meta['transform']}<br>
        <b>Dtype:</b> {meta['dtype']}<br>
        """

        # Create a simple dialog window to show the metadata
        dlg = QDialog(self)
        dlg.setWindowTitle("Image Metadata")
        layout = QVBoxLayout(dlg)
        label = QLabel(info)
        label.setWordWrap(True)  # Enable word wrapping for long lines
        layout.addWidget(label)
        dlg.exec_()  # Show the dialog

# --- Main entry point of the application ---
if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Show the startup dialog to select the image file
    startup = StartupDialog()
    if startup.exec_() == QDialog.Accepted and startup.file_path:
        # If user clicks OK and a file path is selected, launch the main viewer
        viewer = BandVisualizer(startup.file_path)
        viewer.show()
        sys.exit(app.exec_())  # Start the Qt event loop
