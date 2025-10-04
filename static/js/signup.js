
// signup.js: Refactored to update Django form fields directly from display inputs

document.addEventListener('DOMContentLoaded', function() {
    // Django form fields
    const weightKgInput = document.getElementById('id_weight_kg');
    const heightCmInput = document.getElementById('id_height_cm');
    // Display inputs
    const weightDisplayInput = document.getElementById('weight-display-input');
    const heightCmDisplayInput = document.getElementById('height-cm-display-input');
    const heightFtDisplayInput = document.getElementById('height-ft-display-input');
    const heightInDisplayInput = document.getElementById('height-in-display-input');
    // Groups and toggles
    const heightCmGroup = document.getElementById('height-cm-display-group');
    const heightFtGroup = document.getElementById('height-ft-display-group');
    const unitToggleButtons = document.querySelectorAll('.unit-btn');

    // ⭐️ NEW: Get the BMI output element ⭐️
    const bmiOutput = document.getElementById('bmi-output');

    if (weightKgInput) weightKgInput.style.display = 'none';
    if (heightCmInput) heightCmInput.style.display = 'none';

    // ⭐️ NEW: Function to calculate and display BMI ⭐️
    function calculateAndDisplayBMI() {
        const weightKg = parseFloat(weightKgInput.value) || 0;
        const heightM = (parseFloat(heightCmInput.value) || 0) / 100;

        if (weightKg > 0 && heightM > 0) {
            const bmi = weightKg / (heightM * heightM);
            bmiOutput.textContent = bmi.toFixed(1);
            if (bmi < 18.5) {
                bmiOutput.style.color = '#3b82f6'; // Underweight
            } else if (bmi < 25) {
                bmiOutput.style.color = '#10b981'; // Normal
            } else if (bmi < 30) {
                bmiOutput.style.color = '#f59e0b'; // Overweight
            } else {
                bmiOutput.style.color = '#ef4444'; // Obese
            }
        } else {
            bmiOutput.textContent = '--';
            bmiOutput.style.color = 'inherit';
        }
    }

    function updateFormValues() {
        // Weight
        const activeWeightUnit = document.querySelector('.unit-btn[data-target="weight"].active').dataset.unit;
        const weightDisplayVal = parseFloat(weightDisplayInput.value) || 0;
        if (weightDisplayVal > 0) {
            weightKgInput.value = (activeWeightUnit === 'lb')
                ? (weightDisplayVal * 0.453592).toFixed(2)
                : weightDisplayVal.toFixed(2);
        } else {
            weightKgInput.value = '';
        }
        // Height
        const activeHeightUnit = document.querySelector('.unit-btn[data-target="height"].active').dataset.unit;
        let heightInCm = 0;
        if (activeHeightUnit === 'cm') {
            heightInCm = parseFloat(heightCmDisplayInput.value) || 0;
        } else {
            const feet = parseFloat(heightFtDisplayInput.value) || 0;
            const inches = parseFloat(heightInDisplayInput.value) || 0;
            heightInCm = (feet * 30.48) + (inches * 2.54);
        }
        heightCmInput.value = heightInCm > 0 ? heightInCm.toFixed(2) : '';

        // ⭐️ NEW: Call the BMI function after updating values ⭐️
        calculateAndDisplayBMI();
    }

    unitToggleButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            this.parentElement.querySelectorAll('.unit-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            if (this.dataset.target === 'height') {
                const isCm = this.dataset.unit === 'cm';
                heightCmGroup.style.display = isCm ? 'block' : 'none';
                heightFtGroup.style.display = isCm ? 'none' : 'flex';
            }
            updateFormValues();
        });
    });

    [weightDisplayInput, heightCmDisplayInput, heightFtDisplayInput, heightInDisplayInput].forEach(input => {
        if (input) input.addEventListener('input', updateFormValues);
    });
});
