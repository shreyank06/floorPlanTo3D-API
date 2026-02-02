# Three.js Integration Guide

## Overview

This project now includes full Three.js integration for converting 2D floor plan images into interactive 3D models. The system detects walls, doors, and windows from 2D floor plans using Mask R-CNN and generates detailed 3D geometry with proper wall thickness and openings.

## What's New

### 1. **3D Geometry Generator** (`geometry_3d_generator.py`)
   - Converts 2D detection JSON to 3D models
   - Creates walls with configurable thickness
   - Places doors and windows at appropriate heights
   - Generates floor and ceiling planes
   - Exports to glTF 2.0 format

### 2. **New API Endpoint** (`/generate3d`)
   - Accepts floor plan images via POST request
   - Returns detection results + 3D model in glTF format
   - Supports customizable parameters:
     - `wall_height` (default: 3.0m)
     - `wall_thickness` (default: 0.15m)
     - `door_height` (default: 2.1m)
     - `window_height` (default: 1.2m)
     - `window_sill_height` (default: 0.9m)

### 3. **Interactive Web Viewer** (`/viewer`)
   - Beautiful web interface with Three.js
   - Drag-and-drop image upload
   - Real-time 3D model generation
   - Interactive controls (rotate, pan, zoom)
   - Export glTF models for use in other applications

## Installation & Setup

### Prerequisites
All required Python dependencies are already in `requirements.txt`:
- Flask 2.0.1
- Flask-CORS 5.0.0
- NumPy 1.19.5
- Pillow 8.2.0
- TensorFlow 1.15.3
- Keras 2.0.8
- scikit-image 0.17.2

### Running the Application

1. **Start the Flask server:**
   ```bash
   python application.py
   ```
   The server will start on `http://127.0.0.1:5000`

2. **Access the 3D Viewer:**
   - Open your browser and navigate to: `http://127.0.0.1:5000/viewer`
   - You should see the FloorPlan to 3D Viewer interface

## Usage

### Web Interface

1. **Upload a Floor Plan:**
   - Click "Choose Floor Plan Image" or drag-and-drop an image
   - Supported formats: PNG, JPG, JPEG

2. **Adjust 3D Settings (Optional):**
   - Wall Height: Height of walls in meters (2.0 - 5.0m)
   - Wall Thickness: Thickness of walls in meters (0.05 - 0.5m)
   - Door Height: Height of doors in meters (1.8 - 2.5m)
   - Window Height: Height of windows in meters (0.5 - 2.0m)
   - Window Sill Height: Distance from floor to window sill (0.3 - 1.5m)

3. **Generate 3D Model:**
   - Click "Generate 3D Model"
   - Wait for processing (typically 5-15 seconds)
   - View the interactive 3D model

4. **Interact with the Model:**
   - **Rotate:** Left-click and drag
   - **Pan:** Right-click and drag
   - **Zoom:** Scroll wheel

5. **Export Model:**
   - Click "Export glTF" to download the 3D model
   - Use the exported file in Blender, Unity, or other 3D software

### API Endpoints

#### 1. Original Detection Endpoint (Unchanged)
```bash
POST http://127.0.0.1:5000/
Content-Type: multipart/form-data

Parameters:
  - image: [floor plan image file]

Response:
{
  "points": [...],
  "classes": [...],
  "Width": 1024,
  "Height": 768,
  "averageDoor": 50.5
}
```

#### 2. New 3D Generation Endpoint
```bash
POST http://127.0.0.1:5000/generate3d
Content-Type: multipart/form-data

Parameters:
  - image: [floor plan image file]
  - wall_height: 3.0 (optional)
  - wall_thickness: 0.15 (optional)
  - door_height: 2.1 (optional)
  - window_height: 1.2 (optional)
  - window_sill_height: 0.9 (optional)

Response:
{
  "detection": {
    "points": [...],
    "classes": [...],
    "Width": 1024,
    "Height": 768,
    "averageDoor": 50.5
  },
  "gltf": {
    "asset": { "version": "2.0", ... },
    "scene": 0,
    "scenes": [...],
    "nodes": [...],
    "meshes": [...],
    "accessors": [...],
    "bufferViews": [...],
    "buffers": [...]
  },
  "metadata": {
    "wall_height": 3.0,
    "wall_thickness": 0.15,
    "num_vertices": 256,
    "num_faces": 128,
    "num_walls": 12,
    "num_doors": 2,
    "num_windows": 4
  }
}
```

### Example: Using the API with cURL

```bash
# Test the 3D generation endpoint
curl -X POST http://127.0.0.1:5000/generate3d \
  -F "image=@path/to/floorplan.jpg" \
  -F "wall_height=3.0" \
  -F "wall_thickness=0.15" \
  > output.json
```

### Example: Using the API with Python

```python
import requests

# Upload floor plan and generate 3D model
url = 'http://127.0.0.1:5000/generate3d'
files = {'image': open('floorplan.jpg', 'rb')}
data = {
    'wall_height': 3.0,
    'wall_thickness': 0.15,
    'door_height': 2.1,
    'window_height': 1.2,
    'window_sill_height': 0.9
}

response = requests.post(url, files=files, data=data)
result = response.json()

# Access detection results
detection = result['detection']
print(f"Detected {len(detection['classes'])} elements")

# Access glTF model
gltf_model = result['gltf']
print(f"Model has {result['metadata']['num_vertices']} vertices")

# Save glTF to file
import json
with open('output.gltf', 'w') as f:
    json.dump(gltf_model, f, indent=2)
```

## Architecture

### Processing Pipeline

```
Floor Plan Image (2D)
        ↓
[Mask R-CNN Detection]
  - Walls
  - Doors
  - Windows
        ↓
[2D Detection JSON]
  - Bounding boxes
  - Classifications
        ↓
[3D Geometry Generator]
  - Extrude walls vertically
  - Add wall thickness
  - Place doors/windows
  - Generate floor/ceiling
        ↓
[glTF 2.0 Model]
        ↓
[Three.js Renderer]
  - Interactive viewer
  - Orbit controls
  - Export capability
```

### File Structure

```
FloorPlanTo3D-API/
├── application.py              # Flask server with endpoints
├── geometry_3d_generator.py    # 3D geometry generation logic
├── mrcnn/                      # Mask R-CNN model
├── weights/                    # Pre-trained model weights
├── static/
│   ├── index.html             # Web viewer interface
│   └── js/
│       └── viewer.js          # Three.js visualization logic
├── requirements.txt            # Python dependencies
└── THREE_JS_INTEGRATION_GUIDE.md  # This file
```

## Technical Details

### 3D Coordinate System
- **X-axis:** Width of the floor plan
- **Y-axis:** Height (vertical, up is positive)
- **Z-axis:** Depth of the floor plan

### Scaling
- The system automatically scales floor plans to approximate real-world dimensions
- Default assumption: Floor plan represents ~10m x 10m space
- Scaling can be adjusted in `geometry_3d_generator.py` (lines 96-97)

### glTF Format
- Industry-standard 3D format
- Supports vertices, normals, and vertex colors
- Binary data embedded as base64 data URI
- Compatible with:
  - Three.js
  - Babylon.js
  - Blender
  - Unity
  - Unreal Engine
  - Sketchfab

### Browser Compatibility
The web viewer requires a modern browser with:
- WebGL support
- ES6 module support
- Tested on: Chrome, Firefox, Edge, Safari (latest versions)

## Customization

### Adjusting 3D Parameters

Edit `geometry_3d_generator.py` to modify default parameters:

```python
generator = FloorPlan3DGenerator(
    wall_height=3.0,        # Wall height in meters
    wall_thickness=0.15,    # Wall thickness in meters
    door_height=2.1,        # Door height in meters
    window_height=1.2,      # Window height in meters
    window_sill_height=0.9  # Window sill height in meters
)
```

### Changing Colors

Modify colors in `geometry_3d_generator.py`:
- Floor: Line 134 - `[0.85, 0.85, 0.85]` (light gray)
- Ceiling: Line 157 - `[0.95, 0.95, 0.95]` (white)
- Walls: Line 171 - `[0.9, 0.88, 0.85]` (light beige)
- Doors: Line 240 - `[0.6, 0.4, 0.2]` (brown)
- Windows: Line 277 - `[0.7, 0.85, 0.95]` (light blue)

### Adding Textures

To add textures instead of vertex colors:
1. Modify the glTF export to include texture coordinates (UV mapping)
2. Add material definitions with texture references
3. Include texture images in the glTF buffers

## Troubleshooting

### Model Not Displaying
- Check browser console for errors (F12)
- Verify the API endpoint is responding: `curl http://127.0.0.1:5000/viewer`
- Ensure Flask server is running with CORS enabled

### Walls Not Aligned
- The system determines wall orientation based on bounding box dimensions
- Very square walls may be misclassified
- Adjust the threshold in `_generate_walls()` if needed

### Poor Detection Quality
- Use high-quality, clear floor plan images
- Ensure walls, doors, and windows are clearly visible
- Avoid overly complex or hand-drawn floor plans
- Consider retraining the Mask R-CNN model with your specific floor plan style

### Export Issues
- Exported glTF files can be viewed in:
  - Online: https://gltf-viewer.donmccurdy.com/
  - Blender: File → Import → glTF 2.0
  - Windows 3D Viewer (built-in)

## Future Enhancements

Potential improvements:
- [ ] Automatic wall merging and corner detection
- [ ] Multi-story building support
- [ ] Furniture detection and placement
- [ ] Texture mapping from floor plan colors
- [ ] Room labeling and segmentation
- [ ] Measurement annotations
- [ ] VR/AR export formats
- [ ] Animated doors and windows

## Support

For issues or questions:
1. Check the Flask server logs
2. Inspect browser console (F12)
3. Verify input image quality
4. Review detection JSON output

## License

This integration maintains the same license as the original FloorPlanTo3D-API project.
