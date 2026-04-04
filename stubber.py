import json
import os
from typing import Any, Dict

from database.src.db_utils import exec_sql_file, initialize_db
from dbdiagram import translate

#region Headers
# imports, globals, etc.

global_imports = ( # for imports such as UUID or datetime
    "from uuid import UUID\n"\
    "import datetime\n\n"
  )

headers = {
  "api/src": lambda module: ( global_imports + \
    "from flask import Blueprint, jsonify, request\n"\
   f"from database.src import {module} as db\n\n"\
   f"{module}_bp = Blueprint(\"{module}\",__name__,url_prefix=\"/{module}\")\n\n"
  ),

  "api/tests": lambda module: ( global_imports + \
    "from test_utils import *\n\n"\
    f"BASE = \"http://127.0.0.1:5000/{module}/\"\n\n"
  ),

  "database" : lambda module: ( global_imports + \
    "from database.src.db_utils import *\n"\
   f"from database.src.models import {module.capitalize()[:-1]}\n\n"
  ),

  "database/tests" : lambda module: ( global_imports + \
    f"import database.src.{module} as db\n\n"
  ),

  "conftest" : lambda module: ( global_imports + \
    "import pytest\n"\
    f"from database.src import db_utils\n\n"
  ),

  "server" : lambda module: ( global_imports + \
    "from flask import Flask\n"\
    "import sys\n\n"
  )
}

#endregion

#region Parsing

def get_singular(module) -> str:
  return module[:-1]


def get_Object(module) -> str:
  return module.capitalize()[:-1]


def get_pk(attrs) -> str:
  return list(attrs[0].keys())[0]


def get_pk_arguments(attrs) -> Dict[str,str]:
  values = list(attrs[0].values())[0]
  return {
    "python_type" : values[0],
    "sql_type" : values[1],
    "column_parameters" : values[2],
    "sample" : values[3]
  }


def get_attr_name(attr) -> str:
  return list(attr.keys())[0]


def get_attr_arguments(attr) -> Dict[str,str]:
  values = list(attr.values())[0]
  if len(values) < 4: values += [None]
  return {
    "python_type" : values[0],
    "sql_type" : values[1],
    "column_parameters" : values[2],
    "sample" : values[3]
  }


def write_methods(f, module, attrs, method, label, modules) -> None:
  f.write(f"#region {label}\n\n")
  for function in method(module, attrs, modules):
    f.write(function)
  f.write("#endregion\n\n")


def get_dependencies(modules, attrs) -> Dict[str,str]:
  dependencies = {}
  parameters = ""
  first = True
  for attr in attrs:
    for other, other_attrs in modules.items():
      if f"REFERENCES {other}".upper() in get_attr_arguments(attr)["column_parameters"].upper():
        dependencies[get_attr_name(attr)] = [other, get_pk(other_attrs), 
                                             f"one_{get_singular(other)}.{get_pk(other_attrs)}"]
        parameters += f"{", " if not first else ""}one_{get_singular(other)}"

  return parameters, dependencies
#endregion

#region DB Methods

def make_gets(module: str, attrs: list[Dict[str,str]], modules: Dict[str,Any]) -> list[str]:
  singular = get_singular(module)
  Object = get_Object(module)

  all = \
   f"def get_all_{module}() -> list[{Object}]:\n"\
    "\t\"\"\"\n"\
   f"\tReturns all {module} in the database\n\n"\
    "\tReturns:\n"\
   f"\t\tlist[{Object}]: all {module} in the database\n"\
    "\t\"\"\"\n"\
   f"\tsql = \"SELECT * FROM {module};\"\n\n"\
    "\tresult = exec_get_all(sql)\n\n"\
   f"\treturn [{singular.capitalize()}(row) for row in result]\n\n"
  
  queried = \
   f"def get_{module}(kwargs) -> list[{Object}]:\n"\
    "\t\"\"\"\n"\
   f"\tReturns {module} with matching attributes\n\n"\
    "\t## Kwargs:\n"
  
  for attr in attrs:
    key = get_attr_name(attr)
    value = get_attr_arguments(attr)["python_type"]
    queried += f"\t\t:{key} ({value}): the {singular}\'s {key}\n"

  queried += \
    "\n\tReturns:\n"\
   f"\t\tlist[{Object}]: all {module} in the database\n"\
    "\t\"\"\"\n"\
   f"\tif not kwargs: return get_all_{module}()\n"\
   f"\tsql = \"SELECT * FROM {module} WHERE\\n\"\n"\
   f"\tfor i,key in enumerate(kwargs):\n"\
    "\t\tsql += f\"\\t{key} = %({key})s\"\n"\
    "\t\tsql += \",\\n\" if i < len(kwargs)-1 else \"\\n\"\n\n"\
    "\tresult = exec_get_all(sql,kwargs)\n\n"\
   f"\treturn [{Object}(row) for row in result]\n\n"

  return all, queried
  

def make_creates(module: str, attrs: list[Dict[str,str]], modules: Dict[str,Any]) -> list[str]:
  singular = get_singular(module)
  Object = get_Object(module)

  create = \
   f"def create_{module}(kwargs) -> {Object}:\n"\
    "\t\"\"\"\n"\
   f"\tCreates and returns a {singular}\n\n"\
    "\t## Kwargs:\n"
  
  for attr in attrs:
    key = get_attr_name(attr)
    value = get_attr_arguments(attr)

    create += f"\t\t:{key} ({value["python_type"]}"\
     f"{", optional" if ("NOT NULL" not in value["column_parameters"].upper() or 
                         "DEFAULT" in value["column_parameters"].upper()) else ""}): "\
     f"the {singular}\'s {key}\n"

  create += \
    "\n\tReturns:\n"\
   f"\t\t{Object}: the created {singular}\n"\
    "\t\"\"\"\n"\
    "\tif len(kwargs) == 0: return None\n"\
   f"\tsql = \"INSERT INTO {module} (\"\n"\
    "\tvalues = \"VALUES(\"\n"\
    "\tfor i,key in enumerate(kwargs):\n"\
    "\t\tsql += key\n"\
    "\t\tvalues += f\"%({key})s\"\n"\
    "\t\tsql += \", \" if i < len(kwargs)-1 else \") \"\n\n"\
    "\t\tvalues += \", \" if i < len(kwargs)-1 else \")\"\n\n"\
   f"\tsql += values\n"\
   f"\tsql += \"\\nRETURNING *\"\n\n"\
    "\tresult = exec_commit_returning(sql,kwargs)[0]\n\n"\
   f"\treturn {Object}(result)\n\n"
  
  return create,


def make_updates(module: str, attrs: list[Dict[str,str]], modules: Dict[str,Any]) -> list[str]:
  pk = get_pk(attrs)
  pk_type = get_pk_arguments(attrs)["python_type"]
  singular = get_singular(module)
  Object = get_Object(module)
  
  update = \
   f"def update_{module}({pk}: {pk_type}, kwargs) -> {Object}:\n"\
    "\t\"\"\"\n"\
   f"\tUpdates and returns a {singular} from its {pk}\n\n"\
   f"\tArgs:\n"\
   f"\t\t{pk} ({pk_type}): the {singular} to update\n\n"\
    "\t## Kwargs:\n"
  
  for attr in attrs:
    key = get_attr_name(attr)
    value = get_attr_arguments(attr)["python_type"]

    update += f"\t\t:{key} ({value}): the {singular}\'s {key}\n"

  update += \
    "\n\tReturns:\n"\
   f"\t\t{Object}: the updated {singular}\n"\
    "\t\"\"\"\n"\
    "\tkwargs = dict(kwargs)\n"\
    "\tif len(kwargs) == 0: return\n"\
   f"\tsql = \"UPDATE {module} SET \\n\"\n"\
    "\tfor i,key in enumerate(kwargs):\n"\
    "\t\tsql += f\"{key} = %({key})s\"\n"\
    "\t\tsql += \",\\n\" if i < len(kwargs)-1 else \"\\n\"\n\n"\
   f"\tsql += \"\\nWHERE {pk} = %({pk})s\\n\"\n"\
    "\tsql += \"RETURNING *\"\n\n"\
   f"\tkwargs[\"{pk}\"] = {pk}\n"\
    "\tresult = exec_commit_returning(sql,kwargs)[0]\n"\
   f"\treturn {Object}(result)\n\n"\
  
  return update,


def make_deletes(module: str, attrs: list[Dict[str,str]], modules: Dict[str,Any]) -> list[str]:
  pk = get_pk(attrs)
  pk_type = get_pk_arguments(attrs)["python_type"]
  singular = get_singular(module)
  Object = get_Object(module)

  delete = \
   f"def delete_{module}({pk}: {pk_type}) -> {Object}:\n"\
    "\t\"\"\"\n"\
   f"\tDeletes a {singular} from its {pk}\n\n"\
    "\tArgs:\n"\
   f"\t\t{pk} ({pk_type}): the {singular} to delete\n\n"\
    "\tReturns:\n"\
   f"\t\t{Object}: the deleted {singular}\n"\
    "\t\"\"\"\n"\
   f"\tsql = \"DELETE FROM {module} WHERE {pk} = %({pk})s RETURNING * \"\n"\
    "\tresult = exec_commit_returning(sql,{"+f"\"{pk}\": {pk}"+"})[0]\n"\
   f"\treturn {Object}(result)\n\n"

  return delete,

#endregion

#region API Methods

def make_gets_api(module: str, attrs: list[Dict[str,str]], modules: Dict[str,Any]) -> list[str]:
  pk = get_pk(attrs)
  pk_type = get_pk_arguments(attrs)["python_type"]
  singular = get_singular(module)
  Object = get_Object(module)

  from_pk = \
   f"@{module}_bp.route('/<{pk}>', methods=[\"GET\"])\n"\
   f"def get_{module}_from_pk({pk}: {pk_type}):\n"\
    "\t\"\"\"\n"\
   f"\tReturns a specific {singular} from its {pk}\n\n"\
   f"\tArgs:\n"\
   f"\t\t{pk} ({pk_type}): the {singular}'s {pk}\n"\
    "\t\"\"\"\n"\
   f"\tresult = db.get_{module}("+"{"+f"\"{pk}\": {pk}"+"})\n"\
    "\tif result is not None:\n"\
    "\t\treturn jsonify([row.__dict__ for row in result]), 200\n"\
    "\telse:\n"\
    "\t\treturn jsonify({\"error\": f\""+f"{Object}"+" {"+f"{pk}"+"} not found\"}), 404\n\n"
  
  queried = \
   f"@{module}_bp.route('/', methods=[\"GET\"])\n"\
   f"def get_{module}_from_query():\n"\
    "\t\"\"\"\n"\
   f"\tReturns {module} with matching attributes\n\n"\
    "\t## Query parameters:\n"
  
  for attr in attrs:
    key = get_attr_name(attr)
    value = get_attr_arguments(attr)["python_type"]

    queried += f"\t\t:{key} ({value}): the {singular}\'s {key}\n"

  queried += \
    "\n\tReturns:\n"\
   f"\t\tlist[{Object}]: all {module} in the database\n"\
    "\t\"\"\"\n"\
   f"\tresult = db.get_{module}(request.args)\n"\
    "\tif result is not None:\n"\
    "\t\treturn jsonify([row.__dict__ for row in result]), 200\n"\
    "\telse:\n"\
    "\t\treturn jsonify([]), 204\n\n"
  
  return from_pk, queried 


def make_posts_api(module: str, attrs: list[Dict[str,str]], modules: Dict[str,Any]) -> list[str]:
  singular = get_singular(module)

  post = \
   f"@{module}_bp.route('/', methods=[\"POST\"])\n"\
   f"def post_{module}():\n"\
    "\t\"\"\"\n"\
   f"\tCreates and returns a {singular}\n\n"\
    "\t## Body Parameters:\n"
  
  for attr in attrs:
    key = get_attr_name(attr)
    value = get_attr_arguments(attr)

    post += f"\t\t:{key} ({value["python_type"]}"\
     f"{", optional" if ("NOT NULL" not in value["column_parameters"].upper() or 
                         "DEFAULT" in value["column_parameters"].upper()) else ""}): "\
     f"the {singular}\'s {key}\n"

  post += \
    "\n\t\"\"\"\n"\
   f"\tresult = db.create_{module}(request.json)\n"\
    "\treturn jsonify(result.__dict__), 201\n\n"
  
  return post,


def make_puts_api(module: str, attrs: list[Dict[str,str]], modules: Dict[str,Any]) -> list[str]:
  pk = get_pk(attrs)
  pk_type = get_pk_arguments(attrs)["python_type"]
  singular = get_singular(module)

  put = \
   f"@{module}_bp.route('/<{pk}>', methods=[\"PUT\"])\n"\
   f"def put_{module}({pk}: {pk_type}):\n"\
    "\t\"\"\"\n"\
   f"\tUpdates and returns a {singular} from its {pk}\n\n"\
   f"\tArgs:\n"\
   f"\t\t{pk} ({pk_type}): the {singular} to update\n\n"\
    "\t## Query parameters:\n"
  
  for attr in attrs:
    key = get_attr_name(attr)
    value = get_attr_arguments(attr)["python_type"]

    put += f"\t\t:{key} ({value}): the {singular}\'s {key}\n"

  put += \
    "\t\"\"\"\n"\
   f"\tresult = db.update_{module}({pk}, dict(request.args))\n"\
    "\treturn jsonify(result.__dict__), 200\n\n"
  
  return put,


def make_deletes_api(module: str, attrs: list[Dict[str,str]], modules: Dict[str,Any]) -> list[str]:
  pk = get_pk(attrs)
  pk_type = get_pk_arguments(attrs)["python_type"]
  singular = get_singular(module)

  delete = \
   f"@{module}_bp.route('/<{pk}>', methods=[\"DELETE\"])\n"\
   f"def delete_{module}({pk}: {pk_type}):\n"\
    "\t\"\"\"\n"\
   f"\tDeletes a {singular} from its {pk}\n\n"\
    "\tArgs:\n"\
   f"\t\t{pk} ({pk_type}): the {singular} to delete\n"\
    "\t\"\"\"\n"\
   f"\tresult = db.delete_{module}({pk})\n"\
    "\treturn jsonify(result.__dict__), 200\n\n"
  
  return delete,

#endregion

#region DB Tests

def test_gets(module: str, attrs: list[Dict[str,str]], modules: Dict[str,Any]) -> list[str]:
  singular = get_singular(module)
  Object = get_Object(module)
  pk = get_pk(attrs)

  return \
   f"def test_get_one_{singular}(one_{singular}):\n"\
   f"\tresult = db.get_{module}("\
    "{"\
   f"\"{pk}\": one_{singular}.{pk}"\
    "})[0]\n"\
   f"\tassert result == one_{singular}\n\n",

def test_creates(module: str, attrs: list[Dict[str,str]], modules: Dict[str,Any]) -> list[str]:
  singular = get_singular(module)
  Object = get_Object(module)
  parameters, dependencies = get_dependencies(modules, attrs)

  result = \
   f"def test_create_{module}({parameters}):\n"\
   f"\tnew_{singular} = "\
    "{\n"
  for attr in attrs:
    key = get_attr_name(attr) 
    value = get_attr_arguments(attr)["sample"]
    if value is None: continue
    result += (f"\t\t\"{key}\": {repr(value)},\n")
  result += \
    "\t}\n\n"\
   f"\tresult = db.create_{module}(new_{singular})\n\n"\
   f"\texpected = {Object}(exec_get_one(\"SELECT * FROM {module}\"))\n\n"\
   f"\tassert expected == result\n\n"
  
  return result,

def test_updates(module: str, attrs: list[Dict[str,str]], modules: Dict[str,Any]) -> list[str]:
  singular = get_singular(module)
  Object = get_Object(module)
  pk = get_pk(attrs)

  return \
   f"def test_update_{module}(one_{singular}):\n"\
    "\t# Can\'t actually test update without prompting a second sample value (eh, it\'s good enough)\n"\
   f"\texpected = {Object}(exec_get_one(\"SELECT * FROM {module}\"))\n\n"\
   f"\tdb.update_{module}(one_{singular}.{pk}, one_{singular}.__dict__)\n"\
   f"\tresult = {Object}(exec_get_one(\"SELECT * FROM {module}\"))\n\n"\
    "\tassert expected == result\n\n",

def test_deletes(module: str, attrs: list[Dict[str,str]], modules: Dict[str,Any]) -> list[str]:
  singular = get_singular(module)
  Object = get_Object(module)
  pk = get_pk(attrs)

  return \
   f"def test_delete_{module}(one_{singular}):\n"\
   f"\tdb.delete_{module}(one_{singular}.{pk})\n"\
   f"\tresult, = exec_get_one(\"SELECT COUNT(*) FROM {module}\")\n"\
    "\tassert result == 0\n\n",

#endregion

#region API Tests

def test_gets_api(module: str, attrs: list[Dict[str,str]], modules: Dict[str,Any]) -> list[str]:
  singular = get_singular(module)
  Object = get_Object(module)
  pk = get_pk(attrs)

  return \
   f"def test_get_{module}(one_{singular}):\n"\
    "\tresult = get_rest_call(BASE)[0]\n"\
   f"\tassert result.get(\"{pk}\")\n\n",

def test_posts_api(module: str, attrs: list[Dict[str,str]], modules: Dict[str,Any]) -> list[str]:
  singular = get_singular(module)
  Object = get_Object(module)
  pk = get_pk(attrs)
  parameters, dependencies = get_dependencies(modules, attrs)

  result = \
   f"def test_post_{module}({parameters}):\n"\
   f"\tnew_{singular} = "\
    "{\n"
  for attr in attrs:
    key = get_attr_name(attr) 
    value = get_attr_arguments(attr)["sample"]
    if value is None: continue
    result += (f"\t\t\"{key}\": {repr(value)},\n")
  result += (
    "\t}\n\n"\
   f"\tresult = post_rest_call(BASE,json=new_{singular},expected_code=201)\n"\
   f"\tassert result.get(\"{pk}\")\n\n"
  )
  
  return result,

def test_puts_api(module: str, attrs: list[Dict[str,str]], modules: Dict[str,Any]) -> list[str]:
  singular = get_singular(module)
  Object = get_Object(module)
  pk = get_pk(attrs)

  return \
   f"def test_put_{module}(one_{singular}):\n"\
   f"\tresult = put_rest_call(BASE+str(one_{singular}.{pk}), params=one_{singular}.__dict__)\n"\
    "\texpected = {}\n"\
   f"\tassert result.get(\"{pk}\")\n\n",

def test_deletes_api(module: str, attrs: list[Dict[str,str]], modules: Dict[str,Any]) -> list[str]:
  singular = get_singular(module)
  Object = get_Object(module)
  pk = get_pk(attrs)

  return \
   f"def test_delete_{module}(one_{singular}):\n"\
   f"\tresult = delete_rest_call(BASE+str(one_{singular}.{pk}))\n"\
    "\tassert len(get_rest_call(BASE)) == 0\n\n"\
   f"\tassert result.get(\"{pk}\")\n\n",
            
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
    for i,attr in enumerate(attrs):
      print(f"    {get_attr_name(attr)}: {get_attr_arguments(attr)["sql_type"]}"\
                  f"{"," if i < len(attrs)-1 else ""}")

  #region Models

  with open("database/src/models.py","w") as f:
    f.write(global_imports)

    for module, attrs in modules.items():
      singular = get_singular(module)
      Object = get_Object(module)

      f.write(f"class {Object}:\n")
      for attr in attrs:
        f.write(f"\t{get_attr_name(attr)}: {get_attr_arguments(attr)["python_type"]}\n")
      f.write("\n\tdef __init__(self, args):\n")
      for i,attr in enumerate(attrs):
        f.write(f"\t\tself.{get_attr_name(attr)} = args[{i}]\n")
      f.write("\n\tdef __eq__(self,other):\n"\
             f"\t\tif type(other) != {Object}: return False\n"
              "\t\treturn (\n")
      for i,attr in enumerate(attrs):
        f.write(f"\t\t\tself.{get_attr_name(attr)} == other.{get_attr_name(attr)}{" and" if i < len(attrs)-1 else ""}\n")
      f.write("\t\t)\n\n")

  #endregion

  #region SQL

  for module, attrs in modules.items():
    with open(f"database/schema/{module}.sql", "w") as f:
      f.write(f"CREATE TABLE IF NOT EXISTS {module} (\n")
      for i,attr in enumerate(attrs):
        f.write(f"\t{get_attr_name(attr)} {get_attr_arguments(attr)["sql_type"]} {get_attr_arguments(attr)["column_parameters"]} {"PRIMARY KEY" if i == 0 else ""}{"," if i < len(attrs)-1 else ""}\n")
      f.write(");\n")
    exec_sql_file(f"schema/{module}.sql")

  with open("database/schema/schema.txt","w") as f:
    f.write(translate())

  #endregion

  gen = ((direct, subdir, module) for direct in dirs for subdir in subdirs for module in modules)
  for (direct, subdir, module) in gen:
    attrs = modules[module]
    with open(f"{direct}/{subdir}/{"test_" if subdir == "tests" else ""}{module}{"_api" if subdir == "tests" and direct == "api" else ""}.py", "w") as f:

      #region Database

      if direct == "database":
        f.write(headers["database"](module))
        
        if subdir == "src":
          for method,label in zip([make_gets,make_creates,make_updates,make_deletes],
                                  ["Get Methods","Create Methods","Update Methods","Delete Methods"]):
            write_methods(f,module,attrs,method,label,modules)

        elif subdir == "tests":
          f.write(headers["database/tests"](module))
          for method,label in zip([test_gets,test_creates,test_updates,test_deletes],
                                  ["Get Methods","Create Methods","Update Methods","Delete Methods"]):
            write_methods(f,module,attrs,method,label,modules)
              
      #endregion

      #region API

      elif direct == "api":

        if subdir == "src":
          f.write(headers["api/src"](module))
          for method,label in zip([make_gets_api,make_posts_api,make_puts_api,make_deletes_api],
                                  ["Get Methods","Post Methods","Put Methods","Delete Methods"]):
            write_methods(f,module,attrs,method,label,modules)


        elif subdir == "tests":
          f.write(headers["api/tests"](module))
          for method,label in zip([test_gets_api,test_posts_api,test_puts_api,test_deletes_api],
                                  ["Get Methods","Post Methods","Put Methods","Delete Methods"]):
            write_methods(f,module,attrs,method,label,modules)

      #endregion

  #region Conftests

  with open(f"database/tests/conftest.py","w") as f:
    f.write(headers["conftest"](module))
    # Reset database function
    f.write(
      "@pytest.fixture(scope=\"function\", autouse=True)\n"\
      "def reset_database():\n"\
      "\tsql = \"DROP TABLE IF EXISTS "
    )
    for i,module in enumerate(modules):
      f.write(
        f"{module}{", " if i < len(modules)-1 else " CASCADE;\"\n"}"
      )
    f.write("\tdb_utils.exec_commit(sql)\n")
    for i,module in enumerate(modules):
      f.write(
        f"\tdb_utils.exec_sql_file(\"schema/{module}.sql\")\n"
      )
    
    f.write("\n\n")

    for i, (module, attrs) in enumerate(modules.items()):
      singular = get_singular(module)

      parameters, dependencies = get_dependencies(modules, attrs)

      f.write(
        f"from database.src.{module} import create_{module}\n\n"\
          "@pytest.fixture(scope=\"function\")\n"\
        f"def one_{singular}({parameters}):\n"\
        f"\tnew_{module} = "+"{\n"
      )
      for attr in attrs:
        key = get_attr_name(attr)
        if dependencies.get(key) is None:
          value = repr(get_attr_arguments(attr)["sample"])
          if value is None: continue
        else:
          value = dependencies[key][2]
        f.write(f"\t\t\"{key}\": {value},\n")
      f.write(
        "\t}\n\n"\
        f"\treturn create_{module}(new_{module})\n\n"
      )

  with open("api/tests/conftest.py","w") as f:
    f.write("from database.tests.conftest import *\n\n")

  #endregion
  
  #region Server

  with open("api/server.py", "w") as f:
    f.write(headers["server"](module))

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
      "\t# python3 -m flask --app api/server.py run --debug\n"\
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
