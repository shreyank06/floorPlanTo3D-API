"""
Test script for Three.js integration
Tests the 3D generation functionality
"""

import requests
import json
import os

def test_3d_generation(image_path, output_path='test_output.gltf'):
    """
    Test the 3D generation endpoint

    Args:
        image_path: Path to floor plan image
        output_path: Path to save the glTF output
    """
    print("Testing 3D Generation API...")
    print(f"Input image: {image_path}")

    # Check if image exists
    if not os.path.exists(image_path):
        print(f"Error: Image file not found at {image_path}")
        print("\nPlease provide a valid floor plan image path.")
        return False

    # API endpoint
    url = 'http://127.0.0.1:5000/generate3d'

    # Prepare request
    try:
        with open(image_path, 'rb') as img_file:
            files = {'image': img_file}
            data = {
                'wall_height': 3.0,
                'wall_thickness': 0.15,
                'door_height': 2.1,
                'window_height': 1.2,
                'window_sill_height': 0.9
            }

            print("\nSending request to API...")
            response = requests.post(url, files=files, data=data)

            if response.status_code == 200:
                result = response.json()

                # Print detection results
                print("\n✓ API Response Successful!")
                print("\nDetection Results:")
                print(f"  - Image dimensions: {result['detection']['Width']}x{result['detection']['Height']}")
                print(f"  - Detected elements: {len(result['detection']['classes'])}")

                # Count element types
                walls = sum(1 for c in result['detection']['classes'] if c['name'] == 'wall')
                doors = sum(1 for c in result['detection']['classes'] if c['name'] == 'door')
                windows = sum(1 for c in result['detection']['classes'] if c['name'] == 'window')

                print(f"    • Walls: {walls}")
                print(f"    • Doors: {doors}")
                print(f"    • Windows: {windows}")

                # Print 3D model metadata
                print("\n3D Model Metadata:")
                metadata = result['metadata']
                print(f"  - Wall height: {metadata['wall_height']}m")
                print(f"  - Wall thickness: {metadata['wall_thickness']}m")
                print(f"  - Vertices: {metadata['num_vertices']}")
                print(f"  - Faces: {metadata['num_faces']}")

                # Save glTF output
                gltf_data = result['gltf']
                with open(output_path, 'w') as f:
                    json.dump(gltf_data, f, indent=2)

                print(f"\n✓ glTF model saved to: {output_path}")
                print("\nYou can view this file:")
                print("  - Online: https://gltf-viewer.donmccurdy.com/")
                print("  - Blender: File → Import → glTF 2.0")
                print("  - Web viewer: http://127.0.0.1:5000/viewer")

                return True
            else:
                print(f"\n✗ API Error: Status code {response.status_code}")
                print(response.text)
                return False

    except requests.exceptions.ConnectionError:
        print("\n✗ Connection Error: Could not connect to the API server.")
        print("\nPlease ensure:")
        print("  1. The Flask server is running (python application.py)")
        print("  2. The server is accessible at http://127.0.0.1:5000")
        return False
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        return False


def test_detection_only(image_path):
    """
    Test the original detection endpoint (without 3D generation)

    Args:
        image_path: Path to floor plan image
    """
    print("\nTesting Detection API (original endpoint)...")

    if not os.path.exists(image_path):
        print(f"Error: Image file not found at {image_path}")
        return False

    url = 'http://127.0.0.1:5000/'

    try:
        with open(image_path, 'rb') as img_file:
            files = {'image': img_file}
            response = requests.post(url, files=files)

            if response.status_code == 200:
                result = response.json()
                print("✓ Detection successful!")
                print(f"  - Detected elements: {len(result['classes'])}")
                return True
            else:
                print(f"✗ Error: Status code {response.status_code}")
                return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("FloorPlan to 3D - Integration Test")
    print("=" * 60)

    # Check for test images
    image_folder = './images'

    if os.path.exists(image_folder):
        test_images = [f for f in os.listdir(image_folder)
                      if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

        if test_images:
            print(f"\nFound {len(test_images)} test images in ./images/")
            test_image = os.path.join(image_folder, test_images[0])
            print(f"Using: {test_image}")

            # Run tests
            print("\n" + "=" * 60)
            test_detection_only(test_image)

            print("\n" + "=" * 60)
            test_3d_generation(test_image)

        else:
            print("\nNo test images found in ./images/")
            print("Please add a floor plan image to the ./images/ folder")
    else:
        print("\n./images/ folder not found")
        print("Please provide a floor plan image path:")
        print("\nUsage:")
        print("  python test_3d_integration.py")
        print("\nOr manually test:")
        print("  test_3d_generation('path/to/your/floorplan.jpg')")

    print("\n" + "=" * 60)
