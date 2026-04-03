from flask import Blueprint, jsonify, request
from database.src import sessions as db

sessions_bp = Blueprint("sessions",__name__,url_prefix="/sessions")

@sessions_bp.route('/<id>', methods=["GET"])
def get_sessions_from_pk(id: str):
	result = db.get_sessions(id=id)
	if result is not None:
		return jsonify([row.__dict__ for row in result]), 200
	else:
		return jsonify({"error": f"Session {id} not found"}), 404

@sessions_bp.route('/', methods=["GET"])
def get_sessions_from_query():
	result = db.get_sessions(request.args)
	if result is not None:
		return jsonify([row.__dict__ for row in result]), 200
	else:
		return jsonify([]), 204


@sessions_bp.route('/', methods=["POST"])
def post_sessions():
	result = db.create_sessions(request.json)
	return jsonify(result.__dict__), 201


@sessions_bp.route('/<id>', methods=["PUT"])
def put_sessions(id: str):
	result = db.update_sessions(id, request.args)
	return jsonify(result.__dict__), 200


@sessions_bp.route('/<id>', methods=["DELETE"])
def delete_sessions(id: str):
	result = db.delete_sessions(id)
	return jsonify(), 204


