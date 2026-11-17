"""Application entry point."""
from flask import Flask, send_from_directory

import api
import services


app = Flask(__name__, static_folder="static", static_url_path="/static")
app.register_blueprint(api.api)


@app.get("/")
def home():
    return send_from_directory(app.static_folder, "index.html")


@app.errorhandler(404)
def not_found(_error):
    return {"error": "Not found"}, 404


services.seed_foods()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
