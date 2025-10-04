document.addEventListener('DOMContentLoaded', function() {
    // Cache DOM Elements
    const navTabs = document.querySelectorAll('.nav-tab');
    const profileSections = document.querySelectorAll('.profile-section');
    const updateBtns = document.querySelectorAll('.update-btn');
    const modal = document.getElementById('updateMetricModal');
    const modalTitle = document.getElementById('modalTitle');
    const metricInput = document.getElementById('metric-value');
    const saveMetricBtn = document.getElementById('saveMetric');
    const closeModalBtn = document.querySelector('.close-modal');
    const weightUnitInputs = document.querySelectorAll('input[name="weight_unit"]');
    const metricsChart = document.getElementById('metricsChart');

    let currentMetric = null;
    let chart = null;

    // Tab Navigation
    function switchTab(targetTab) {
        navTabs.forEach(tab => {
            if (tab.dataset.tab === targetTab) {
                tab.classList.add('active');
                tab.setAttribute('aria-selected', 'true');
            } else {
                tab.classList.remove('active');
                tab.setAttribute('aria-selected', 'false');
            }
        });

        profileSections.forEach(section => {
            if (section.id === targetTab) {
                section.hidden = false;
                section.setAttribute('aria-hidden', 'false');
            } else {
                section.hidden = true;
                section.setAttribute('aria-hidden', 'true');
            }
        });
    }

    navTabs.forEach(tab => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });

    // Metric Update Modal
    function openModal(metric, currentValue) {
        currentMetric = metric;
        modalTitle.textContent = `Update ${metric.charAt(0).toUpperCase() + metric.slice(1)}`;
        metricInput.value = currentValue;
        modal.classList.add('active');
        metricInput.focus();
        
        document.body.style.overflow = 'hidden';
    }

    function closeModal() {
        modal.classList.remove('active');
        currentMetric = null;
        metricInput.value = '';
        document.body.style.overflow = '';
    }

    updateBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const metric = btn.dataset.metric;
            const currentValue = document.querySelector(`[data-metric="${metric}"] .metric-value`).textContent;
            openModal(metric, parseFloat(currentValue));
        });
    });

    closeModalBtn.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });

    // Handle ESC key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('active')) {
            closeModal();
        }
    });

    // Save Metric Updates
    saveMetricBtn.addEventListener('click', async () => {
        if (!currentMetric || !metricInput.value) return;

        try {
            const response = await updateMetric(currentMetric, metricInput.value);
            if (response.ok) {
                const data = await response.json();
                updateMetricDisplay(currentMetric, data.value);
                closeModal();
                showNotification('Success', 'Metric updated successfully', 'success');
            } else {
                throw new Error('Failed to update metric');
            }
        } catch (error) {
            showNotification('Error', 'Failed to update metric', 'error');
        }
    });

    // API Calls
    async function updateMetric(metric, value) {
        return fetch('/api/update-metric/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                metric: metric,
                value: value
            })
        });
    }

    function getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]').value;
    }

    // Update Display
    function updateMetricDisplay(metric, value) {
        const displayElement = document.querySelector(`[data-metric="${metric}"] .metric-value`);
        if (displayElement) {
            displayElement.textContent = `${value} ${metric === 'weight' ? 'kg' : 'cm'}`;
        }
        updateBMI();
    }

    // BMI Calculation
    function updateBMI() {
        const weightElement = document.querySelector('[data-metric="weight"] .metric-value');
        const heightElement = document.querySelector('[data-metric="height"] .metric-value');
        const bmiDisplay = document.getElementById('bmi-display');
        const bmiStatus = document.getElementById('bmi-status');

        if (weightElement && heightElement && bmiDisplay && bmiStatus) {
            const weight = parseFloat(weightElement.textContent);
            const height = parseFloat(heightElement.textContent) / 100; // convert cm to m
            
            if (weight && height) {
                const bmi = weight / (height * height);
                bmiDisplay.textContent = bmi.toFixed(1);
                
                // Update BMI status
                const status = getBMIStatus(bmi);
                bmiStatus.textContent = status.label;
                bmiStatus.className = `metric-status ${status.class}`;
            }
        }
    }

    function getBMIStatus(bmi) {
        if (bmi < 18.5) return { label: 'Underweight', class: 'status-warning' };
        if (bmi < 25) return { label: 'Normal', class: 'status-success' };
        if (bmi < 30) return { label: 'Overweight', class: 'status-warning' };
        return { label: 'Obese', class: 'status-danger' };
    }

    // Notifications
    function showNotification(title, message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <strong>${title}</strong>
            <p>${message}</p>
        `;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('fade-out');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    // Initialize Chart
    function initializeMetricsChart() {
        if (!metricsChart) return;

        const ctx = metricsChart.getContext('2d');
        chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [], // Will be populated with dates
                datasets: [{
                    label: 'Weight (kg)',
                    data: [], // Will be populated with weight values
                    borderColor: '#16c498',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false
                    }
                }
            }
        });
    }

    // Load initial data
    async function loadMetricsHistory() {
        try {
            const response = await fetch('/api/metrics-history/');
            if (response.ok) {
                const data = await response.json();
                updateChart(data);
            }
        } catch (error) {
            console.error('Failed to load metrics history:', error);
        }
    }

    function updateChart(data) {
        if (!chart) return;

        chart.data.labels = data.dates;
        chart.data.datasets[0].data = data.weights;
        chart.update();
    }

    // Initialize
    updateBMI();
    initializeMetricsChart();
    loadMetricsHistory();

    // Handle unit preference changes
    weightUnitInputs.forEach(input => {
        input.addEventListener('change', function() {
            localStorage.setItem('weightUnit', this.value);
            updateMetricDisplays();
        });
    });

    // Set initial unit preference
    const savedWeightUnit = localStorage.getItem('weightUnit') || 'kg';
    document.querySelector(`input[name="weight_unit"][value="${savedWeightUnit}"]`).checked = true;
});
