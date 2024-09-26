document.addEventListener("DOMContentLoaded", function () {
    const heroImages = document.getElementById('hero-images');
    const maxPokemonId = 898; // Adjust according to the maximum number of Pokémon in the API
    const containerWidth = heroImages.clientWidth;
    const containerHeight = heroImages.clientHeight;
    const baseSize = 70; // Base size for images

    // Row configurations: each entry is [number of images, size multiplier, top offset percentage]
    const rowConfigs = [
        [11, 3, -10],  // Row 1: 11 images, 3x base size, bottom
        [13, 2, 30],  // Row 2: 13 images, 2x base size, 30% from bottom
        [11, 1.5, 55]  // Row 3: 11 images, 1.5x base size, 55% from bottom
    ];

    // Set to keep track of used Pokémon IDs
    const usedPokemonIds = new Set();

    // Helper function to convert a string to title case
    function toTitleCase(str) {
        return str.replace(/\b\w/g, (char) => char.toUpperCase());
    }

    function getRandomInt(min, max) {
        return Math.floor(Math.random() * (max - min + 1)) + min;
    }

    function getUniquePokemonId() {
        let randomId;
        do {
            randomId = getRandomInt(1, maxPokemonId);
        } while (usedPokemonIds.has(randomId));
        usedPokemonIds.add(randomId);
        return randomId;
    }

    function createImageElement(src, size, name) {
        const img = document.createElement('img');
        img.src = src;
        img.alt = name;
        img.classList.add('hero-img');
        img.style.width = `${size}px`;
        img.style.height = `${size}px`;
        img.setAttribute('data-name', name); // Add data-name attribute for hover tooltip
        return img;
    }

    function createCellElement(pokemonName) {
        const cell = document.createElement('div');
        cell.classList.add('cell');
        cell.setAttribute('data-name', pokemonName); // Set the data-name attribute with the Pokémon name
        cell.style.pointerEvents = 'auto'; // Allow mouse events on cells
        return cell;
    }

    function positionImages(images, row, numCells, topOffsetPercentage, zIndex) {
        const rowHeight = containerHeight / rowConfigs.length;
        const rowTop = (containerHeight * topOffsetPercentage) / 100;
        const cellWidth = containerWidth / numCells;

        images.forEach((img, index) => {
            const size = parseInt(img.style.width);
            const leftPosition = index * cellWidth + (cellWidth - size) / 2;
            img.style.left = `${leftPosition}px`;
            img.style.bottom = `${rowTop}px`;
            img.style.position = 'absolute';
            img.style.zIndex = zIndex - 1; // Set z-index based on row

            // Create and style cell with the correct Pokémon name
            const cell = createCellElement(img.getAttribute('data-name')); // Pass the Pokémon name to the cell
            cell.style.width = `${cellWidth}px`;
            cell.style.height = `${rowHeight}px`;
            cell.style.left = `${index * cellWidth}px`;
            cell.style.bottom = `${rowTop}px`;
            cell.style.position = 'absolute';
            cell.style.zIndex = zIndex; // Set z-index for cell

            heroImages.appendChild(cell);
        });
    }

    // Image creation logic remains the same
    rowConfigs.forEach((config, row) => {
        const [numImages, sizeMultiplier, topOffsetPercentage] = config;
        const images = [];
        const zIndex = rowConfigs.length - row; // Higher z-index for front rows

        const imagePromises = []; // Array to hold promises for image creation

        for (let i = 0; i < numImages; i++) {
            const randomId = getUniquePokemonId(); // Get a unique Pokémon ID
            const size = baseSize * sizeMultiplier;
            const imgUrl = `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/${randomId}.png`;

            // Fetch Pokémon name from the PokeAPI and create the image element
            const imagePromise = fetch(`https://pokeapi.co/api/v2/pokemon/${randomId}`)
                .then(response => response.json())
                .then(data => {
                    const imgElement = createImageElement(imgUrl, size, toTitleCase(data.name)); // Convert name to title case
                    heroImages.appendChild(imgElement);
                    images.push(imgElement);
                });

            imagePromises.push(imagePromise); // Add the promise to the array
        }

        // Once all images are fetched and created, position them
        Promise.all(imagePromises).then(() => {
            positionImages(images, row, numImages, topOffsetPercentage, zIndex);
            addHoverEvents(); // Set up hover events AFTER images are appended
        });
    });

    function addHoverEvents() {
        let tooltip; // Declare a variable to hold the tooltip element

        heroImages.addEventListener('mouseover', function(e) {
            // Check if the hovered element has the class 'cell' and a valid data-name attribute
            if (e.target.classList.contains('cell') && e.target.getAttribute('data-name')) {
                // Create the tooltip element
                tooltip = document.createElement('div');
                tooltip.classList.add('tooltip');
                tooltip.innerText = e.target.getAttribute('data-name'); // Set the tooltip text to Pokémon name

                // Basic styling for the tooltip
                tooltip.style.position = 'absolute';
                tooltip.style.backgroundColor = '#333';
                tooltip.style.color = '#fff';
                tooltip.style.padding = '5px 10px';
                tooltip.style.borderRadius = '4px';
                tooltip.style.fontSize = '14px';
                tooltip.style.pointerEvents = 'none';
                tooltip.style.opacity = '0.8';
                tooltip.style.zIndex = '1000'; // Ensure tooltip appears above other elements

                // Append tooltip to the body
                document.body.appendChild(tooltip);

                // Get the position and dimensions of the hero-images container
                const heroRect = heroImages.getBoundingClientRect();
                const tooltipWidth = tooltip.clientWidth;
                const tooltipHeight = tooltip.clientHeight;

                // Position the tooltip at the top middle of the hero-images div
                tooltip.style.left = `${heroRect.left + (heroRect.width / 2) - (tooltipWidth / 2)}px`;
                tooltip.style.top = `${heroRect.top - tooltipHeight + 50}px`; // Adjust to position above hero-images div
            }
        });

        // Remove tooltip on mouseout
        heroImages.addEventListener('mouseout', function(e) {
            if (tooltip) {
                tooltip.remove(); // Remove the tooltip from the DOM
                tooltip = null; // Reset the tooltip variable
            }
        });
    }
});
