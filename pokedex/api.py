import requests
from .cache import get_sprite_path, load, load_sprite, save, save_sprite
from .common import api_url_build, sprite_url_build


def _http_get(url, **params):
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response


def _call_api(endpoint, resource_id=None, subresource=None):
    url = api_url_build(endpoint, resource_id, subresource)
    get_endpoint_list = resource_id is None
    response = _http_get(url)

    data = filter_english_data(response.json())

    if get_endpoint_list and data["count"] != len(data["results"]):
        items = data["count"]
        response = _http_get(url, limit=items)
        data = response.json()
    return data


def get_data(endpoint, resource_id=None, subresource=None, **kwargs):
    force_lookup = kwargs.get("force_lookup", False)

    if not force_lookup:
        try:
            return load(endpoint, resource_id, subresource)
        except KeyError:
            pass
    data = _call_api(endpoint, resource_id, subresource)
    save(data, endpoint, resource_id, subresource)
    return data


def _call_sprite_api(sprite_type, sprite_id, **kwargs):
    url = sprite_url_build(sprite_type, sprite_id, **kwargs)
    response = _http_get(url)

    abs_path = get_sprite_path(sprite_type, sprite_id, **kwargs)
    data = dict(img_data=response.content, path=abs_path)
    return data


def get_sprite(sprite_type, sprite_id, **kwargs):
    force_lookup = kwargs.get("force_lookup", False)

    if not force_lookup:
        try:
            return load_sprite(sprite_type, sprite_id, **kwargs)
        except FileNotFoundError:
            pass
    data = _call_sprite_api(sprite_type, sprite_id, **kwargs)
    save_sprite(data, sprite_type, sprite_id, **kwargs)
    return data


def filter_english_data(data):
    print("Filter English")
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
        "version_group",
    ]
    for field in fields_to_filter:
        if field in filtered_data:
            entries = filtered_data[field]
            if isinstance(entries, list):
                filtered_entries = [
                    entry
                    for entry in entries
                    if isinstance(entry, dict) and
                       isinstance(entry.get("language", {}), dict) and
                       entry["language"].get("name") == "en"
                ]
                filtered_data[field] = filtered_entries
    return filtered_data
