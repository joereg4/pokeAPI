# UI Changelog (historical)

Notes from an earlier UI improvement pass. Kept for reference; see git history for details.

## Item display

- Fixed sprite rendering in item_detail.html (96px dimensions)
- Improved container styling with shadows and padding
- Reorganized item detail header (name, sprite, edit icon in a row)

## Move category

- Reusable formatter for category names
- Bootstrap badges; error handling for missing data
- Fixed description duplication

## Move damage class template

- Added move_damage_class_detail.html for physical, special, and status moves

## Move detail

- Damage class badges link to move-damage-class route
- Removed duplicate damage class information

## Type display

- Replaced type image nameplates with colored badges on type_detail and pokemon_detail

## General

- Consistent type badge colors
- Generation names formatted with uppercase Roman numerals
