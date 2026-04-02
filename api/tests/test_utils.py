"""
Modified from SWEN 610
"""

import requests
# The client (unittest) can only contact the server using RESTful API calls


# For API calls using GET.  params and header are defaulted to 'empty'

def get_rest_call(url, params = {}, get_header = {}, expected_code = 200):
    response = requests.get(url, params, headers = get_header)
    assert expected_code == response.status_code, f'Response code to {url} not {expected_code}'
    return response.json()

# For API calls using POST.  params and header are defaulted to 'empty'

def post_rest_call(url, json = {}, post_header = {}, params = {}, expected_code = 200):
    '''Implements a REST api using the POST verb'''
    response = requests.post(url, params, json, headers = post_header)
    assert expected_code == response.status_code, f'Response code to {url} not {expected_code}'
    return response.json() if expected_code != 204 else None

# For API calls using PUT.  params and header are defaulted to 'empty'

def put_rest_call(url, json = {}, params = {}, put_header = {},expected_code = 200):
    '''Implements a REST api using the PUT verb'''
    response = requests.put(url, json, params=params, headers = put_header)
    assert expected_code == response.status_code, f'Response code to {url} not {expected_code}'
    return response.json()

# For API calls using DELETE.  header is defaulted to 'empty'

def delete_rest_call(url, delete_header={}, expected_code = 200):
    '''Implements a REST api using the DELETE verb'''
    response = requests.delete(url, headers = delete_header)
    assert expected_code == response.status_code, f'Response code to {url} not {expected_code}'
    return response.json()