// static/js/result.js

document.addEventListener('DOMContentLoaded', () => {
    // Result page loaded

    // Initialize the page with animations and interactions
    initializePage();

    // Function to create a "Show More/Less" toggle for long lists
    const createToggleForList = (listContainer, itemSelector) => {
        const listElement = listContainer.querySelector('ul');
        if (!listElement) return;
        
        const items = listElement.querySelectorAll(itemSelector);
        const maxVisible = 3; // Show the first 3 items

        if (items.length > maxVisible) {
            // Add data attribute to track state
            listContainer.setAttribute('data-expanded', 'false');
            
            // Hide items beyond the maxVisible limit
            for (let i = maxVisible; i < items.length; i++) {
                items[i].classList.add('hidden-item');
            }

            // Check if toggle button already exists
            if (!listContainer.querySelector('.toggle-list-button')) {
                // Create and append the "Show More" button
                const toggleButton = document.createElement('a');
                toggleButton.href = '#';
                toggleButton.textContent = `Show ${items.length - maxVisible} More...`;
                toggleButton.className = 'toggle-list-button';
                listContainer.appendChild(toggleButton);

                // Add click event listener to the button
                toggleButton.addEventListener('click', (e) => {
                    e.preventDefault(); // Prevent page jump
                    const isExpanded = listContainer.getAttribute('data-expanded') === 'true';

                    if (isExpanded) {
                        // Collapse the list
                        for (let i = maxVisible; i < items.length; i++) {
                            items[i].classList.add('hidden-item');
                        }
                        toggleButton.textContent = `Show ${items.length - maxVisible} More...`;
                        listContainer.setAttribute('data-expanded', 'false');
                    } else {
                        // Expand the list
                        for (let i = maxVisible; i < items.length; i++) {
                            items[i].classList.remove('hidden-item');
                        }
                        toggleButton.textContent = 'Show Less';
                        listContainer.setAttribute('data-expanded', 'true');
                    }
                });
            }
        }
    };

    // Apply the toggle function to the Pros and Cons lists
    const prosContainer = document.querySelector('.pros');
    const consContainer = document.querySelector('.cons');

    if (prosContainer) createToggleForList(prosContainer, 'li');
    if (consContainer) createToggleForList(consContainer, 'li');

    // Add error handling for images
    document.querySelectorAll('img').forEach(img => {
        img.addEventListener('error', function() {
            this.style.display = 'none';
            
            // Show placeholder if it exists
            const placeholder = this.nextElementSibling;
            if (placeholder && placeholder.classList.contains('product-image-placeholder')) {
                placeholder.style.display = 'block';
            }
        });
        
        img.addEventListener('load', function() {});
    });

    // Add smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Initialize any interactive elements
    function initializePage() {
    // Initializing result page
        
        // Add loading states for images
        const images = document.querySelectorAll('img[data-src]');
        images.forEach(img => {
            img.src = img.getAttribute('data-src');
        });

        // Add animation delays for staggered animations
        const animatedElements = document.querySelectorAll('.animate__animated');
        animatedElements.forEach((element, index) => {
            element.style.animationDelay = `${index * 0.1}s`;
        });

        // Initialize tooltips if any
        initializeTooltips();

        // Add print functionality enhancement
        enhancePrintFunctionality();
    }

    // Tooltip initialization (if needed)
    function initializeTooltips() {
        const elementsWithTooltip = document.querySelectorAll('[data-toggle="tooltip"]');
        elementsWithTooltip.forEach(element => {
            element.addEventListener('mouseenter', showTooltip);
            element.addEventListener('mouseleave', hideTooltip);
        });
    }

    function showTooltip(e) {
        const tooltipText = this.getAttribute('data-title');
        if (!tooltipText) return;

        const tooltip = document.createElement('div');
        tooltip.className = 'custom-tooltip';
        tooltip.textContent = tooltipText;
        document.body.appendChild(tooltip);

        const rect = this.getBoundingClientRect();
        tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
        tooltip.style.top = rect.top - tooltip.offsetHeight - 5 + 'px';
    }

    function hideTooltip() {
        const tooltip = document.querySelector('.custom-tooltip');
        if (tooltip) {
            tooltip.remove();
        }
    }

    // Enhanced print functionality
    function enhancePrintFunctionality() {
        const printButton = document.querySelector('.btn-print');
        if (printButton) {
            printButton.addEventListener('click', () => {
                // Add print-specific classes before printing
                document.body.classList.add('printing');
                
                setTimeout(() => {
                    window.print();
                    // Remove print classes after a delay
                    setTimeout(() => {
                        document.body.classList.remove('printing');
                    }, 1000);
                }, 500);
            });
        }
    }

    // Add keyboard navigation
    document.addEventListener('keydown', (e) => {
        // Escape key to go back to scan page
        if (e.key === 'Escape') {
            const scanAgainBtn = document.querySelector('.btn-scan-again');
            if (scanAgainBtn) {
                scanAgainBtn.click();
            }
        }
        
        // Print with Ctrl+P (override default)
        if (e.ctrlKey && e.key === 'p') {
            e.preventDefault();
            window.print();
        }
    });

    // Performance monitoring
    const pageLoadTime = performance.now();
    // Page load time (ms): ${pageLoadTime}

    // Send analytics event (if you have analytics)
    if (typeof gtag !== 'undefined') {
        gtag('event', 'page_view', {
            'page_title': 'Analysis Result',
            'page_location': window.location.href
        });
    }
});

// Add some basic CSS for tooltips
const style = document.createElement('style');
style.textContent = `
    .custom-tooltip {
        position: fixed;
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 5px 10px;
        border-radius: 4px;
        font-size: 0.8rem;
        z-index: 10000;
        pointer-events: none;
        max-width: 200px;
        text-align: center;
    }
    
    .printing .btn-scan-again,
    .printing .btn-print,
    .printing .toggle-list-button {
        display: none !important;
    }
`;
document.head.appendChild(style);