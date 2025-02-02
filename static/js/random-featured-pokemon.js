document.addEventListener("DOMContentLoaded", function() {
    const maxPokemonId = 898; // Maximum number of Pokémon
    const numFeatured = 4; // Number of Pokémon to feature
    const featuredContainer = document.getElementById('feature-section'); // Target the correct ID

    function getRandomInt(min, max) {
        return Math.floor(Math.random() * (max - min + 1)) + min;
    }

    function fetchPokemonData(id) {
        return fetch(`https://pokeapi.co/api/v2/pokemon/${id}`)
            .then(response => response.json())
            .then(data => {
                // Use the correct artwork endpoint URL
                const artworkUrl = `/artwork/${id}`;
                
                // First check if the artwork exists
                return fetch(artworkUrl)
                    .then(response => {
                        if (!response.ok) {
                            // If artwork doesn't exist, throw error to skip this Pokemon
                            throw new Error('No artwork available');
                        }
                        return {
                            name: data.name.charAt(0).toUpperCase() + data.name.slice(1),
                            type: data.types.map(typeInfo => typeInfo.type.name).join('/'),
                            sprite: artworkUrl
                        };
                    });
            });
    }

    function createPokemonCard(pokemon) {
        const col = document.createElement('div');
        col.classList.add('col');

        // Create the anchor wrapper
        const cardLink = document.createElement('a');
        cardLink.href = `/pokemon/${pokemon.name.toLowerCase()}`;
        cardLink.style.textDecoration = 'none';
        cardLink.style.color = 'inherit';
        cardLink.classList.add('card-hover');

        const card = document.createElement('div');
        card.classList.add('card');
        card.style.width = '100%';
        card.style.transition = 'transform 0.2s ease-in-out';

        const img = document.createElement('img');
        img.src = pokemon.sprite;
        img.alt = pokemon.name;
        img.classList.add('card-img-top');

        const cardBody = document.createElement('div');
        cardBody.classList.add('card-body');

        const name = document.createElement('h5');
        name.classList.add('card-title');
        name.textContent = pokemon.name;

        const type = document.createElement('p');
        type.classList.add('card-text');
        type.textContent = `Type: ${pokemon.type}`;

        cardBody.appendChild(name);
        cardBody.appendChild(type);
        card.appendChild(img);
        card.appendChild(cardBody);
        cardLink.appendChild(card);
        col.appendChild(cardLink);

        // Add hover effect
        cardLink.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-5px)';
            card.style.boxShadow = '0 4px 8px rgba(0,0,0,0.2)';
        });

        cardLink.addEventListener('mouseleave', () => {
            card.style.transform = 'translateY(0)';
            card.style.boxShadow = '';
        });

        return col;
    }

    function displayFeaturedPokemon() {
        featuredContainer.innerHTML = ''; // Clear any existing content

        const randomIds = new Set();
        const displayedCards = new Set();
        let attempts = 0;
        const maxAttempts = 50; // Prevent infinite loops

        function tryAddPokemon() {
            if (displayedCards.size >= numFeatured || attempts >= maxAttempts) {
                return;
            }

            const id = getRandomInt(1, maxPokemonId);
            if (!randomIds.has(id)) {
                randomIds.add(id);
                attempts++;

                fetchPokemonData(id)
                    .then(pokemon => {
                        if (displayedCards.size < numFeatured) {
                            const card = createPokemonCard(pokemon);
                            featuredContainer.appendChild(card);
                            displayedCards.add(id);
                        }
                    })
                    .catch(() => {
                        // If this Pokemon failed (no artwork), try another
                        tryAddPokemon();
                    });
            } else {
                tryAddPokemon();
            }
        }

        // Start adding Pokemon
        for (let i = 0; i < numFeatured * 2; i++) { // Try more than we need to ensure we get enough
            tryAddPokemon();
        }
    }

    displayFeaturedPokemon();
});
