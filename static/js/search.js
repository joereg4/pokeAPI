/**
 * search.js – Navbar autocomplete powered by /api/search (PostgreSQL-backed).
 *
 * Features:
 *   - Debounced input (150 ms) to avoid flooding the server
 *   - Fetches from /api/search?q=<term>&limit=10
 *   - Ranked results: prefix matches first, then substring matches
 *   - Keyboard navigation (arrow keys + Enter)
 *   - Escapes HTML to prevent XSS
 *   - Graceful error handling (silently hides suggestions on failure)
 */
$(document).ready(function () {
    var debounceTimer = null;
    var DEBOUNCE_MS = 150;
    var highlightIndex = -1; // currently highlighted suggestion (-1 = none)

    var $searchBox = $('#search-box');
    var $suggestions = $('#suggestions');

    // ---- helpers ----

    /**
     * Escape HTML special characters to prevent XSS when rendering
     * user-controlled or DB-sourced strings into the dropdown.
     */
    function escapeHtml(str) {
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    }

    function generateUrl(type, name) {
        return '/' + encodeURIComponent(type) + '/' + encodeURIComponent(name);
    }

    function showDropdown() {
        if (!$suggestions.hasClass('show')) {
            $suggestions.addClass('show');
            $searchBox.attr('aria-expanded', 'true');
        }
    }

    function hideDropdown() {
        $suggestions.removeClass('show');
        $searchBox.attr('aria-expanded', 'false');
        highlightIndex = -1;
    }

    function highlightItem(index) {
        var $items = $suggestions.find('.dropdown-item');
        $items.removeClass('active');
        highlightIndex = index;
        if (index >= 0 && index < $items.length) {
            $items.eq(index).addClass('active');
            // Scroll into view if needed
            $items[index].scrollIntoView({ block: 'nearest' });
        }
    }

    // ---- main search handler ----

    function performSearch() {
        var query = $searchBox.val().trim();
        $suggestions.empty();
        highlightIndex = -1;

        if (query.length === 0) {
            hideDropdown();
            return;
        }

        $.ajax({
            url: '/api/search',
            data: { q: query, limit: 10 },
            dataType: 'json',
            timeout: 3000, // 3-second client timeout
            success: function (results) {
                $suggestions.empty();
                highlightIndex = -1;

                if (!results || results.length === 0) {
                    hideDropdown();
                    return;
                }

                var query = $searchBox.val().trim();
                $.each(results, function (_i, resource) {
                    var safeName = escapeHtml(resource.name);
                    var safeType = escapeHtml(resource.type);
                    var href = generateUrl(resource.type, resource.name);
                    var safeQuery = escapeHtml(query);
                    $suggestions.append(
                        '<li><a class="dropdown-item" data-search-query="' + safeQuery + '" href="' + href + '">' +
                        safeName + ' <span class="text-muted">(' + safeType + ')</span></a></li>'
                    );
                });

                showDropdown();
            },
            error: function () {
                // Silently hide on error – don't disrupt the user
                hideDropdown();
            }
        });
    }

    // ---- event bindings ----

    // Debounced input handler
    $searchBox.on('input', function () {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(performSearch, DEBOUNCE_MS);
    });

    // Keyboard navigation
    $searchBox.on('keydown', function (e) {
        var $items = $suggestions.find('.dropdown-item');
        if ($items.length === 0) return;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            highlightItem(Math.min(highlightIndex + 1, $items.length - 1));
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            highlightItem(Math.max(highlightIndex - 1, 0));
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (highlightIndex >= 0 && highlightIndex < $items.length) {
                var $selected = $items.eq(highlightIndex);
                var q = $selected.attr('data-search-query') || $searchBox.val().trim();
                if (typeof gtag === 'function' && q) {
                    gtag('event', 'search', { search_term: q });
                }
                window.location.href = $selected.attr('href');
            }
        } else if (e.key === 'Escape') {
            hideDropdown();
        }
    });

    // GA4 search event when user selects a result (click or Enter)
    $suggestions.on('click', '.dropdown-item', function (e) {
        var q = $(this).attr('data-search-query') || $searchBox.val().trim();
        if (typeof gtag === 'function' && q) {
            gtag('event', 'search', { search_term: q });
        }
    });

    // Hide dropdown when clicking outside
    $(document).on('click', function (e) {
        if (!$(e.target).closest('.dropdown').length) {
            hideDropdown();
        }
    });
});
