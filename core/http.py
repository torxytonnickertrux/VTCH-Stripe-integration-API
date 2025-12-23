from flask import jsonify

def ok(payload=None, status=200):
    return jsonify(payload or {}), status

def error(code, status=400):
    return jsonify({'error': code}), status
