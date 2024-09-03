$(document).ready(function () {
    $('#search-box').on('input', function () {
        const query = $(this).val().toLowerCase();
        const $suggestions = $('#suggestions');
        $suggestions.empty(); // Clear previous suggestions

        if (query.length > 0) {
            const filteredResults = resources.filter(resource => resource.name.startsWith(query));

            if (filteredResults.length > 0) {
                // Populate the suggestions dropdown
                $.each(filteredResults, function (index, resource) {
                    $suggestions.append(`<li><a class="dropdown-item" href="${generateUrl(resource.type, resource.name)}">${resource.name} (${resource.type})</a></li>`);
                });

                // Manually add the show class to display the dropdown
                if (!$suggestions.hasClass('show')) {
                    $suggestions.addClass('show');
                    $('#search-box').attr('aria-expanded', true);
                }
            } else {
                // Hide dropdown if no results found
                $suggestions.removeClass('show');
                $('#search-box').attr('aria-expanded', false);
            }
        } else {
            // Hide dropdown if input is empty
            $suggestions.removeClass('show');
            $('#search-box').attr('aria-expanded', false);
        }
    });

    // Hide dropdown when clicking outside
    $(document).click(function (e) {
        if (!$(e.target).closest('.dropdown').length) {
            $('#suggestions').removeClass('show');
            $('#search-box').attr('aria-expanded', false);
        }
    });

    function generateUrl(resource, name) {
        // Replace any hyphen in the resource with an underscore
        const updatedResource = resource.replace(/-/g, '_');
        return `/${updatedResource}/${name}`;
    }
});
