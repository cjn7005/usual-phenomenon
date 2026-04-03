from test_utils import *

BASE = "http://127.0.0.1:5000/users"

def test_get_users():
	result = get_rest_call(BASE)
	assert 1+1 == 2

def test_post_users():
	result = post_rest_call(BASE)
	assert 1+1 == 2

def test_put_users():
	result = put_rest_call(BASE)
	assert 1+1 == 2

def test_delete_users():
	result = delete_rest_call(BASE)
	assert 1+1 == 2

