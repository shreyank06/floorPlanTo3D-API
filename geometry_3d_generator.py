"""
3D Geometry Generator for Floor Plans
Converts 2D floor plan detection JSON into 3D models with detailed geometry
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple
import json


@dataclass
class Point2D:
    """2D point representation"""
    x: float
    y: float


@dataclass
class BBox:
    """Bounding box with classification"""
    x1: float
    y1: float
    x2: float
    y2: float
    class_name: str

    @property
    def width(self):
        return abs(self.x2 - self.x1)

    @property
    def height(self):
        return abs(self.y2 - self.y1)

    @property
    def center(self):
        return Point2D((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)


class FloorPlan3DGenerator:
    """Generates 3D geometry from 2D floor plan detection results"""

    def __init__(self, wall_height=3.0, wall_thickness=0.15,
                 door_height=2.1, window_height=1.2, window_sill_height=0.9):
        """
        Initialize the 3D generator with architectural parameters

        Args:
            wall_height: Height of walls in meters (default: 3.0m)
            wall_thickness: Thickness of walls in meters (default: 0.15m = 15cm)
            door_height: Height of doors in meters (default: 2.1m)
            window_height: Height of windows in meters (default: 1.2m)
            window_sill_height: Height from floor to window sill (default: 0.9m)
        """
        self.wall_height = wall_height
        self.wall_thickness = wall_thickness
        self.door_height = door_height
        self.window_height = window_height
        self.window_sill_height = window_sill_height

        # Storage for geometry data
        self.vertices = []
        self.faces = []
        self.normals = []
        self.colors = []

    def parse_detection_json(self, detection_json):
        """
        Parse the floor plan detection JSON

        Args:
            detection_json: JSON dict from the detection API

        Returns:
            Tuple of (walls, doors, windows) as lists of BBox objects
        """
        points = detection_json['points']
        classes = detection_json['classes']
        width = detection_json['Width']
        height = detection_json['Height']

        walls = []
        doors = []
        windows = []

        for point, class_info in zip(points, classes):
            # Points are already in pixel coordinates (not normalized 0-1)
            bbox = BBox(
                x1=point['x1'],
                y1=point['y1'],
                x2=point['x2'],
                y2=point['y2'],
                class_name=class_info['name']
            )

            if bbox.class_name == 'wall':
                walls.append(bbox)
            elif bbox.class_name == 'door':
                doors.append(bbox)
            elif bbox.class_name == 'window':
                windows.append(bbox)

        return walls, doors, windows, width, height

    def generate_3d_model(self, detection_json):
        """
        Generate complete 3D model from detection JSON

        Args:
            detection_json: JSON dict from the detection API

        Returns:
            Dict containing vertices, faces, and metadata for 3D rendering
        """
        walls, doors, windows, img_width, img_height = self.parse_detection_json(detection_json)

        # Reset geometry data
        self.vertices = []
        self.faces = []
        self.normals = []
        self.colors = []

        # Scaling factor to convert pixels to meters (approximate)
        # Assume the floor plan represents a typical room of about 10m x 10m
        scale_x = 10.0 / img_width
        scale_y = 10.0 / img_height

        # Generate geometry for each component
        self._generate_floor(walls, scale_x, scale_y, img_width, img_height)
        self._generate_walls(walls, doors, windows, scale_x, scale_y)
        self._generate_doors(doors, scale_x, scale_y)
        self._generate_windows(windows, scale_x, scale_y)
        self._generate_ceiling(walls, scale_x, scale_y, img_width, img_height)

        return {
            'vertices': self.vertices,
            'faces': self.faces,
            'normals': self.normals,
            'colors': self.colors,
            'metadata': {
                'wall_height': self.wall_height,
                'wall_thickness': self.wall_thickness,
                'num_vertices': len(self.vertices),
                'num_faces': len(self.faces),
                'num_walls': len(walls),
                'num_doors': len(doors),
                'num_windows': len(windows)
            }
        }

    def _generate_floor(self, walls, scale_x, scale_y, width, height):
        """Generate floor plane"""
        # Create a simple rectangular floor based on image bounds
        base_idx = len(self.vertices)

        # Floor vertices (Y is up in 3D, so floor is at y=0)
        floor_vertices = [
            [0, 0, 0],                                    # Bottom-left
            [width * scale_x, 0, 0],                      # Bottom-right
            [width * scale_x, 0, height * scale_y],       # Top-right
            [0, 0, height * scale_y]                      # Top-left
        ]

        self.vertices.extend(floor_vertices)

        # Floor faces (two triangles)
        self.faces.extend([
            [base_idx, base_idx + 1, base_idx + 2],
            [base_idx, base_idx + 2, base_idx + 3]
        ])

        # Floor color (darker for better contrast)
        floor_color = [0.6, 0.6, 0.6]
        self.colors.extend([floor_color] * 4)

        # Normals pointing up
        self.normals.extend([[0, 1, 0]] * 4)

    def _generate_ceiling(self, walls, scale_x, scale_y, width, height):
        """Generate ceiling plane (semi-transparent for bird's eye view)"""
        base_idx = len(self.vertices)

        # Ceiling vertices at wall_height
        ceiling_vertices = [
            [0, self.wall_height, 0],
            [width * scale_x, self.wall_height, 0],
            [width * scale_x, self.wall_height, height * scale_y],
            [0, self.wall_height, height * scale_y]
        ]

        self.vertices.extend(ceiling_vertices)

        # Ceiling faces (two triangles, winding order reversed)
        self.faces.extend([
            [base_idx, base_idx + 2, base_idx + 1],
            [base_idx, base_idx + 3, base_idx + 2]
        ])

        # Ceiling color (semi-transparent white for bird's eye view)
        ceiling_color = [0.95, 0.95, 0.95]
        self.colors.extend([ceiling_color] * 4)

        # Normals pointing down
        self.normals.extend([[0, -1, 0]] * 4)

    def _generate_walls(self, walls, doors, windows, scale_x, scale_y):
        """Generate wall geometry with cutouts for doors and windows"""
        wall_color = [0.95, 0.95, 0.95]  # White/light gray for better visibility

        for wall in walls:
            # Determine if wall is horizontal or vertical
            is_horizontal = wall.width > wall.height

            # Convert to 3D coordinates
            x1 = wall.x1 * scale_x
            z1 = wall.y1 * scale_y
            x2 = wall.x2 * scale_x
            z2 = wall.y2 * scale_y

            # Check for intersecting doors/windows
            intersecting_openings = []
            for door in doors:
                if self._check_intersection(wall, door):
                    intersecting_openings.append(('door', door))
            for window in windows:
                if self._check_intersection(wall, window):
                    intersecting_openings.append(('window', window))

            if is_horizontal:
                # Horizontal wall (along X axis)
                self._create_horizontal_wall(x1, z1, x2, z2, wall_color,
                                             intersecting_openings, scale_x, scale_y)
            else:
                # Vertical wall (along Z axis)
                self._create_vertical_wall(x1, z1, x2, z2, wall_color,
                                           intersecting_openings, scale_x, scale_y)

    def _create_horizontal_wall(self, x1, z1, x2, z2, color, openings, scale_x, scale_y):
        """Create a horizontal wall (along X axis) with optional openings"""
        base_idx = len(self.vertices)

        # Wall runs along X, with thickness in Z direction
        z_center = (z1 + z2) / 2
        z_front = z_center - self.wall_thickness / 2
        z_back = z_center + self.wall_thickness / 2

        # Simple wall without openings for now (openings will be handled by boolean operations)
        # Front face
        vertices = [
            [x1, 0, z_front], [x2, 0, z_front],
            [x2, self.wall_height, z_front], [x1, self.wall_height, z_front],
            # Back face
            [x1, 0, z_back], [x2, 0, z_back],
            [x2, self.wall_height, z_back], [x1, self.wall_height, z_back]
        ]

        self.vertices.extend(vertices)

        # Faces
        faces = [
            # Front face
            [base_idx, base_idx + 1, base_idx + 2],
            [base_idx, base_idx + 2, base_idx + 3],
            # Back face
            [base_idx + 5, base_idx + 4, base_idx + 7],
            [base_idx + 5, base_idx + 7, base_idx + 6],
            # Left face
            [base_idx + 4, base_idx, base_idx + 3],
            [base_idx + 4, base_idx + 3, base_idx + 7],
            # Right face
            [base_idx + 1, base_idx + 5, base_idx + 6],
            [base_idx + 1, base_idx + 6, base_idx + 2],
            # Top face
            [base_idx + 3, base_idx + 2, base_idx + 6],
            [base_idx + 3, base_idx + 6, base_idx + 7]
        ]

        self.faces.extend(faces)
        self.colors.extend([color] * 8)

        # Normals (simplified - one per vertex)
        normals = [
            [0, 0, -1], [0, 0, -1], [0, 0, -1], [0, 0, -1],
            [0, 0, 1], [0, 0, 1], [0, 0, 1], [0, 0, 1]
        ]
        self.normals.extend(normals)

    def _create_vertical_wall(self, x1, z1, x2, z2, color, openings, scale_x, scale_y):
        """Create a vertical wall (along Z axis) with optional openings"""
        base_idx = len(self.vertices)

        # Wall runs along Z, with thickness in X direction
        x_center = (x1 + x2) / 2
        x_front = x_center - self.wall_thickness / 2
        x_back = x_center + self.wall_thickness / 2

        # Front face
        vertices = [
            [x_front, 0, z1], [x_front, 0, z2],
            [x_front, self.wall_height, z2], [x_front, self.wall_height, z1],
            # Back face
            [x_back, 0, z1], [x_back, 0, z2],
            [x_back, self.wall_height, z2], [x_back, self.wall_height, z1]
        ]

        self.vertices.extend(vertices)

        # Faces
        faces = [
            # Front face
            [base_idx, base_idx + 1, base_idx + 2],
            [base_idx, base_idx + 2, base_idx + 3],
            # Back face
            [base_idx + 5, base_idx + 4, base_idx + 7],
            [base_idx + 5, base_idx + 7, base_idx + 6],
            # Left face
            [base_idx + 4, base_idx, base_idx + 3],
            [base_idx + 4, base_idx + 3, base_idx + 7],
            # Right face
            [base_idx + 1, base_idx + 5, base_idx + 6],
            [base_idx + 1, base_idx + 6, base_idx + 2],
            # Top face
            [base_idx + 3, base_idx + 2, base_idx + 6],
            [base_idx + 3, base_idx + 6, base_idx + 7]
        ]

        self.faces.extend(faces)
        self.colors.extend([color] * 8)

        # Normals
        normals = [
            [-1, 0, 0], [-1, 0, 0], [-1, 0, 0], [-1, 0, 0],
            [1, 0, 0], [1, 0, 0], [1, 0, 0], [1, 0, 0]
        ]
        self.normals.extend(normals)

    def _generate_doors(self, doors, scale_x, scale_y):
        """Generate door geometry"""
        door_color = [0.4, 0.25, 0.1]  # Darker brown for better visibility

        for door in doors:
            x1 = door.x1 * scale_x
            z1 = door.y1 * scale_y
            x2 = door.x2 * scale_x
            z2 = door.y2 * scale_y

            # Create a simple door panel
            base_idx = len(self.vertices)

            # Determine door orientation
            is_horizontal = door.width > door.height

            if is_horizontal:
                # Door along X axis
                z_pos = (z1 + z2) / 2
                vertices = [
                    [x1, 0, z_pos], [x2, 0, z_pos],
                    [x2, self.door_height, z_pos], [x1, self.door_height, z_pos]
                ]
            else:
                # Door along Z axis
                x_pos = (x1 + x2) / 2
                vertices = [
                    [x_pos, 0, z1], [x_pos, 0, z2],
                    [x_pos, self.door_height, z2], [x_pos, self.door_height, z1]
                ]

            self.vertices.extend(vertices)

            # Door faces (both sides visible)
            self.faces.extend([
                [base_idx, base_idx + 1, base_idx + 2],
                [base_idx, base_idx + 2, base_idx + 3],
                [base_idx + 1, base_idx, base_idx + 3],
                [base_idx + 1, base_idx + 3, base_idx + 2]
            ])

            self.colors.extend([door_color] * 4)

            # Normals
            if is_horizontal:
                self.normals.extend([[0, 0, 1]] * 4)
            else:
                self.normals.extend([[1, 0, 0]] * 4)

    def _generate_windows(self, windows, scale_x, scale_y):
        """Generate window geometry"""
        window_color = [0.3, 0.6, 0.9]  # Darker blue for better visibility

        for window in windows:
            x1 = window.x1 * scale_x
            z1 = window.y1 * scale_y
            x2 = window.x2 * scale_x
            z2 = window.y2 * scale_y

            # Create a simple window panel
            base_idx = len(self.vertices)

            # Determine window orientation
            is_horizontal = window.width > window.height

            y_bottom = self.window_sill_height
            y_top = self.window_sill_height + self.window_height

            if is_horizontal:
                # Window along X axis
                z_pos = (z1 + z2) / 2
                vertices = [
                    [x1, y_bottom, z_pos], [x2, y_bottom, z_pos],
                    [x2, y_top, z_pos], [x1, y_top, z_pos]
                ]
            else:
                # Window along Z axis
                x_pos = (x1 + x2) / 2
                vertices = [
                    [x_pos, y_bottom, z1], [x_pos, y_bottom, z2],
                    [x_pos, y_top, z2], [x_pos, y_top, z1]
                ]

            self.vertices.extend(vertices)

            # Window faces (both sides visible)
            self.faces.extend([
                [base_idx, base_idx + 1, base_idx + 2],
                [base_idx, base_idx + 2, base_idx + 3],
                [base_idx + 1, base_idx, base_idx + 3],
                [base_idx + 1, base_idx + 3, base_idx + 2]
            ])

            self.colors.extend([window_color] * 4)

            # Normals
            if is_horizontal:
                self.normals.extend([[0, 0, 1]] * 4)
            else:
                self.normals.extend([[1, 0, 0]] * 4)

    def _check_intersection(self, wall, opening):
        """Check if an opening (door/window) intersects with a wall"""
        # Simple bounding box intersection
        return not (opening.x2 < wall.x1 or opening.x1 > wall.x2 or
                   opening.y2 < wall.y1 or opening.y1 > wall.y2)

    def export_to_gltf_dict(self, detection_json):
        """
        Export the 3D model to glTF 2.0 format as a dictionary

        Args:
            detection_json: JSON dict from the detection API

        Returns:
            Dictionary representing glTF 2.0 structure
        """
        geometry = self.generate_3d_model(detection_json)

        # Convert to numpy arrays for easier processing
        vertices = np.array(geometry['vertices'], dtype=np.float32)
        faces = np.array(geometry['faces'], dtype=np.uint32)
        normals = np.array(geometry['normals'], dtype=np.float32)
        colors = np.array(geometry['colors'], dtype=np.float32)

        # Flatten arrays
        vertices_flat = vertices.flatten().tolist()
        faces_flat = faces.flatten().tolist()
        normals_flat = normals.flatten().tolist()
        colors_flat = colors.flatten().tolist()

        # Calculate bounding box
        min_vals = vertices.min(axis=0).tolist()
        max_vals = vertices.max(axis=0).tolist()

        # Build glTF structure
        gltf = {
            "asset": {
                "version": "2.0",
                "generator": "FloorPlanTo3D-API"
            },
            "scene": 0,
            "scenes": [
                {
                    "nodes": [0]
                }
            ],
            "nodes": [
                {
                    "mesh": 0
                }
            ],
            "materials": [
                {
                    "pbrMetallicRoughness": {
                        "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
                        "metallicFactor": 0.0,
                        "roughnessFactor": 1.0
                    },
                    "doubleSided": True
                }
            ],
            "meshes": [
                {
                    "primitives": [
                        {
                            "attributes": {
                                "POSITION": 0,
                                "NORMAL": 1,
                                "COLOR_0": 2
                            },
                            "indices": 3,
                            "material": 0,
                            "mode": 4
                        }
                    ]
                }
            ],
            "accessors": [
                {
                    "bufferView": 0,
                    "componentType": 5126,  # FLOAT
                    "count": len(vertices),
                    "type": "VEC3",
                    "max": max_vals,
                    "min": min_vals
                },
                {
                    "bufferView": 1,
                    "componentType": 5126,  # FLOAT
                    "count": len(normals),
                    "type": "VEC3"
                },
                {
                    "bufferView": 2,
                    "componentType": 5126,  # FLOAT
                    "count": len(colors),
                    "type": "VEC3"
                },
                {
                    "bufferView": 3,
                    "componentType": 5125,  # UNSIGNED_INT
                    "count": len(faces_flat),
                    "type": "SCALAR"
                }
            ],
            "bufferViews": [
                {
                    "buffer": 0,
                    "byteOffset": 0,
                    "byteLength": len(vertices_flat) * 4
                },
                {
                    "buffer": 0,
                    "byteOffset": len(vertices_flat) * 4,
                    "byteLength": len(normals_flat) * 4
                },
                {
                    "buffer": 0,
                    "byteOffset": len(vertices_flat) * 4 + len(normals_flat) * 4,
                    "byteLength": len(colors_flat) * 4
                },
                {
                    "buffer": 0,
                    "byteOffset": len(vertices_flat) * 4 + len(normals_flat) * 4 + len(colors_flat) * 4,
                    "byteLength": len(faces_flat) * 4
                }
            ],
            "buffers": [
                {
                    "byteLength": (len(vertices_flat) + len(normals_flat) + len(colors_flat) + len(faces_flat)) * 4
                }
            ]
        }

        # Prepare binary buffer data
        buffer_data = (
            np.array(vertices_flat, dtype=np.float32).tobytes() +
            np.array(normals_flat, dtype=np.float32).tobytes() +
            np.array(colors_flat, dtype=np.float32).tobytes() +
            np.array(faces_flat, dtype=np.uint32).tobytes()
        )

        return gltf, buffer_data, geometry['metadata']
