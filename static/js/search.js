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
            // Add other routes here
        };
        return routes[resource] || '#';
    }
});
