import json
import os
from typing import Dict

from database.src.db_utils import initialize_db

#region Headers
# imports, globals, etc.

headers = {
  "api/src": lambda module: (
    "from flask import Blueprint, jsonify, request\n"\
   f"from database.src import {module} as db\n\n"\
   f"{module}_bp = Blueprint(\"{module}\",__name__,url_prefix=\"/{module}\")\n\n"
  ),

  "api/tests": lambda module: (
    "from test_utils import *\n\n"\
    f"BASE = \"http://127.0.0.1:5000/{module}\"\n\n"
  ),

  "database" : lambda module: (
    "from database.src.db_utils import *\n"\
   f"from database.src.models import {module.capitalize()}\n\n"
  ),

  "database/tests" : lambda module: (
    f"import database.src.{module} as db\n\n"
  ),

  "server" : lambda module: (
    "from flask import Flask\n"\
    "import sys\n\n"
  )
}

#endregion

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
  pk = list(attrs[0].keys())[0]
  pk_type = list(attrs[0].values())[0][0]
  
  update = \
   f"def update_{module}({pk}: {pk_type}, **kwargs) -> None:\n"\
   f"\tsql = \"UPDATE {module} SET \\n\"\n"\
    "\tfor i,key in enumerate(kwargs):\n"\
    "\t\tsql += f\"{key} = %({key})s\"\n"\
    "\t\tsql += \",\\n\" if i < len(kwargs)-1 else \"\\n\"\n\n"\
   f"\tsql += \"\\nWHERE {pk} = %({pk})s\"\n\n"\
   f"\tkwargs[\"{pk}\"] = {pk}\n"\
    "\texec_commit(sql,kwargs)\n\n"\
  
  return update,


def make_deletes(module: str, attrs: list[Dict[str,str]]) -> list[str]:
  pk = list(attrs[0].keys())[0]
  pk_type = list(attrs[0].values())[0][0]

  delete = \
   f"def delete_{module}({pk}: {pk_type}) -> None:\n"\
   f"\tsql = \"DELETE FROM {module} WHERE {pk} = %({pk})s\"\n"\
    "\texec_commit(sql,{"\
   f"\"{pk}\": {pk}"\
    "})\n\n"\

  return delete,

#endregion

#region API Methods

def make_gets_api(module: str, attrs: list[Dict[str,str]]) -> list[str]:
  pk = list(attrs[0].keys())[0]
  pk_type = list(attrs[0].values())[0][0]

  from_pk = \
   f"@{module}_bp.route('/<{pk}>', methods=[\"GET\"])\n"\
   f"def get_{module}_from_pk({pk}: {pk_type}):\n"\
   f"\tresult = db.get_{module}({pk}={pk})\n"\
    "\tif result is not None:\n"\
    "\t\treturn jsonify([row.__dict__ for row in result]), 200\n"\
    "\telse:\n"\
    "\t\treturn jsonify({\"error\": f\""\
   f"{module.capitalize()[:-1]}"\
    " {"\
   f"{pk}"\
    "} "\
    "not found\"}), 404\n\n"
  
  queried = \
   f"@{module}_bp.route('/', methods=[\"GET\"])\n"\
   f"def get_{module}_from_query():\n"\
   f"\tresult = db.get_{module}(request.args)\n"\
    "\tif result is not None:\n"\
    "\t\treturn jsonify([row.__dict__ for row in result]), 200\n"\
    "\telse:\n"\
    "\t\treturn jsonify([]), 204\n\n"
  
  return from_pk, queried 


def make_posts_api(module: str, attrs: list[Dict[str,str]]) -> list[str]:
  post = \
   f"@{module}_bp.route('/', methods=[\"POST\"])\n"\
   f"def post_{module}():\n"\
   f"\tresult = db.create_{module}(request.json)\n"\
    "\treturn jsonify(result.__dict__), 201\n\n"
  
  return post,


def make_puts_api(module: str, attrs: list[Dict[str,str]]) -> list[str]:
  pk = list(attrs[0].keys())[0]
  pk_type = list(attrs[0].values())[0][0]

  put = \
   f"@{module}_bp.route('/<{pk}>', methods=[\"PUT\"])\n"\
   f"def put_{module}({pk}: {pk_type}):\n"\
   f"\tresult = db.update_{module}({pk}, request.args)\n"\
    "\treturn jsonify(result.__dict__), 200\n\n"
  
  return put,


def make_deletes_api(module: str, attrs: list[Dict[str,str]]) -> list[str]:
  pk = list(attrs[0].keys())[0]
  pk_type = list(attrs[0].values())[0][0]

  delete = \
   f"@{module}_bp.route('/<{pk}>', methods=[\"DELETE\"])\n"\
   f"def delete_{module}({pk}: {pk_type}):\n"\
   f"\tresult = db.delete_{module}({pk})\n"\
    "\treturn jsonify(""), 204\n\n"
  
  return delete,

#endregion

#region DB Tests

def test_gets(module: str, attrs: list[Dict[str,str]]) -> list[str]:
  return \
   f"def test_get_{module}():\n"\
   f"\tresult = db.get_{module}()\n"\
    "\tassert 1+1 == 2\n\n",

def test_creates(module: str, attrs: list[Dict[str,str]]) -> list[str]:
  return \
   f"def test_create_{module}():\n"\
   f"\tresult = db.create_{module}()\n"\
    "\tassert 1+1 == 2\n\n",

def test_updates(module: str, attrs: list[Dict[str,str]]) -> list[str]:
  return \
   f"def test_update_{module}():\n"\
   f"\tresult = db.update_{module}()\n"\
    "\tassert 1+1 == 2\n\n",

def test_deletes(module: str, attrs: list[Dict[str,str]]) -> list[str]:
  return \
   f"def test_delete_{module}():\n"\
   f"\tresult = db.delete_{module}()\n"\
    "\tassert 1+1 == 2\n\n",

#endregion

#region API Tests

def test_gets_api(module: str, attrs: list[Dict[str,str]]) -> list[str]:
  return \
   f"def test_get_{module}():\n"\
    "\tresult = get_rest_call(BASE)\n"\
    "\tassert 1+1 == 2\n\n",

def test_posts_api(module: str, attrs: list[Dict[str,str]]) -> list[str]:
  return \
   f"def test_post_{module}():\n"\
    "\tresult = post_rest_call(BASE)\n"\
    "\tassert 1+1 == 2\n\n",

def test_puts_api(module: str, attrs: list[Dict[str,str]]) -> list[str]:
  return \
   f"def test_put_{module}():\n"\
    "\tresult = put_rest_call(BASE)\n"\
    "\tassert 1+1 == 2\n\n",

def test_deletes_api(module: str, attrs: list[Dict[str,str]]) -> list[str]:
  return \
   f"def test_delete_{module}():\n"\
    "\tresult = delete_rest_call(BASE)\n"\
    "\tassert 1+1 == 2\n\n",
            
#endregion

def main():
  dirs = ["api","database"]
  subdirs = ["src","tests"]
  models = "models.json"
  with open(models,"r") as f:
    modules = json.load(f)

  # Double check dirs are there
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
          f.write(headers["api/src"](module))
          for method in [make_gets_api,make_posts_api,make_puts_api,make_deletes_api]:
            for function in method(module, attrs):
              f.write(function)
            f.write("\n")


        elif subdir == "tests":
          f.write(headers["api/tests"](module))
          for method in [test_gets_api,test_posts_api,test_puts_api,test_deletes_api]:
            for function in method(module, attrs):
              f.write(function)

      #endregion

      #region Database

      elif direct == "database":
        f.write(headers["database"](module))
        
        if subdir == "src":
          for method in [make_gets,make_creates,make_updates,make_deletes]:
            for function in method(module, attrs):
              f.write(function)
            f.write("\n")

        elif subdir == "tests":
          f.write(headers["database/tests"](module))
          for method in [test_gets,test_creates,test_updates,test_deletes]:
            for function in method(module, attrs):
              f.write(function)
      #endregion
  
  #region Server

  with open("api/server.py", "w") as f:
    f.write(headers["api/src"](module))

    for module in modules:
      f.write(f"from api.src.{module} import {module}_bp\n")
    f.write("\n")
      
    f.write("app = Flask(__name__)\n\n")

    for module in modules:
      f.write(f"app.register_blueprint({module}_bp)\n")
    f.write("\n")

    f.write(
      "@app.route('/')\n"\
      "def hello_world():\n"\
      "\treturn 'Hello world!'\n\n"\
      "if __name__ == \"__main__\":\n"\
      "\t# python3 -m flask --app api/src/server.py run --debug\n"\
      "\tif len(sys.argv) > 1:\n"\
      "\t\tdebug = sys.argv[1] == \"--debug\"\n"\
      "\telse:\n"\
      "\t\tdebug = False\n"\
      "\tapp.run(debug=debug)\n"
    )

    #endregion

if __name__ == "__main__":
    main()
    initialize_db()
