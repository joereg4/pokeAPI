document.addEventListener("DOMContentLoaded", function () {
    const heroImages = document.getElementById('hero-images');
    const maxPokemonId = 898; // Adjust according to the maximum number of Pokémon in the API
    const containerWidth = heroImages.clientWidth;
    const containerHeight = heroImages.clientHeight;
    const baseSize = 70; // Base size for images

    // Detect if we're on a mobile device
    const isMobile = window.innerWidth <= 768;

    // Row configurations: each entry is [number of images, size multiplier, top offset percentage]
    const rowConfigs = isMobile ? [
        [5, 3, -10],   // Mobile: Row 1: 5 images, 3x base size, bottom
        [7, 2, 30],    // Mobile: Row 2: 7 images, 2x base size, middle
        [5, 1.5, 55]   // Mobile: Row 3: 5 images, 1.5x base size, top
    ] : [
        [11, 3, -10],  // Desktop: Row 1: 11 images, 3x base size, bottom
        [13, 2, 30],   // Desktop: Row 2: 13 images, 2x base size, middle
        [11, 1.5, 55]  // Desktop: Row 3: 11 images, 1.5x base size, top
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
        // Create the image element
        const img = document.createElement('img');
        img.src = src;
        img.alt = name;
        img.classList.add('hero-img');
        img.style.width = `${size}px`;
        img.style.height = `${size}px`;
        img.setAttribute('data-name', name); // Add data-name attribute for possible tooltip
        img.title = name; // Set the title attribute for native browser tooltip

        return img; // Return the image element
    }

    function createCellElementWithAnchor(pokemonName) {
        // Create a new anchor element
        const anchor = document.createElement('a');
        anchor.href = `/pokemon/${pokemonName.toLowerCase()}`; // Set the href attribute with lowercase Pokémon name
        anchor.target = "_self"; // Ensure the link opens in the same tab

        // Create the cell element
        const cell = document.createElement('div');
        cell.classList.add('cell');
        cell.setAttribute('data-name', pokemonName); // Set the data-name attribute with the Pokémon name
        cell.style.pointerEvents = 'auto'; // Allow mouse events on cells
        cell.style.position = 'relative'; // Position relative for proper tooltip placement

        // Append the cell element to the anchor
        anchor.appendChild(cell);

        return anchor; // Return the anchor element with the cell inside
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

            // Create and style cell with the correct Pokémon name and anchor
            const anchor = createCellElementWithAnchor(img.getAttribute('data-name')); // Create anchor with cell
            anchor.style.width = `${cellWidth}px`;
            anchor.style.height = `${rowHeight}px`;
            anchor.style.left = `${index * cellWidth}px`;
            anchor.style.bottom = `${rowTop}px`;
            anchor.style.position = 'absolute';
            anchor.style.zIndex = zIndex; // Set z-index for anchor

            // Append the cell and anchor (with the image inside) to the heroImages container
            heroImages.appendChild(anchor);
            heroImages.appendChild(img);
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
                    images.push(imgElement); // Push the image to the images array
                });

            imagePromises.push(imagePromise); // Add the promise to the array
        }

        // Once all images are fetched and created, position them
        Promise.all(imagePromises).then(() => {
            positionImages(images, row, numImages, topOffsetPercentage, zIndex);
            // No need to add hover events as title attribute will show tooltip natively
        });
    });

    // Add window resize handler to reload the page when switching between mobile and desktop
    let lastIsMobile = isMobile;
    window.addEventListener('resize', () => {
        const currentIsMobile = window.innerWidth <= 768;
        if (currentIsMobile !== lastIsMobile) {
            location.reload();
        }
    });
});
