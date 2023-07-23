# api.py
# -*- coding: utf-8 -*-

import requests

from .cache import get_sprite_path, load, load_sprite, save, save_sprite
from .common import api_url_build, sprite_url_build


def _call_api(endpoint, resource_id=None, subresource=None):
    url = api_url_build(endpoint, resource_id, subresource)

    # Get a list of resources at the endpoint, if no resource_id is given.
    get_endpoint_list = resource_id is None

    response = requests.get(url)
    response.raise_for_status()

    data = response.json()
    data = filter_english_data(data)

    if get_endpoint_list and data["count"] != len(data["results"]):
        # We got a section of all results; we want ALL of them.
        items = data["count"]
        num_items = dict(limit=items)

        response = requests.get(url, params=num_items)
        response.raise_for_status()

        data = response.json()

    return data


def get_data(endpoint, resource_id=None, subresource=None, **kwargs):
    if not kwargs.get("force_lookup", False):
        try:
            data = load(endpoint, resource_id, subresource)
            return data
        except KeyError:
            pass

    data = _call_api(endpoint, resource_id, subresource)
    save(data, endpoint, resource_id, subresource)

    return data


def _call_sprite_api(sprite_type, sprite_id, **kwargs):
    url = sprite_url_build(sprite_type, sprite_id, **kwargs)

    response = requests.get(url)
    response.raise_for_status()

    abs_path = get_sprite_path(sprite_type, sprite_id, **kwargs)
    data = dict(img_data=response.content, path=abs_path)

    return data


def get_sprite(sprite_type, sprite_id, **kwargs):
    if not kwargs.get("force_lookup", False):
        try:
            data = load_sprite(sprite_type, sprite_id, **kwargs)
            return data
        except FileNotFoundError:
            pass

    data = _call_sprite_api(sprite_type, sprite_id, **kwargs)
    save_sprite(data, sprite_type, sprite_id, **kwargs)

    return data

def filter_english_data(data):
    filtered_data = data.copy()
    fields_to_filter = [
        "names",
        "effect_entries",
        "flavor_text_entries",
        "color",
        "genera",
        "habitat",
        "shape",
        "descriptions",
    ]

    for field in fields_to_filter:
        if field in filtered_data:
            entries = filtered_data[field]
            if isinstance(entries, list):
                filtered_entries = [
                    entry
                    for entry in entries
                    if entry.get("language", {}).get("name") == "en"
                ]
                filtered_data[field] = filtered_entries
            else:
                filtered_data[
                    field
                ] = None  # or handle the case when the field is not a list

    return filtered_data



