$(document).ready(function () {
    $('#search-box').on('input', function () {
        const query = $(this).val().toLowerCase();
        $('#suggestions').empty();

        if (query.length > 0) {
            const filteredResults = resources.filter(resource => resource.name.startsWith(query));

            if (filteredResults.length > 0) {
                $.each(filteredResults, function (index, resource) {
                    $('#suggestions').append(`<li><a href="${generateUrl(resource.type, resource.name)}">${resource.name} (${resource.type})</a></li>`);
                });
            } else {
                $('#suggestions').append('<li>No results found</li>');
            }
        }
    });

    function generateUrl(resource, name) {
        const routes = {
            'pokemon': `/pokemon/${name}`,
            'berry': `/berry/${name}`,
            'ability': `/ability/${name}`,
            'item': `/item/${name}`,
            'move': `/move/${name}`,
            'berry-firmness': `/berry_firmness/${name}`,
            'berry-flavor': `/berry_flavor/${name}`,
            'contest-type': `/contest_type/${name}`,
            'egg-group': `/egg_group/${name}`,
            'encounter-condition': `/encounter_condition/${name}`,
            'encounter-condition-value': `/encounter_condition_value/${name}`,
            'encounter-method': `/encounter_method/${name}`,
            'evolution-trigger': `/evolution_trigger/${name}`,
            'gender': `/gender/${name}`,
            'generation': `/generation/${name}`,
            'growth-rate': `/growth_rate/${name}`,
            'item-attribute': `/item_attribute/${name}`,
            'item-category': `/item_category/${name}`,
            'item-fling-effect': `/item_fling_effect/${name}`,
            'item-pocket': `/item_pocket/${name}`,
            'language': `/language/${name}`,
            'location': `/location/${name}`,
            'location-area': `/location_area/${name}`,
            'move-ailment': `/move_ailment/${name}`,
            'move-battle-style': `/move_battle_style/${name}`,
            'move-category': `/move_category/${name}`,
            'move-damage-class': `/move_damage_class/${name}`,
            'move-learn-method': `/move_learn_method/${name}`,
            'move-target': `/move_target/${name}`,
            'nature': `/nature/${name}`,
            'pal-park-area': `/pal_park_area/${name}`,
            'pokeathlon-stat': `/pokeathlon_stat/${name}`,
            'pokedex': `/pokedex/${name}`,
            'pokemon-color': `/pokemon_color/${name}`,
            'pokemon-form': `/pokemon_form/${name}`,
            'pokemon-habitat': `/pokemon_habitat/${name}`,
            'pokemon-shape': `/pokemon_shape/${name}`,
            'pokemon-species': `/pokemon_species/${name}`,
            'region': `/region/${name}`,
            'stat': `/stat/${name}`,
            'type': `/type/${name}`,
            'version': `/version/${name}`,
            'version-group': `/version_group/${name}`,
        };
        return routes[resource] || '#';
    }
});
