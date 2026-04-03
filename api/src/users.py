from flask import Blueprint, jsonify, request
from database.src import users as db

users_bp = Blueprint("users",__name__,url_prefix="/users")

@users_bp.route('/<id>', methods=["GET"])
def get_users_from_pk(id: str):
	result = db.get_users(id=id)
	if result is not None:
		return jsonify([row.__dict__ for row in result]), 200
	else:
		return jsonify({"error": f"User {id} not found"}), 404

@users_bp.route('/', methods=["GET"])
def get_users_from_query():
	result = db.get_users(request.args)
	if result is not None:
		return jsonify([row.__dict__ for row in result]), 200
	else:
		return jsonify([]), 204


@users_bp.route('/', methods=["POST"])
def post_users():
	result = db.create_users(request.json)
	return jsonify(result.__dict__), 201


@users_bp.route('/<id>', methods=["PUT"])
def put_users(id: str):
	result = db.update_users(id, request.args)
	return jsonify(result.__dict__), 200


@users_bp.route('/<id>', methods=["DELETE"])
def delete_users(id: str):
	result = db.delete_users(id)
	return jsonify(), 204


