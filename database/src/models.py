from pydantic import BaseModel

class Users(BaseModel):
	id: str
	username: str

	def __init__(self, *args):
		self.id = args[0]
		self.username = args[1]


class Sessions(BaseModel):
	id: str
	session_key: str

	def __init__(self, *args):
		self.id = args[0]
		self.session_key = args[1]


