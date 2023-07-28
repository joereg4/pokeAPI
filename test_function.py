import pytest
from pokedex import utils


def test_get_data_valid_endpoint():
    endpoint = 'pokemon'  # replace with an actual valid endpoint
    result = utils.get_data(endpoint)
    print(result)

    # Other assertions based on the expected structure and content of the result


def test_call_api():
    endpoint = 'pokemon'  # replace with an actual valid endpoint
    result = utils._call_api(endpoint)
    print(result)
