import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

class FloorPlanViewer {
    constructor() {
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.currentModel = null;
        this.currentFile = null;
        this.gltfData = null;

        this.initViewer();
        this.setupEventListeners();
    }

    initViewer() {
        const container = document.getElementById('viewer3d');

        // Create scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x1a1a2e);  // Dark blue-gray for better contrast

        // Create camera
        this.camera = new THREE.PerspectiveCamera(
            60,
            container.clientWidth / container.clientHeight,
            0.1,
            1000
        );
        this.camera.position.set(10, 10, 10);
        this.camera.lookAt(0, 0, 0);

        // Create renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(container.clientWidth, container.clientHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        container.appendChild(this.renderer.domElement);

        // Add orbit controls
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.screenSpacePanning = false;
        this.controls.minDistance = 2;
        this.controls.maxDistance = 50;
        // Allow viewing from any angle (including top-down bird's eye view)
        // this.controls.maxPolarAngle = Math.PI / 2;  // Removed to allow top-down view

        // Add lights
        this.setupLights();

        // Add grid helper with better colors for dark background
        const gridHelper = new THREE.GridHelper(20, 20, 0x444444, 0x222222);
        this.scene.add(gridHelper);

        // Add axes helper
        const axesHelper = new THREE.AxesHelper(5);
        this.scene.add(axesHelper);

        // Handle window resize
        window.addEventListener('resize', () => this.onWindowResize());

        // Start animation loop
        this.animate();
    }

    setupLights() {
        // Brighter ambient light
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
        this.scene.add(ambientLight);

        // Main directional light (sun)
        const directionalLight = new THREE.DirectionalLight(0xffffff, 1.0);
        directionalLight.position.set(10, 20, 10);
        directionalLight.castShadow = true;
        directionalLight.shadow.camera.left = -20;
        directionalLight.shadow.camera.right = 20;
        directionalLight.shadow.camera.top = 20;
        directionalLight.shadow.camera.bottom = -20;
        directionalLight.shadow.mapSize.width = 2048;
        directionalLight.shadow.mapSize.height = 2048;
        this.scene.add(directionalLight);

        // Additional directional light from opposite side
        const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.6);
        directionalLight2.position.set(-10, 15, -10);
        this.scene.add(directionalLight2);

        // Hemisphere light for better ambient lighting
        const hemisphereLight = new THREE.HemisphereLight(0xffffff, 0x444444, 0.6);
        hemisphereLight.position.set(0, 20, 0);
        this.scene.add(hemisphereLight);
    }

    setupEventListeners() {
        const imageInput = document.getElementById('imageInput');
        const generateBtn = document.getElementById('generateBtn');
        const exportBtn = document.getElementById('exportBtn');
        const uploadSection = document.getElementById('uploadSection');
        const topViewBtn = document.getElementById('topViewBtn');

        // File input change
        imageInput.addEventListener('change', (e) => this.handleFileSelect(e));

        // Generate button click
        generateBtn.addEventListener('click', () => this.generate3DModel());

        // Export button click
        exportBtn.addEventListener('click', () => this.exportGLTF());

        // Top view button click
        topViewBtn.addEventListener('click', () => this.setBirdsEyeView());

        // Drag and drop
        uploadSection.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadSection.classList.add('dragover');
        });

        uploadSection.addEventListener('dragleave', () => {
            uploadSection.classList.remove('dragover');
        });

        uploadSection.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadSection.classList.remove('dragover');

            const files = e.dataTransfer.files;
            if (files.length > 0 && files[0].type.startsWith('image/')) {
                imageInput.files = files;
                this.handleFileSelect({ target: { files: files } });
            }
        });
    }

    handleFileSelect(event) {
        const file = event.target.files[0];
        if (!file) return;

        this.currentFile = file;

        // Show preview
        const reader = new FileReader();
        reader.onload = (e) => {
            const previewImage = document.getElementById('previewImage');
            const previewContainer = document.getElementById('previewContainer');

            previewImage.src = e.target.result;
            previewContainer.style.display = 'block';

            document.getElementById('generateBtn').disabled = false;
            this.showStatus('info', 'Image loaded. Click "Generate 3D Model" to continue.');
        };
        reader.readAsDataURL(file);
    }

    async generate3DModel() {
        if (!this.currentFile) return;

        const generateBtn = document.getElementById('generateBtn');
        generateBtn.disabled = true;
        generateBtn.textContent = 'Generating...';

        this.showStatus('info', 'Processing floor plan...');
        document.getElementById('viewerOverlay').innerHTML =
            '<div><div class="spinner"></div>Generating 3D model...</div>';
        document.getElementById('viewerOverlay').classList.remove('hidden');

        try {
            // Prepare form data
            const formData = new FormData();
            formData.append('image', this.currentFile);
            formData.append('wall_height', document.getElementById('wallHeight').value);
            formData.append('wall_thickness', document.getElementById('wallThickness').value);
            formData.append('door_height', document.getElementById('doorHeight').value);
            formData.append('window_height', document.getElementById('windowHeight').value);
            formData.append('window_sill_height', document.getElementById('windowSillHeight').value);

            // Make API request
            const response = await fetch('/generate3d', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }

            const data = await response.json();
            console.log('API Response:', data);

            this.gltfData = data.gltf;

            // Update info panel
            this.updateInfoPanel(data.metadata, data.detection);

            // Load the 3D model
            await this.loadGLTFModel(data.gltf);

            this.showStatus('success', '3D model generated successfully!');
            document.getElementById('exportBtn').style.display = 'block';
            document.getElementById('infoPanel').style.display = 'block';

        } catch (error) {
            console.error('Error generating 3D model:', error);
            this.showStatus('error', `Failed to generate 3D model: ${error.message}`);
            document.getElementById('viewerOverlay').classList.remove('hidden');
            document.getElementById('viewerOverlay').textContent =
                'Error generating 3D model. Please try again.';
        } finally {
            generateBtn.disabled = false;
            generateBtn.textContent = 'Generate 3D Model';
        }
    }

    async loadGLTFModel(gltfData) {
        // Clear existing model
        if (this.currentModel) {
            this.scene.remove(this.currentModel);
            this.currentModel.traverse((child) => {
                if (child.geometry) child.geometry.dispose();
                if (child.material) {
                    if (Array.isArray(child.material)) {
                        child.material.forEach(mat => mat.dispose());
                    } else {
                        child.material.dispose();
                    }
                }
            });
        }

        return new Promise((resolve, reject) => {
            const loader = new GLTFLoader();

            // Convert glTF object to JSON string for loading
            const gltfJson = JSON.stringify(gltfData);
            const gltfBlob = new Blob([gltfJson], { type: 'application/json' });
            const gltfUrl = URL.createObjectURL(gltfBlob);

            loader.load(
                gltfUrl,
                (gltf) => {
                    console.log('glTF loaded successfully:', gltf);
                    this.currentModel = gltf.scene;

                    console.log('Model children count:', this.currentModel.children.length);

                    // Enhance materials and add edges for better visibility
                    let meshCount = 0;
                    this.currentModel.traverse((child) => {
                        if (child.isMesh) {
                            meshCount++;
                            console.log('Found mesh:', child.name, 'geometry vertices:', child.geometry.attributes.position.count);

                            // Make material double-sided and configure transparency
                            if (child.material) {
                                child.material.side = THREE.DoubleSide;
                                child.material.transparent = true;
                                child.material.opacity = 0.95; // Slightly transparent for better viewing

                                // Make ceiling more transparent for bird's eye view
                                const positions = child.geometry.attributes.position;
                                if (positions) {
                                    let highestY = -Infinity;
                                    for (let i = 0; i < positions.count; i++) {
                                        const y = positions.getY(i);
                                        if (y > highestY) highestY = y;
                                    }
                                    // If most vertices are at the top (ceiling), make it very transparent
                                    if (highestY > 2.5) {
                                        child.material.opacity = 0.15; // Very transparent ceiling
                                        console.log('Made ceiling transparent');
                                    }
                                }

                                child.material.needsUpdate = true;
                            }

                            // Add edge geometry for better visibility
                            const edges = new THREE.EdgesGeometry(child.geometry, 15);
                            const lineMaterial = new THREE.LineBasicMaterial({
                                color: 0xffffff,  // White edges on dark background
                                linewidth: 2,
                                transparent: true,
                                opacity: 0.6
                            });
                            const lineSegments = new THREE.LineSegments(edges, lineMaterial);
                            child.add(lineSegments);
                        }
                    });

                    console.log('Total meshes found:', meshCount);

                    // Calculate bounding box to center and scale model
                    const box = new THREE.Box3().setFromObject(this.currentModel);
                    const center = box.getCenter(new THREE.Vector3());
                    const size = box.getSize(new THREE.Vector3());

                    console.log('Model bounding box:', {
                        min: box.min,
                        max: box.max,
                        center: center,
                        size: size
                    });

                    // Center model
                    this.currentModel.position.x = -center.x;
                    this.currentModel.position.y = -box.min.y;  // Floor at y=0
                    this.currentModel.position.z = -center.z;

                    // Add model to scene
                    this.scene.add(this.currentModel);

                    // Add bounding box helper to visualize model bounds
                    const boxHelper = new THREE.BoxHelper(this.currentModel, 0x00ff00);
                    this.scene.add(boxHelper);
                    console.log('Added green bounding box helper');

                    // Adjust camera to view entire model from a better angle
                    const maxDim = Math.max(size.x, size.y, size.z);
                    const fov = this.camera.fov * (Math.PI / 180);
                    let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2));
                    cameraZ *= 2.0; // More padding for better initial view

                    console.log('Camera position:', {
                        x: cameraZ * 0.8,
                        y: cameraZ * 0.6,
                        z: cameraZ * 0.8
                    });

                    this.camera.position.set(cameraZ * 0.8, cameraZ * 0.6, cameraZ * 0.8);
                    this.camera.lookAt(0, size.y / 2, 0);
                    this.controls.target.set(0, size.y / 2, 0);
                    this.controls.update();

                    // Hide overlay
                    document.getElementById('viewerOverlay').classList.add('hidden');

                    // Clean up blob URL
                    URL.revokeObjectURL(gltfUrl);

                    console.log('Model loaded and positioned successfully');
                    resolve();
                },
                (progress) => {
                    console.log('Loading progress:', progress);
                },
                (error) => {
                    console.error('Error loading glTF:', error);
                    console.error('Error details:', error.message, error.stack);
                    URL.revokeObjectURL(gltfUrl);

                    document.getElementById('viewerOverlay').classList.remove('hidden');
                    document.getElementById('viewerOverlay').textContent =
                        'Error loading 3D model. Check console for details.';

                    reject(error);
                }
            );
        });
    }

    updateInfoPanel(metadata, detection) {
        document.getElementById('wallCount').textContent = metadata.num_walls || 0;
        document.getElementById('doorCount').textContent = metadata.num_doors || 0;
        document.getElementById('windowCount').textContent = metadata.num_windows || 0;
        document.getElementById('vertexCount').textContent = metadata.num_vertices || 0;
        document.getElementById('faceCount').textContent = metadata.num_faces || 0;
    }

    showStatus(type, message) {
        const statusEl = document.getElementById('statusMessage');
        statusEl.className = `status-message ${type}`;
        statusEl.textContent = message;
        statusEl.style.display = 'block';

        if (type === 'success' || type === 'error') {
            setTimeout(() => {
                statusEl.style.display = 'none';
            }, 5000);
        }
    }

    exportGLTF() {
        if (!this.gltfData) {
            alert('No 3D model to export');
            return;
        }

        // Convert glTF object to JSON string
        const gltfJson = JSON.stringify(this.gltfData, null, 2);
        const blob = new Blob([gltfJson], { type: 'application/json' });

        // Create download link
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'floorplan_3d_model.gltf';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        this.showStatus('success', 'glTF file exported successfully!');
    }

    setBirdsEyeView() {
        if (!this.currentModel) {
            alert('Please generate a 3D model first');
            return;
        }

        // Calculate model center and size
        const box = new THREE.Box3().setFromObject(this.currentModel);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());

        // Position camera directly above the model
        const maxDim = Math.max(size.x, size.z); // Use x and z for top-down view
        const height = maxDim * 1.2; // Camera height above model

        this.camera.position.set(center.x, center.y + height, center.z);
        this.camera.lookAt(center.x, center.y, center.z);
        this.controls.target.set(center.x, center.y, center.z);
        this.controls.update();

        console.log('Switched to bird\'s eye view');
    }

    onWindowResize() {
        const container = document.getElementById('viewer3d');
        this.camera.aspect = container.clientWidth / container.clientHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(container.clientWidth, container.clientHeight);
    }

    animate() {
        requestAnimationFrame(() => this.animate());

        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }
}

// Initialize viewer when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new FloorPlanViewer();
});
