from flask import jsonify

def ok(payload=None, status=200):
    return jsonify(payload or {}), status

def error(code, status=400, message=None):
    payload = {
        'error': (str(code).lower() if isinstance(code, str) else code),
        'code': (str(code).upper() if isinstance(code, str) else code),
    }
    if message:
        payload['message'] = message
    return jsonify(payload), status
