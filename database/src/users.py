from database.src.db_utils import *
from database.src.models import Users

def get_all_users() -> list[Users]:
	sql = "SELECT * FROM users;"

	result = exec_get_all(sql)

	return [Users(row) for row in result]

def get_users(**kwargs) -> list[Users]:
	if not kwargs: return get_all_users()
	sql = "SELECT * FROM users WHERE\n"
	for i,key in enumerate(kwargs):
		sql += f"\t{key} = %({key})s"
		sql += ",\n" if i < len(kwargs)-1 else "\n"

	result = exec_get_all(sql,kwargs)

	return [Users(row) for row in result]


def create_users(**kwargs) -> Users:
	sql = "INSERT INTO users ("
	values = "VALUES("
	for i,key in enumerate(kwargs):
		sql += key
		values += f"%({key})s"
		sql += ", " if i < len(kwargs)-1 else ") "

		values += ", " if i < len(kwargs)-1 else ")"

	sql += values
	sql += "\nRETURNING *"

	result = exec_commit_returning(sql,kwargs)

	return Users(result)


def update_users(id: str, **kwargs) -> None:
	sql = "UPDATE users SET \n"
	for i,key in enumerate(kwargs):
		sql += f"{key} = %({key})s"
		sql += ",\n" if i < len(kwargs)-1 else "\n"

	sql += "\nWHERE id = %(id)s"

	kwargs["id"] = id
	exec_commit(sql,kwargs)


def delete_users(id: str) -> None:
	sql = "DELETE FROM users WHERE id = %(id)s"
	exec_commit(sql,{"id": id})


