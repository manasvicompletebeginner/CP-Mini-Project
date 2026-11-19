"""
app.py - Flask REST API + page server for the Student Expense Splitter.

UNIT V (Flask):
  * Routes with GET and POST methods.
  * `request` object: request.get_json() for POST bodies, request.args for query strings.
  * `jsonify` builds JSON responses; send_file streams the PNG chart and CSV.
  * @app.errorhandler turns our custom exceptions into JSON error responses.

Run:  python app.py   then open http://127.0.0.1:5000
"""
import os
from datetime import date

from flask import Flask, jsonify, render_template, request, send_file

from splitter import JSONStorage, RoomService, SplitterError, export_expenses_csv
from splitter.analytics import spending_chart_png, summarize
from splitter.exceptions import ValidationError
from splitter.validators import validate_username

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "rooms_data.json")
EXPORT_DIR = os.path.join(BASE_DIR, "exports")

app = Flask(__name__)
app.json.ensure_ascii = False             # keep ₹ readable in JSON
service = RoomService(JSONStorage(DATA_FILE))


# ---------------- helpers & error handling ----------------
def json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object.")
    return data


def truthy(value):
    return str(value).lower() in {"1", "true", "yes", "on"}      # set literal


@app.errorhandler(SplitterError)
def handle_splitter_error(error):
    return jsonify(error.to_dict()), error.status_code


@app.errorhandler(404)
def handle_not_found(error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "NotFound", "message": "No such API route."}), 404
    return error


@app.errorhandler(500)
def handle_server_error(error):
    return jsonify({"error": "ServerError", "message": "Unexpected server error."}), 500


# ---------------- pages ----------------
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


# ---------------- users ----------------
@app.route("/api/login", methods=["POST"])
def login():
    body = json_body()
    return jsonify(service.login(body.get("username"))), 200


@app.route("/api/users/<username>/rooms", methods=["GET"])
def user_rooms(username):
    active, previous = service.rooms_for_user(username, owner_only=truthy(request.args.get("owner_only")))
    return jsonify({"active": active, "previous": previous})


@app.route("/api/users/<username>/summary", methods=["GET"])
def user_summary(username):
    active, previous = service.rooms_for_user(username)
    return jsonify(summarize(active, previous))


@app.route("/api/users/<username>/chart.png", methods=["GET"])
def user_chart(username):
    _, previous = service.rooms_for_user(username)
    return send_file(spending_chart_png(previous, validate_username(username)), mimetype="image/png")


@app.route("/api/users/<username>/export.csv", methods=["GET"])
def user_export(username):
    username = validate_username(username)
    _, previous = service.rooms_for_user(username)
    filename = f"{username}_expenses_{date.today().isoformat()}.csv"
    path = os.path.join(EXPORT_DIR, filename)
    export_expenses_csv(previous, path)
    return send_file(path, mimetype="text/csv", as_attachment=True, download_name=filename)


# ---------------- rooms ----------------
@app.route("/api/rooms", methods=["POST"])
def create_room():
    body = json_body()
    room = service.create_room(
        owner=body.get("username"),
        room_name=body.get("room_name", ""),
        activity=body.get("activity"),
        date=body.get("date"),
        total_amount=body.get("total_amount"),
        total_people=body.get("total_people"),
        split_type=body.get("split_type", "equal"),
        custom_shares=body.get("custom_shares"),
    )
    return jsonify(room), 201


@app.route("/api/rooms/<code>", methods=["GET"])
def get_room(code):
    return jsonify(service.get_room(code, viewer=request.args.get("username")))


@app.route("/api/rooms/<code>/join", methods=["POST"])
def join_room(code):
    body = json_body()
    return jsonify(service.join_room(code, body.get("username")))


@app.route("/api/rooms/<code>/pay", methods=["POST"])
def pay_room(code):
    body = json_body()
    room = service.pay(code, body.get("username"))
    message = f"Payment recorded. {room['name']} moved to your Previous Rooms."
    return jsonify({"room": room, "message": message})


if __name__ == "__main__":
    app.run(debug=True)
