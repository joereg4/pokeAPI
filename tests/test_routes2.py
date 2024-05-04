import pytest
from flask import Flask
from werkzeug.exceptions import BadRequest
from routes import get_endpoint_data

app = Flask(__name__)


def test_get_endpoint_data_with_int_id_or_name(mocker):
    mocker.patch('routes.render_template', return_value="Success")
    mocker.patch('sys.modules[__name__].some_function', return_value="Data")

    with app.test_request_context():
        result = get_endpoint_data("some-function", "1")
        assert result == "Success"


def test_get_endpoint_data_with_string_id_or_name(mocker):
    mocker.patch('routes.render_template', return_value="Success")
    mocker.patch('sys.modules[__name__].some_function', return_value="Data")

    with app.test_request_context():
        result = get_endpoint_data("some-function", "some_string")
        assert result == "Success"


def test_get_endpoint_data_with_invalid_endpoint():
    with app.test_request_context():
        with pytest.raises(BadRequest):
            get_endpoint_data("invalid-endpoint", "1")


def test_get_endpoint_data_with_endpoint_not_in_all(mocker):
    mocker.patch('routes.pokedex.__all__', new=["other_function"])

    with app.test_request_context():
        with pytest.raises(BadRequest):
            get_endpoint_data("some-function", "1")
