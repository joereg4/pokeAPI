document.addEventListener("DOMContentLoaded", function() {
    const heroImages = document.getElementById('hero-images');
    const maxPokemonId = 898; // Adjust according to the maximum number of Pokémon in the API
    const containerWidth = heroImages.clientWidth;
    const containerHeight = heroImages.clientHeight;
    const baseSize = 70; // Base size for images

    // Row configurations: each entry is [number of images, size multiplier, top offset percentage]
    const rowConfigs = [
        [9, 3, -10],  // Row 1: 15 images, 3x base size, bottom
        [11, 2, 40],  // Row 2: 10 images, 2x base size, 40% from bottom
        [9, 1.5, 65]  // Row 3: 5 images, 1.5x base size, 70% from bottom
    ];

    function getRandomInt(min, max) {
        return Math.floor(Math.random() * (max - min + 1)) + min;
    }

    function createImageElement(src, size) {
        const img = document.createElement('img');
        img.src = src;
        img.alt = 'Pokémon';
        img.classList.add('hero-img');
        img.style.width = `${size}px`;
        img.style.height = `${size}px`;
        return img;
    }

    function createCellElement() {
        const cell = document.createElement('div');
        cell.classList.add('cell');
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
            img.style.zIndex = zIndex; // Set z-index based on row

            // Create and style cell
            const cell = createCellElement();
            cell.style.width = `${cellWidth}px`;
            cell.style.height = `${rowHeight}px`;
            cell.style.left = `${index * cellWidth}px`;
            cell.style.bottom = `${rowTop}px`;
            cell.style.position = 'absolute';;
            cell.style.zIndex = zIndex; // Set z-index for cell

            heroImages.appendChild(cell);
        });
    }

    rowConfigs.forEach((config, row) => {
        const [numImages, sizeMultiplier, topOffsetPercentage] = config;
        const images = [];
        const zIndex = rowConfigs.length - row; // Higher z-index for front rows
        for (let i = 0; i < numImages; i++) {
            const randomId = getRandomInt(1, maxPokemonId);
            const size = baseSize * sizeMultiplier;
            const imgUrl = `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/${randomId}.png`;
            const imgElement = createImageElement(imgUrl, size);
            heroImages.appendChild(imgElement);
            images.push(imgElement);
        }
        positionImages(images, row, numImages, topOffsetPercentage, zIndex);
    });
});
