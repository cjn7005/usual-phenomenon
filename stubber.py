import json
import os
from typing import Dict

from database.src.db_utils import initialize_db

#region DB Methods

def make_gets(module: str, attrs: list[Dict[str,str]]) -> list[str]:
  all = \
   f"def get_all_{module}() -> list[{module.capitalize()}]:\n"\
   f"\tsql = \"SELECT * FROM {module};\"\n\n"\
    "\tresult = exec_get_all(sql)\n\n"\
   f"\treturn [{module.capitalize()}(row) for row in result]\n\n"
  
  queried = \
   f"def get_{module}(**kwargs) -> list[{module.capitalize()}]:\n"\
   f"\tif not kwargs: return get_all_{module}()\n"\
   f"\tsql = \"SELECT * FROM {module} WHERE\\n\"\n"\
   f"\tfor i,key in enumerate(kwargs):\n"\
    "\t\tsql += f\"\\t{key} = %({key})s\"\n"\
    "\t\tsql += \",\\n\" if i < len(kwargs)-1 else \"\\n\"\n\n"\
    "\tresult = exec_get_all(sql,kwargs)\n\n"\
   f"\treturn [{module.capitalize()}(row) for row in result]\n\n"

  return all, queried
  

def make_creates(module: str, attrs: list[Dict[str,str]]) -> list[str]:
  create = \
   f"def create_{module}(**kwargs) -> {module.capitalize()}:\n"\
   f"\tsql = \"INSERT INTO {module} (\"\n"\
    "\tvalues = \"VALUES(\"\n"\
    "\tfor i,key in enumerate(kwargs):\n"\
    "\t\tsql += key\n"\
    "\t\tvalues += f\"%({key})s\"\n"\
    "\t\tsql += \", \" if i < len(kwargs)-1 else \") \"\n\n"\
    "\t\tvalues += \", \" if i < len(kwargs)-1 else \")\"\n\n"\
   f"\tsql += values\n"\
   f"\tsql += \"\\nRETURNING *\"\n\n"\
    "\tresult = exec_commit_returning(sql,kwargs)\n\n"\
   f"\treturn {module.capitalize()}(result)\n\n"
  
  return create,


def make_updates(module: str, attrs: list[Dict[str,str]]) -> list[str]:
  update = \
   f"def update_{module}({list(attrs[0].keys())[0]}: {list(attrs[0].values())[0][0]}, **kwargs) -> None:\n"\
   f"\tsql = \"UPDATE {module} SET \\n\"\n"\
    "\tfor i,key in enumerate(kwargs):\n"\
    "\t\tsql += f\"{key} = %({key})s\"\n"\
    "\t\tsql += \",\\n\" if i < len(kwargs)-1 else \"\\n\"\n\n"\
   f"\tsql += \"\\nWHERE {list(attrs[0].keys())[0]} = %({list(attrs[0].keys())[0]})s\"\n\n"\
   f"\tkwargs[\"{list(attrs[0].keys())[0]}\"] = {list(attrs[0].keys())[0]}\n"\
    "\texec_commit(sql,kwargs)\n\n"\
  
  return update,


def make_deletes(module: str, attrs: list[Dict[str,str]]) -> list[str]:
  delete = \
   f"def delete_{module}({list(attrs[0].keys())[0]}: {list(attrs[0].values())[0][0]}) -> None:\n"\
   f"\tsql = \"DELETE FROM {module} WHERE {list(attrs[0].keys())[0]} = %({list(attrs[0].keys())[0]})s\"\n"\
    "\texec_commit(sql,{"\
   f"\"{list(attrs[0].keys())[0]}\": {list(attrs[0].keys())[0]}"\
    "})\n\n"\

  return delete,

#endregion

#region API Methods

def make_gets_api(module: str, attrs: list[Dict[str,str]]) -> list[str]:
  return []


def make_posts_api(module: str, attrs: list[Dict[str,str]]) -> list[str]:
  return []


def make_puts_api(module: str, attrs: list[Dict[str,str]]) -> list[str]:
  return []


def make_get_deletes_api(module: str, attrs: list[Dict[str,str]]) -> list[str]:
  return []

#endregion



def main():
  dirs = ["api","database"]
  subdirs = ["src","tests"]
  models = "models.json"
  with open(models,"r") as f:
    modules = json.load(f)

  os.makedirs("database/schema", exist_ok=True)
  os.makedirs("database/src", exist_ok=True)
  os.makedirs("database/tests", exist_ok=True)
  os.makedirs("api/src", exist_ok=True)
  os.makedirs("api/tests", exist_ok=True)

  print(f"Generating backend from {models}")
  print("Models:")
  for module, attrs in modules.items():
    print(f"  {module}:")
    for i,item in enumerate(attrs):
      print(f"    {list(item.keys())[0]}: {list(item.values())[0][1]}{"," if i < len(attrs)-1 else ""}")

  #region Models

  with open("database/src/models.py","w") as f:
    f.write("from pydantic import BaseModel\n\n")
    for module, attrs in modules.items():
      f.write(f"class {module.capitalize()}(BaseModel):\n")
      for attr in attrs:
        f.write(f"\t{list(attr.keys())[0]}: {list(attr.values())[0][0]}\n")
      f.write("\n\tdef __init__(self, *args):\n")
      for i,attr in enumerate(attrs):
        f.write(f"\t\tself.{list(attr.keys())[0]} = args[{i}]\n")
      f.write("\n\n")

  #endregion

  #region SQL

  for module, attrs in modules.items():
    with open(f"database/schema/{module}.sql", "w") as f:
      f.write(f"CREATE TABLE IF NOT EXISTS {module} (\n")
      for i,attr in enumerate(attrs):
        f.write(f"\t{list(attr.keys())[0]} {list(attr.values())[0][1]} {list(attr.values())[0][2] if len(list(attr.values())[0]) > 2 else ""} {"PRIMARY KEY" if i == 0 else ""}{"," if i < len(attrs)-1 else ""}\n")
      f.write(");\n")

  #endregion

  gen = ((direct, subdir, module) for direct in dirs for subdir in subdirs for module in modules)
  for (direct, subdir, module) in gen:
    with open(f"{direct}/{subdir}/{"test_" if subdir == "tests" else ""}{module}{"_api" if subdir == "tests" and direct == "api" else ""}.py", "w") as f:

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
from database.src.models import {module.capitalize()}

"""
            )
        
        if subdir == "src":
          for method in [make_gets,make_creates,make_updates,make_deletes]:
            for function in method(module, attrs):
              f.write(function)
            f.write("\n")

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

    #endregion

if __name__ == "__main__":
    main()
    initialize_db()
