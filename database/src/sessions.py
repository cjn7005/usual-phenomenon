from database.src.db_utils import *
from database.src.models import Sessions

def get_all_sessions() -> list[Sessions]:
	sql = "SELECT * FROM sessions;"

	result = exec_get_all(sql)

	return [Sessions(row) for row in result]

def get_sessions(**kwargs) -> list[Sessions]:
	if not kwargs: return get_all_sessions()
	sql = "SELECT * FROM sessions WHERE\n"
	for i,key in enumerate(kwargs):
		sql += f"\t{key} = %({key})s"
		sql += ",\n" if i < len(kwargs)-1 else "\n"

	result = exec_get_all(sql,kwargs)

	return [Sessions(row) for row in result]


def create_sessions(**kwargs) -> Sessions:
	sql = "INSERT INTO sessions ("
	values = "VALUES("
	for i,key in enumerate(kwargs):
		sql += key
		values += f"%({key})s"
		sql += ", " if i < len(kwargs)-1 else ") "

		values += ", " if i < len(kwargs)-1 else ")"

	sql += values
	sql += "\nRETURNING *"

	result = exec_commit_returning(sql,kwargs)

	return Sessions(result)


def update_sessions(id: str, **kwargs) -> None:
	sql = "UPDATE sessions SET \n"
	for i,key in enumerate(kwargs):
		sql += f"{key} = %({key})s"
		sql += ",\n" if i < len(kwargs)-1 else "\n"

	sql += "\nWHERE id = %(id)s"

	kwargs["id"] = id
	exec_commit(sql,kwargs)


def delete_sessions(id: str) -> None:
	sql = "DELETE FROM sessions WHERE id = %(id)s"
	exec_commit(sql,{"id": id})


