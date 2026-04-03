from flask import Blueprint, jsonify, request
from database.src import sessions as db

sessions_bp = Blueprint("sessions",__name__,url_prefix="/sessions")

from api.src.users import users_bp
from api.src.sessions import sessions_bp

app = Flask(__name__)

app.register_blueprint(users_bp)
app.register_blueprint(sessions_bp)

@app.route('/')
def hello_world():
	return 'Hello world!'

if __name__ == "__main__":
	# python3 -m flask --app api/src/server.py run --debug
	if len(sys.argv) > 1:
		debug = sys.argv[1] == "--debug"
	else:
		debug = False
	app.run(debug=debug)
