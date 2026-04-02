import json

from database.src.db_utils import initialize_db


def main():
  dirs = ["api","database"]
  subdirs = ["src","tests"]
  models = "models.json"
  with open(models,"r") as f:
    modules = json.load(f)

  print(f"Generating backend from {models}")
  print("Models:")
  for module, attrs in modules.items():
    print(f"  {module}:")
    for i,item in enumerate(attrs):
      print(f"    {list(item.keys())[0]}: {list(item.values())[0]}{"," if i < len(attrs)-1 else ""}")

  #region SQL
  for module, attrs in modules.items():
    with open(f"database/schema/{module}.sql", "w") as f:
      f.write(f"CREATE TABLE IF NOT EXISTS {module} (\n")
      for i,attr in enumerate(attrs):
        f.write(f"\t{list(attr.keys())[0]} {list(attr.values())[0]}{" PRIMARY KEY" if i == 0 else ""}{"," if i < len(attrs)-1 else ""}\n")
      f.write(")\n")

  #endregion

  gen = ((direct, subdir, module) for direct in dirs for subdir in subdirs for module in modules)
  for (direct, subdir, module) in gen:
    with open(f"{direct}/{subdir}/{"test_" if subdir == "tests" else ""}{module}{"_api" if subdir == "tests" and direct == "api" else ""}.py", "w") as f:
      f.write("# Hello world!\n")

      #region API
      if direct == "api":

        if subdir == "src":
          f.write(
f"""
from flask import Blueprint, jsonify, request
from database.src import {module} as db

{module}_bp = Blueprint("{module}",__name__,url_prefix="/{module}")

"""
            )
          for method, db_method in zip(["get","post","put","delete"],
                                       ["get","insert","update","delete"]):
            f.write(
f"""
@{module}_bp.route('/', methods=["{method.upper()}"])
def {method}_{module}():
  result = db.{db_method}_{module}()
  return jsonify(result)

"""
            )


        elif subdir == "tests":
          f.write("from test_utils import *\n")
          f.write(f"BASE = \"http://127.0.0.1:5000/{module}\"\n")
          for method in ["get","post","put","delete"]:
            f.write(
f"""
def test_{method}_{module}():
    result = {method}_rest_call(BASE)
    assert 1+1 == 2

"""
            )
      #endregion

      #region Database
      elif direct == "database":
        f.write(
f"""
from database.src.db_utils import *

"""
            )
        
        if subdir == "src":
          for method in ["get","insert","update","delete"]:
            # if method == "get": sql = f"SELECT * FROM {module}"
            # if method == "insert": sql = f"INSERT INTO {module} VALUES() RETURNING id"
            # if method == "update": sql = f"UPDATE {module} SET id = 0"
            # if method == "delete": sql = f"DELETE FROM {module} WHERE TRUE"
            sql = f"SELECT * FROM {module}"
            f.write(
f"""
def {method}_{module}():
  sql = "{sql}"

  return exec_commit{"_returning" if method in ["get","insert"] else ""}(sql)

"""
            )


        elif subdir == "tests":
          f.write(f"import database.src.{module} as db\n")
          for method in ["get","insert","update","delete"]:
            f.write(
f"""
def test_{method}_{module}():
    result = db.{method}_{module}()
    assert 1+1 == 2

"""
            )
      #endregion
  
  #region Server
  with open("api/server.py", "w") as f:
    f.write(
f"""
from flask import Flask
import sys

"""
    )

    for module in modules:
      f.write(f"from api.src.{module} import {module}_bp\n\n")
      
    f.write("app = Flask(__name__)\n\n")

    for module in modules:
      f.write(f"app.register_blueprint({module}_bp)\n\n")

    f.write(
f"""
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

"""
    )

if __name__ == "__main__":
    main()
    initialize_db()
