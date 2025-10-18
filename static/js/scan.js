document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const elements = {
        scanForm: document.getElementById('scanForm'),
        fileInput: document.getElementById('id_image'),
        manualBarcodeInput: document.getElementById('manualBarcodeInput'),
        manualBarcodeText: document.getElementById('manualBarcodeText'),
        useManualBarcodeBtn: document.getElementById('useManualBarcodeBtn'),
        clearSessionBtn: document.getElementById('clearSessionBtn'),
        
        uploadArea: document.getElementById('uploadArea'),
        imagePreview: document.getElementById('imagePreview'),
        previewImage: document.getElementById('previewImage'),
        uploadContent: document.querySelector('.upload-area__content'),
        removeImageBtn: document.getElementById('removeImageBtn'),
        
        openCameraBtn: document.getElementById('openCameraBtn'),
        cameraContainer: document.getElementById('cameraContainer'),
        video: document.getElementById('cameraStream'),
        captureBtn: document.getElementById('captureBtn'),
        cancelCameraBtn: document.getElementById('cancelCameraBtn'),
        captureCanvas: document.getElementById('captureCanvas'),
        
        scanBtn: document.getElementById('scanBtn'),
        errorDiv: document.getElementById('errorMessages'),
        successDiv: document.getElementById('successMessages'),
        
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
        tryManualBtn: document.getElementById('tryManualBtn'),
    };

    let cameraStream = null;
    let currentBarcode = '';

    // --- UI State Management ---
    function updateUIState(state) {
        elements.inputView.classList.toggle('d-none', state !== 'input');
        elements.loadingView.classList.toggle('d-none', state !== 'loading');
        elements.resultView.classList.toggle('d-none', state !== 'result');
    }

    // --- Helper Functions ---
    function showError(message) {
        elements.errorDiv.textContent = message;
        elements.successDiv.classList.add('d-none');
        setTimeout(() => { elements.errorDiv.textContent = ''; }, 5000);
    }
    
    function showSuccess(message) {
        elements.successDiv.textContent = message;
        elements.successDiv.classList.remove('d-none');
        elements.errorDiv.textContent = '';
        setTimeout(() => { elements.successDiv.classList.add('d-none'); }, 3000);
    }
    
    function resetFileInput() {
        elements.fileInput.value = null;
    }

    function clearPreview() {
        resetFileInput();
        elements.imagePreview.classList.add('d-none');
        elements.uploadContent.classList.remove('d-none');
        elements.previewImage.src = '#';
        elements.scanBtn.disabled = true;
    }

    function validateBarcode(barcode) {
        // Basic barcode validation - numbers only, 8-13 digits
        const barcodeRegex = /^\d{8,13}$/;
        return barcodeRegex.test(barcode);
    }

    // --- Manual Barcode Handling ---
    function handleManualBarcode() {
        const barcode = elements.manualBarcodeText.value.trim();
        
        if (!barcode) {
            showError('Please enter a barcode number.');
            return;
        }
        
        if (!validateBarcode(barcode)) {
            showError('Please enter a valid barcode (8-13 digits, numbers only).');
            return;
        }
        
        // Set the hidden input value and submit the form
        elements.manualBarcodeInput.value = barcode;
        currentBarcode = barcode;
        
        showSuccess(`Barcode ${barcode} set successfully!`);
        
        // Enable analyze button if we have a valid barcode
        elements.analyzeBtn.disabled = false;
    }

    // --- Session Management ---
    async function clearScanSession() {
        try {
            const response = await fetch(clearSessionUrl, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': getCSRFToken(),
                },
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Clear local state
                elements.manualBarcodeText.value = '';
                elements.manualBarcodeInput.value = '';
                currentBarcode = '';
                clearPreview();
                showSuccess('Session cleared successfully!');
            } else {
                showError('Failed to clear session.');
            }
        } catch (error) {
            showError('Error clearing session: ' + error.message);
        }
    }

    function getCSRFToken() {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        return csrfToken ? csrfToken.value : '';
    }

    // --- File Handling ---
    function handleFileSelect(file) {
        if (!file || !file.type.startsWith('image/')) {
            showError('Please select a valid image file.');
            return;
        }
        
        if (file.size > 5 * 1024 * 1024) {
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
        reader.onerror = () => {
            showError('Error reading file. Please try another image.');
            resetFileInput();
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
            if (result.image_with_boxes) {
                elements.resultImage.src = 'data:image/jpeg;base64,' + result.image_with_boxes;
            }
            elements.resultMessage.textContent = result.message;
            elements.resultMessage.className = result.success ? 'alert alert-success' : 'alert alert-warning';
            
            if (result.barcode_data) {
                elements.barcodeData.classList.remove('d-none');
                elements.barcodeValue.textContent = result.barcode_data;
                currentBarcode = result.barcode_data;
                
                // Also update manual barcode field
                elements.manualBarcodeText.value = result.barcode_data;
                elements.manualBarcodeInput.value = result.barcode_data;
            } else {
                elements.barcodeData.classList.add('d-none');
            }
            
            updateUIState('result');

        } catch (error) {
            showError(`Scanning failed: ${error.message}`);
            updateUIState('input');
        }
    }
    
    function resetToInitialState() {
        clearPreview();
        stopCamera();
        updateUIState('input');
    }

    function stopCamera() {
        if (cameraStream) {
            cameraStream.getTracks().forEach(track => track.stop());
            cameraStream = null;
        }
        elements.cameraContainer.classList.add('d-none');
    }

    // --- Camera Functions ---
    async function initializeCamera() {
        try {
            cameraStream = await navigator.mediaDevices.getUserMedia({ 
                video: { 
                    facingMode: 'environment',
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                } 
            });
            elements.video.srcObject = cameraStream;
            elements.cameraContainer.classList.remove('d-none');
        } catch (err) {
            showError('Camera access was denied or is not available.');
            console.error('Camera error:', err);
        }
    }

    function captureFromCamera() {
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
            
            // Stop camera after capture
            stopCamera();
        }, 'image/jpeg', 0.8);
    }

    // --- Initialization & Event Listeners ---
    function init() {
        // Initialize with current barcode if available
        if (currentBarcode && validateBarcode(currentBarcode)) {
            elements.manualBarcodeText.value = currentBarcode;
            elements.manualBarcodeInput.value = currentBarcode;
            showSuccess(`Previous barcode loaded: ${currentBarcode}`);
        }

        // Manual Barcode Events
        elements.useManualBarcodeBtn.addEventListener('click', handleManualBarcode);
        elements.manualBarcodeText.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                handleManualBarcode();
            }
        });

        // Session Management
        elements.clearSessionBtn.addEventListener('click', clearScanSession);

        // Upload Area Events
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
            e.stopPropagation();
            clearPreview();
        });

        // Camera Events
        elements.openCameraBtn.addEventListener('click', async () => {
            if (cameraStream) {
                stopCamera();
                return;
            }
            await initializeCamera();
        });

        elements.captureBtn.addEventListener('click', captureFromCamera);
        elements.cancelCameraBtn.addEventListener('click', stopCamera);

        // Main Action Buttons
        elements.scanBtn.addEventListener('click', performScan);
        elements.scanAnotherBtn.addEventListener('click', resetToInitialState);
        elements.tryManualBtn.addEventListener('click', () => {
            resetToInitialState();
            elements.manualBarcodeText.focus();
        });
        
        // Set initial state
        updateUIState('input');
    }
    
    // Start the application
    init();
});