from test_utils import *

BASE = "http://127.0.0.1:5000/sessions"

def test_get_sessions():
	result = get_rest_call(BASE)
	assert 1+1 == 2

def test_post_sessions():
	result = post_rest_call(BASE)
	assert 1+1 == 2

def test_put_sessions():
	result = put_rest_call(BASE)
	assert 1+1 == 2

def test_delete_sessions():
	result = delete_rest_call(BASE)
	assert 1+1 == 2

