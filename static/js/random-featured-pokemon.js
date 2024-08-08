document.addEventListener("DOMContentLoaded", function() {
    const maxPokemonId = 898; // Maximum number of Pokémon
    const numFeatured = 3; // Number of Pokémon to feature
    const featuredContainer = document.querySelector('.pokemon-grid');

    // Array of Pokémon that will be featured (can be expanded)
    const featuredPokemon = [];

    function getRandomInt(min, max) {
        return Math.floor(Math.random() * (max - min + 1)) + min;
    }

    function fetchPokemonData(id) {
        return fetch(`https://pokeapi.co/api/v2/pokemon/${id}`)
            .then(response => response.json())
            .then(data => {
                return {
                    name: data.name.charAt(0).toUpperCase() + data.name.slice(1),
                    type: data.types.map(typeInfo => typeInfo.type.name).join('/'),
                    sprite: `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/${id}.png`
                };
            });
    }

    function createPokemonCard(pokemon) {
        const card = document.createElement('div');
        card.classList.add('pokemon-card');

        const img = document.createElement('img');
        img.src = pokemon.sprite;
        img.alt = pokemon.name;

        const name = document.createElement('h3');
        name.textContent = pokemon.name;

        const type = document.createElement('p');
        type.textContent = `Type: ${pokemon.type}`;

        const link = document.createElement('a');
        link.href = `/pokemon/${pokemon.name.toLowerCase()}`;
        link.classList.add('details-link');
        link.textContent = 'View Details';

        card.appendChild(img);
        card.appendChild(name);
        card.appendChild(type);
        card.appendChild(link);

        return card;
    }

    function displayFeaturedPokemon() {
        featuredContainer.innerHTML = ''; // Clear any existing content

        const randomIds = new Set();
        while (randomIds.size < numFeatured) {
            randomIds.add(getRandomInt(1, maxPokemonId));
        }

        randomIds.forEach(id => {
            fetchPokemonData(id).then(pokemon => {
                const card = createPokemonCard(pokemon);
                featuredContainer.appendChild(card);
            });
        });
    }

    displayFeaturedPokemon();
});
