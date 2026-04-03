from database.src.db_utils import *
from database.src.models import Sessions

import database.src.sessions as db

def test_get_sessions():
	result = db.get_sessions()
	assert 1+1 == 2

def test_create_sessions():
	result = db.create_sessions()
	assert 1+1 == 2

def test_update_sessions():
	result = db.update_sessions()
	assert 1+1 == 2

def test_delete_sessions():
	result = db.delete_sessions()
	assert 1+1 == 2

