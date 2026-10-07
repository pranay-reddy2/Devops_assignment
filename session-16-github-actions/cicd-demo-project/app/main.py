"""HTTP API around the calculator so it can be containerised and deployed."""
import os

from flask import Flask, jsonify, request

from app.calculator import OPERATIONS

app = Flask(__name__)
APP_VERSION = os.environ.get("APP_VERSION", "dev")


@app.get("/")
def index():
    return jsonify(
        app="session16-calculator",
        version=APP_VERSION,
        usage="/api/calc?op=add&a=10&b=5",
        operations=sorted(OPERATIONS),
    )


@app.get("/health")
def health():
    return jsonify(status="ok", version=APP_VERSION)


@app.get("/api/calc")
def calc():
    op = request.args.get("op", "")
    if op not in OPERATIONS:
        return jsonify(error=f"unknown op '{op}'", operations=sorted(OPERATIONS)), 400
    try:
        a = float(request.args["a"])
        b = float(request.args["b"])
    except (KeyError, ValueError):
        return jsonify(error="a and b must be numbers"), 400
    try:
        result = OPERATIONS[op](a, b)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    return jsonify(op=op, a=a, b=b, result=result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
