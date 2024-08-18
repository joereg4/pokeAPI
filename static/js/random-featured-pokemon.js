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
                return {
                    name: data.name.charAt(0).toUpperCase() + data.name.slice(1),
                    type: data.types.map(typeInfo => typeInfo.type.name).join('/'),
                    sprite: `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/${id}.png`
                };
            });
    }

    function createPokemonCard(pokemon) {
        const col = document.createElement('div');
        col.classList.add('col');

        const card = document.createElement('div');
        card.classList.add('card'); // Add Bootstrap's card class
        card.style.width = '100%'; // Use a responsive width instead of 1fr

        const img = document.createElement('img');
        img.src = pokemon.sprite;
        img.alt = pokemon.name;
        img.classList.add('card-img-top'); // Add Bootstrap's card image class

        const cardBody = document.createElement('div');
        cardBody.classList.add('card-body'); // Add Bootstrap's card body class

        const name = document.createElement('h5');
        name.classList.add('card-title'); // Add Bootstrap's card title class
        name.textContent = pokemon.name;

        const type = document.createElement('p');
        type.classList.add('card-text'); // Add Bootstrap's card text class
        type.textContent = `Type: ${pokemon.type}`;

        const link = document.createElement('a');
        link.href = `/pokemon/${pokemon.name.toLowerCase()}`;
        link.classList.add('btn', 'btn-primary'); // Add Bootstrap's button classes
        link.textContent = 'View Details';

        cardBody.appendChild(name);
        cardBody.appendChild(type);
        cardBody.appendChild(link);
        card.appendChild(img);
        card.appendChild(cardBody);
        col.appendChild(card);

        return col; // Return the entire column with the card inside
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
