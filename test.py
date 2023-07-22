import os

@app.route('/env')
def show_env():
    return {
        "FLASK_APP": os.environ.get("FLASK_APP"),
        "FLASK_ENV": os.environ.get("FLASK_ENV"),
        "FLASK_DEBUG": os.environ.get("FLASK_DEBUG")
    }