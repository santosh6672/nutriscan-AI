document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const elements = {
        scanForm: document.getElementById('scanForm'),
        fileInput: document.getElementById('id_image'),
        uploadArea: document.getElementById('uploadArea'),
        imagePreview: document.getElementById('imagePreview'),
        previewImage: document.getElementById('previewImage'),
        uploadContent: document.querySelector('.upload-area__content'),
        removeImageBtn: document.getElementById('removeImageBtn'),
        openCameraBtn: document.getElementById('openCameraBtn'),
        cameraContainer: document.getElementById('cameraContainer'),
        video: document.getElementById('cameraStream'),
        captureBtn: document.getElementById('captureBtn'),
        captureCanvas: document.getElementById('captureCanvas'),
        scanBtn: document.getElementById('scanBtn'),
        errorDiv: document.getElementById('errorMessages'),
        
        // UI Views
        inputView: document.getElementById('scan-input-view'),
        loadingView: document.getElementById('loading-view'),
        resultView: document.getElementById('scan-result-view'),
        
        // Result components
        resultImage: document.getElementById('resultImage'),
        resultMessage: document.getElementById('resultMessage'),
        barcodeData: document.getElementById('barcodeData'),
        barcodeValue: document.getElementById('barcodeValue'),
        analyzeBtn: document.getElementById('analyzeBtn'),
        scanAnotherBtn: document.getElementById('scanAnotherBtn'),
    };

    let cameraStream = null;

    // --- UI State Management ---
    /**
     * Controls which part of the UI is visible.
     * @param {'input' | 'loading' | 'result'} state 
     */
    function updateUIState(state) {
        elements.inputView.classList.toggle('d-none', state !== 'input');
        elements.loadingView.classList.toggle('d-none', state !== 'loading');
        elements.resultView.classList.toggle('d-none', state !== 'result');
    }

    // --- Helper Functions ---
    function showError(message) {
        elements.errorDiv.textContent = message;
        // Simple clear after 4 seconds
        setTimeout(() => { elements.errorDiv.textContent = ''; }, 4000);
    }
    
    function resetFileInput() {
        elements.fileInput.value = null; // Important for re-uploading the same file
    }

    function clearPreview() {
        resetFileInput();
        elements.imagePreview.classList.add('d-none');
        elements.uploadContent.classList.remove('d-none');
        elements.previewImage.src = '#';
        elements.scanBtn.disabled = true;
    }

    // --- Event Handlers ---
    function handleFileSelect(file) {
        if (!file || !file.type.startsWith('image/')) return;
        
        if (file.size > 5 * 1024 * 1024) { // 5MB limit
            showError('File is too large. Maximum size is 5MB.');
            resetFileInput();
            return;
        }

        const reader = new FileReader();
        reader.onload = e => {
            elements.previewImage.src = e.target.result;
            elements.uploadContent.classList.add('d-none');
            elements.imagePreview.classList.remove('d-none');
            elements.scanBtn.disabled = false;
        };
        reader.readAsDataURL(file);
    }
    
    // --- Core Logic (API Call) ---
    async function performScan() {
        if (!elements.fileInput.files.length) {
            showError('Please select an image first.');
            return;
        }

        updateUIState('loading');

        const formData = new FormData(elements.scanForm);

        try {
            const response = await fetch(scanUrl, {
                method: 'POST',
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                body: formData,
            });

            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }

            const result = await response.json();

            // Populate result view
            elements.resultImage.src = 'data:image/jpeg;base64,' + result.image_with_boxes;
            elements.resultMessage.textContent = result.message;
            elements.resultMessage.className = result.success ? 'alert alert-info' : 'alert alert-warning';
            
            if (result.barcode_data) {
                elements.barcodeData.classList.remove('d-none');
                elements.barcodeValue.textContent = result.barcode_data;
                elements.analyzeBtn.classList.remove('d-none');
            } else {
                elements.barcodeData.classList.add('d-none');
                elements.analyzeBtn.classList.add('d-none');
            }
            
            updateUIState('result');

        } catch (error) {
            showError(`An error occurred: ${error.message}`);
            updateUIState('input'); // Go back to input screen on error
        }
    }
    
    function resetToInitialState() {
        clearPreview();
        if (cameraStream) {
            cameraStream.getTracks().forEach(track => track.stop());
            cameraStream = null;
        }
        elements.cameraContainer.classList.add('d-none');
        updateUIState('input');
    }

    // --- Initialization & Event Listeners ---
    function init() {
        // Upload Area Click & Drag/Drop
        elements.uploadArea.addEventListener('click', () => elements.fileInput.click());
        elements.uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            elements.uploadArea.classList.add('dragover');
        });
        elements.uploadArea.addEventListener('dragleave', () => elements.uploadArea.classList.remove('dragover'));
        elements.uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            elements.uploadArea.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                elements.fileInput.files = e.dataTransfer.files;
                handleFileSelect(e.dataTransfer.files[0]);
            }
        });

        // File Input Change
        elements.fileInput.addEventListener('change', (e) => handleFileSelect(e.target.files[0]));
        
        // Remove Image Button
        elements.removeImageBtn.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent uploadArea's click event
            clearPreview();
        });

        // Camera Buttons
        elements.openCameraBtn.addEventListener('click', async () => {
            if (cameraStream) {
                cameraStream.getTracks().forEach(track => track.stop());
                cameraStream = null;
                elements.cameraContainer.classList.add('d-none');
                return;
            }
            try {
                cameraStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
                elements.video.srcObject = cameraStream;
                elements.cameraContainer.classList.remove('d-none');
            } catch (err) {
                showError('Camera access was denied or is not available.');
            }
        });

        elements.captureBtn.addEventListener('click', () => {
            const context = elements.captureCanvas.getContext('2d');
            elements.captureCanvas.width = elements.video.videoWidth;
            elements.captureCanvas.height = elements.video.videoHeight;
            context.drawImage(elements.video, 0, 0);

            elements.captureCanvas.toBlob(blob => {
                const file = new File([blob], "capture.jpg", { type: "image/jpeg" });
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                elements.fileInput.files = dataTransfer.files;
                handleFileSelect(file);
            }, 'image/jpeg');

            // Stop camera after capture
            if (cameraStream) {
                cameraStream.getTracks().forEach(track => track.stop());
                cameraStream = null;
            }
            elements.cameraContainer.classList.add('d-none');
        });

        // Main Action Buttons
        elements.scanBtn.addEventListener('click', performScan);
        elements.scanAnotherBtn.addEventListener('click', resetToInitialState);
        
        // Set initial state
        updateUIState('input');
    }
    
    init();
});