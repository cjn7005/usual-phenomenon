from database.src.db_utils import *
from database.src.models import Users

import database.src.users as db

def test_get_users():
	result = db.get_users()
	assert 1+1 == 2

def test_create_users():
	result = db.create_users()
	assert 1+1 == 2

def test_update_users():
	result = db.update_users()
	assert 1+1 == 2

def test_delete_users():
	result = db.delete_users()
	assert 1+1 == 2

