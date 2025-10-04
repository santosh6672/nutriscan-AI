// static/js/result.js

document.addEventListener('DOMContentLoaded', () => {
    console.log('Result page loaded successfully');

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

    // Apply the toggle function to the Pros, Cons, and Alternatives lists
    const prosContainer = document.querySelector('.pros');
    const consContainer = document.querySelector('.cons');
    const alternativesContainer = document.querySelector('.alternatives-card');

    if (prosContainer) createToggleForList(prosContainer, 'li');
    if (consContainer) createToggleForList(consContainer, 'li');
    if (alternativesContainer) createToggleForList(alternativesContainer, 'li');

    // Add error handling for images
    document.querySelectorAll('img').forEach(img => {
        img.addEventListener('error', function() {
            console.log('Image failed to load:', this.alt);
            this.style.display = 'none';
        });
        
        img.addEventListener('load', function() {
            console.log('Image loaded successfully:', this.alt);
        });
    });
});