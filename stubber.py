import argparse
import json
import os
import re
from typing import Any, Dict
from psycopg2.errors import UndefinedTable

from database.src.db_utils import exec_sql_file, initialize_db
from translator import translate_diagram

# Flask api default
api_host = "http://127.0.0.1:5000"

#region Headers
# imports, globals, etc.

global_imports = ( # for imports such as UUID or datetime
    "from uuid import UUID\n"\
    "import datetime\n"\
    "from typing import Any\n\n"
  )

headers = {
  "api/src": lambda module, stubber: ( global_imports + \
    "from flask import Blueprint, jsonify, request\n"\
   f"from database.src import {module} as db\n\n"\
   f"{module}_bp = Blueprint(\"{module}\",__name__,url_prefix=\"/{module}\")\n\n"
  ),

  "api/tests": lambda module, stubber: ( global_imports + \
    "from test_utils import *\n\n"\
    f"BASE = \"http://127.0.0.1:5000/{module}/\"\n\n"
  ),

  "database" : lambda module, stubber: ( global_imports + \
    "from database.src.db_utils import *\n"\
   f"from database.src.models import {stubber.get_Object(module)}\n\n"
  ),

  "database/tests" : lambda module, stubber: ( global_imports + \
    f"import database.src.{module} as db\n\n"
  ),

  "conftest" : lambda module, stubber: ( global_imports + \
    "import pytest\n"\
    f"from database.src import db_utils\n\n"
  ),

  "server" : lambda module, stubber: ( global_imports + \
    "from flask import Flask\n"\
    "from flask_cors import CORS\n"\
    "import sys\n\n"
  )
}

#endregion

#region Custom input

# File body generator
# def my_custom_file(modules):
#   yield "Hello world!\n"

# File path: write mode (e.g. "w" or "a+"), file body (iterable callable)
custom = {
  # "out/myfile.txt" : {
      # "mode": "a+",
      # "body": my_custom_file
  # }
}

#endregion

class Stubber:

  modules: Dict[str, Any]
  model_path: str

  def __init__(self,  model_path):
    self.model_path = model_path
    with open(model_path,"r") as f:
      self.modules = json.load(f)

  #region Parsing

  # {
  #   "module": {
  #     "singular": "module",
  #     "object_name": "Module",
  #     "pk": "module_id",
  #     "attributes": {
  #       "module_id": {
  #         "python_type": "UUID",
  #         "sql_type": "UUID",
  #         "column_arguments": "DEFAULT gen_random_uuid()"
  #       },
  #       "module_attr1": {
  #         "python_type": "str",
  #         "sql_type": "TEXT",
  #         "column_arguments": "NOT NULL",
  #         "sample": "abc"
  #       },
  #       ...
  #     }
  #   },
  #   ...
  # }

  def get_singular(self, module: str) -> str:
    return self.modules[module].get("singular", module[:-1])


  def get_Object(self, module: str) -> str:
    return self.modules[module].get(
      "object_name", 
      re.sub(r"([a-zA-Z])_([a-z])",
             lambda x: x.group(1) + x.group(2).capitalize(),
             re.sub(r"^([a-z])",lambda x: x.group().capitalize(), module)
      )
    )


  def get_pk(self, module: str) -> str:
    result = self.modules[module].get("pk") or self.modules[module].get("primary key")
    if not result:
      raise Exception(f"Primary key [\"pk\" or \"primary key\"] not defined for module {module}")
    return result 


  def get_pk_arguments(self, module: str) -> Dict[str,str]:
    pk = self.get_pk(module)
    return self.modules[module]["attributes"][pk]


  def write_methods(self, module: str, method: callable, label: str) -> None:
    result = (f"#region {label}\n\n")
    for function in method(module):
      result += (function)
    result += ("#endregion\n\n")
    return result


  def get_dependencies(self, module: str) -> Dict[str,str]:
    dependencies = {}
    parameters = ""
    first = True
    for attr, obj in self.modules[module]["attributes"].items():
      for other in self.modules:
        if f"REFERENCES {other}".upper() in obj["column_arguments"].upper():
          dependencies[attr] = [other, self.get_pk(other), 
                                f"one_{self.get_singular(other)}.{self.get_pk(other)}"]
          parameters += f"{", " if not first else ""}one_{self.get_singular(other)}"
          first = False

    return parameters, dependencies


  def build_sample(self, module: str) -> str:
    _, dependencies = self.get_dependencies(module)
    result = ""
    for attr, obj in self.modules[module]["attributes"].items():
      if dependencies.get(attr) is None:
        sample = obj.get("sample")
        if sample is None: continue
        sample = repr(sample)
      else:
        sample = dependencies[attr][2]
      result += (f"\t\t\"{attr}\": {sample},\n")

    return result

  #endregion

  #region DB Methods

  def make_gets(self, module: str) -> list[str]:
    singular = self.get_singular(module)
    Object = self.get_Object(module)

    all = \
    f"def get_all_{module}() -> list[{Object}]:\n"\
      "\t\"\"\"\n"\
    f"\tReturns all {module} in the database\n\n"\
      "\tReturns:\n"\
    f"\t\tlist[{Object}]: all {module} in the database\n"\
      "\t\"\"\"\n"\
    f"\tsql = \"SELECT * FROM {module};\"\n\n"\
      "\tresult = exec_get_all(sql)\n\n"\
    f"\treturn [{Object}(row) for row in result]\n\n"
    
    queried = \
    f"def get_{module}(kwargs) -> list[{Object}]:\n"\
      "\t\"\"\"\n"\
    f"\tReturns {module} with matching attributes\n\n"\
      "\t## Kwargs:\n"
    
    for attr, obj in self.modules[module]["attributes"].items():
      type = obj["python_type"]

      queried += f"\t\t:{attr} ({type}): the {singular}\'s {attr}\n"

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
    

  def make_creates(self, module: str) -> list[str]:
    singular = self.get_singular(module)
    Object = self.get_Object(module)

    create = \
    f"def create_{module}(kwargs) -> {Object}:\n"\
      "\t\"\"\"\n"\
    f"\tCreates and returns a {singular}\n\n"\
      "\t## Kwargs:\n"
    
    for attr, obj in self.modules[module]["attributes"].items():
      create += f"\t\t:{attr} ({obj["python_type"]}"\
      f"{", optional" if ("NOT NULL" not in obj["column_arguments"].upper() or 
                          "DEFAULT" in obj["column_arguments"].upper()) else ""}): "\
      f"the {singular}\'s {attr}\n"

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


  def make_updates(self, module: str) -> list[str]:
    pk = self.get_pk(module)
    pk_type = self.get_pk_arguments(module)["python_type"]
    singular = self.get_singular(module)
    Object = self.get_Object(module)
    
    update = \
    f"def update_{module}({pk}: {pk_type}, kwargs) -> {Object}:\n"\
      "\t\"\"\"\n"\
    f"\tUpdates and returns a {singular} from its {pk}\n\n"\
    f"\tArgs:\n"\
    f"\t\t{pk} ({pk_type}): the {singular} to update\n\n"\
      "\t## Kwargs:\n"
    
    for attr, obj in self.modules[module]["attributes"].items():
      value = obj["python_type"]

      update += f"\t\t:{attr} ({value}): the {singular}\'s {attr}\n"

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


  def make_deletes(self, module: str) -> list[str]:
    pk = self.get_pk(module)
    pk_type = self.get_pk_arguments(module)["python_type"]
    singular = self.get_singular(module)
    Object = self.get_Object(module)

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

  def make_gets_api(self, module: str) -> list[str]:
    pk = self.get_pk(module)
    pk_type = self.get_pk_arguments(module)["python_type"]
    singular = self.get_singular(module)
    Object = self.get_Object(module)

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
    
    for attr, obj in self.modules[module]["attributes"].items():
      type = obj["python_type"]

      queried += f"\t\t:{attr} ({type}): the {singular}\'s {attr}\n"

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


  def make_posts_api(self, module: str) -> list[str]:
    singular = self.get_singular(module)

    post = \
    f"@{module}_bp.route('/', methods=[\"POST\"])\n"\
    f"def post_{module}():\n"\
      "\t\"\"\"\n"\
    f"\tCreates and returns a {singular}\n\n"\
      "\t## Body Parameters:\n"
    
    for attr, obj in self.modules[module]["attributes"].items():
      post += f"\t\t:{attr} ({obj["python_type"]}"\
      f"{", optional" if ("NOT NULL" not in obj["column_arguments"].upper() or 
                          "DEFAULT" in obj["column_arguments"].upper()) else ""}): "\
      f"the {singular}\'s {attr}\n"

    post += \
      "\n\t\"\"\"\n"\
    f"\tresult = db.create_{module}(request.json)\n"\
      "\treturn jsonify(result.__dict__), 201\n\n"
    
    return post,


  def make_puts_api(self, module: str) -> list[str]:
    pk = self.get_pk(module)
    pk_type = self.get_pk_arguments(module)["python_type"]
    singular = self.get_singular(module)

    put = \
    f"@{module}_bp.route('/<{pk}>', methods=[\"PUT\"])\n"\
    f"def put_{module}({pk}: {pk_type}):\n"\
      "\t\"\"\"\n"\
    f"\tUpdates and returns a {singular} from its {pk}\n\n"\
    f"\tArgs:\n"\
    f"\t\t{pk} ({pk_type}): the {singular} to update\n\n"\
      "\t## Query parameters:\n"
    
    for attr, obj in self.modules[module]["attributes"].items():
      type = obj["python_type"]

      put += f"\t\t:{attr} ({type}): the {singular}\'s {attr}\n"

    put += \
      "\t\"\"\"\n"\
    f"\tresult = db.update_{module}({pk}, dict(request.args))\n"\
      "\treturn jsonify(result.__dict__), 200\n\n"
    
    return put,


  def make_deletes_api(self, module: str) -> list[str]:
    pk = self.get_pk(module)
    pk_type = self.get_pk_arguments(module)["python_type"]
    singular = self.get_singular(module)

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

  def test_gets(self, module: str) -> list[str]:
    singular = self.get_singular(module)
    pk = self.get_pk(module)

    one = \
      f"def test_get_one_{singular}(one_{singular}):\n"\
      f"\tresult = db.get_{module}("+"{"+f"\"{pk}\": one_{singular}.{pk}"+"})[0]\n"\
      f"\tassert result == one_{singular}\n\n"

    all = \
      f"def test_get_all_{module}(one_{singular}):\n"\
      f"\tresult = db.get_all_{module}()[0]\n"\
      f"\tassert result == one_{singular}\n\n"
    
    return one, all


  def test_creates(self, module: str) -> list[str]:
    singular = self.get_singular(module)
    Object = self.get_Object(module)
    parameters, _ = self.get_dependencies(module)

    result = \
    f"def test_create_{module}({parameters}):\n"\
    f"\tnew_{singular} = "\
      "{\n"
    
    result += self.build_sample(module)

    result += \
      "\t}\n\n"\
    f"\tresult = db.create_{module}(new_{singular})\n\n"\
    f"\texpected = {Object}(exec_get_one(\"SELECT * FROM {module}\"))\n\n"\
    f"\tassert expected == result\n\n"
    
    return result,


  def test_updates(self, module: str) -> list[str]:
    singular = self.get_singular(module)
    Object = self.get_Object(module)
    pk = self.get_pk(module)

    return \
    f"def test_update_{module}(one_{singular}):\n"\
      "\t# Can\'t actually test update without prompting a second sample value\n"\
      "\t# May be a future feature but for now just edit these tests manually\n"\
      "\t# (It still tests that it can be called, so that\'s something)\n"\
    f"\texpected = {Object}(exec_get_one(\"SELECT * FROM {module}\"))\n\n"\
    f"\tdb.update_{module}(one_{singular}.{pk}, one_{singular}.__dict__)\n"\
    f"\tresult = {Object}(exec_get_one(\"SELECT * FROM {module}\"))\n\n"\
      "\tassert expected == result\n\n",


  def test_deletes(self, module: str) -> list[str]:
    singular = self.get_singular(module)
    pk = self.get_pk(module)

    return \
    f"def test_delete_{module}(one_{singular}):\n"\
    f"\tdb.delete_{module}(one_{singular}.{pk})\n"\
    f"\tresult, = exec_get_one(\"SELECT COUNT(*) FROM {module}\")\n"\
      "\tassert result == 0\n\n",

  #endregion

  #region API Tests

  def test_gets_api(self, module: str) -> list[str]:
    singular = self.get_singular(module)
    pk = self.get_pk(module)

    return \
    f"def test_get_{module}(one_{singular}):\n"\
      "\tresult = get_rest_call(BASE)[0]\n"\
    f"\tassert result.get(\"{pk}\")\n\n",


  def test_posts_api(self, module: str) -> list[str]:
    singular = self.get_singular(module)
    pk = self.get_pk(module)
    parameters, _ = self.get_dependencies(module)

    result = \
    f"def test_post_{module}({parameters}):\n"\
    f"\tnew_{singular} = "\
      "{\n"
    
    result += self.build_sample(module)

    result += (
      "\t}\n\n"\
    f"\tresult = post_rest_call(BASE,json=new_{singular},expected_code=201)\n"\
    f"\tassert result.get(\"{pk}\")\n\n"
    )
    
    return result,


  def test_puts_api(self, module: str) -> list[str]:
    singular = self.get_singular(module)
    pk = self.get_pk(module)

    return \
    f"def test_put_{module}(one_{singular}):\n"\
    f"\tresult = put_rest_call(BASE+str(one_{singular}.{pk}), params=one_{singular}.__dict__)\n"\
      "\texpected = {}\n"\
    f"\tassert result.get(\"{pk}\")\n\n",

  def test_deletes_api(self, module: str) -> list[str]:
    singular = self.get_singular(module)
    pk = self.get_pk(module)

    return \
    f"def test_delete_{module}(one_{singular}):\n"\
    f"\tresult = delete_rest_call(BASE+str(one_{singular}.{pk}))\n"\
      "\tassert len(get_rest_call(BASE)) == 0\n\n"\
    f"\tassert result.get(\"{pk}\")\n\n",
     
  #endregion

  def main(self):
    dirs = ["api","database"]
    subdirs = ["src","tests"]

    # Double check dirs are there
    os.makedirs("database/schema", exist_ok=True)
    os.makedirs("database/src", exist_ok=True)
    os.makedirs("database/tests", exist_ok=True)
    os.makedirs("api/src", exist_ok=True)
    os.makedirs("api/tests", exist_ok=True)

    print(f"Generating backend from {self.model_path}")
    print("Models:")
    for module in self.modules:
      print(f"  {module}:")
      attrs = self.modules[module]["attributes"]

      for i, (attr,obj) in enumerate(attrs.items()):
        print(f"    {attr}: {obj["sql_type"]}"\
                    f"{"," if i < len(attrs)-1 else ""}")

    #region Models

    with open("database/src/models.py","w") as f:
      f.write(global_imports)

      for module in self.modules:
        singular = self.get_singular(module)
        Object = self.get_Object(module)
        attrs = self.modules[module]["attributes"]

        f.write(f"class {Object}:\n")
        for attr, obj in attrs.items():
          f.write(f"\t{attr}: {obj["python_type"]}\n")

        f.write("\n\tdef __init__(self,  args):\n")
        for i,attr in enumerate(attrs):
          f.write(f"\t\tself.{attr} = args[{i}]\n")

        f.write("\n\tdef __eq__(self, other):\n"\
              f"\t\tif type(other) != {Object}: return False\n"
                "\t\treturn (\n")
        for i,attr in enumerate(attrs):
          f.write(f"\t\t\tself.{attr} == other.{attr}{" and" if i < len(attrs)-1 else ""}\n")

        f.write("\t\t)\n\n")

    #endregion

    #region SQL

    for module in self.modules:
      attrs = self.modules[module]["attributes"]

      with open(f"database/schema/{module}.sql", "w") as f:
        f.write(f"CREATE TABLE IF NOT EXISTS {module} (\n")

        for i, (attr,obj) in enumerate(attrs.items()):
          f.write(
            f"\t{attr} {obj["sql_type"]} {obj["column_arguments"]} "\
            f"{"PRIMARY KEY" if i == 0 else ""}{"," if i < len(attrs)-1 else ""}\n"
          )
        f.write(");\n")

      try:
        exec_sql_file(f"schema/{module}.sql")
      except UndefinedTable as e:
        class DependencyException(Exception):
          pass
        
        predecessor, = re.findall(r"\"(?P<table>.+)\"", str(e))

        raise DependencyException(f"Foreign key error - table \"{predecessor}\" must come before table \"{module}\" in {self.model_path}")

    with open("database/schema/schema.txt","w") as f:
      f.write(translate_diagram(
        [os.path.join(os.path.dirname(__file__), f"database/schema/{file}") \
         for file in os.listdir("database/schema/")]))

    #endregion

    gen = ((direct, subdir, module) for direct in dirs for subdir in subdirs for module in self.modules)
    for i, (direct, subdir, module) in enumerate(gen):
      with open(f"{direct}/{subdir}/{"test_" if subdir == "tests" else ""}"\
                f"{module}{"_api" if subdir == "tests" and direct == "api" else ""}.py","w") as f:

        # Write headers
        f.write(headers.get(direct,lambda x,y:"")(module,self))
        f.write(headers.get(f"{direct}/{subdir}",lambda x,y:"")(module,self))
        
        # Write methods and test methods
        methods = {
          "database": {
            "src": zip([self.make_gets,self.make_creates,
                        self.make_updates,self.make_deletes],
                        ["Get Methods","Create Methods",
                        "Update Methods","Delete Methods"]),

            "tests": zip([self.test_gets,self.test_creates,
                          self.test_updates,self.test_deletes],
                        ["Get Methods","Create Methods",
                          "Update Methods","Delete Methods"])
          },
          "api": {
            "src": zip([self.make_gets_api,self.make_posts_api,
                        self.make_puts_api,self.make_deletes_api],
                      ["Get Methods","Create Methods",
                        "Update Methods","Delete Methods"]),

            "tests": zip([self.test_gets_api,self.test_posts_api,
                          self.test_puts_api,self.test_deletes_api],
                        ["Get Methods","Post Methods",
                          "Put Methods","Delete Methods"])
          }
        }
        
        for method,label in methods[direct][subdir]:
          f.write(self.write_methods(module,method,label))

    #region Frontend

    with open("frontend/src/App.js", "w") as f:
      f.write(
        "import { Navbar } from 'reactstrap';\n"\
        "import {\n"\
        "\tBrowserRouter as Router,\n"\
        "\tRoutes,\n"\
        "\tRoute,\n"\
        "\tNavigate\n"\
        "} from \"react-router-dom\";\n\n"\
        "import { "
      )
      
      for module in self.modules:
        f.write(self.get_Object(module) + ", ")
      
      f.write(
        "} from \'./components/Modules\';\n\n"\
        "function App() {\n"\
        "\treturn <>\n"\
        "\t\t<Router>\n"\
        "\t\t\t<Navbar />\n"\
        "\t\t\t<Routes>\n"\
        "\t\t\t\t<Route exact path=\"/\" element={<h1>It works!</h1>}/ >\n" #element={<Navigate to="/customers" />}
      )
      
      for module in self.modules:
        f.write(f"\t\t\t\t<Route path=\"/{module}\" element="+"{"+f"<{self.get_Object(module)} />"+"} />\n")

      f.write(
        "\t\t\t</Routes>\n"\
        "\t\t</Router>\n"
        "\t</>\n"
        "}\n"
        "\n"
        "export default App;\n"
      )

    
    with open("frontend/src/components/Modules.jsx","w") as f:
      f.write("import { MyTable } from './MyTable';\n\n")

      for module, obj in self.modules.items():
        f.write(
          f"export function {self.get_Object(module)}() "+"{\n"\
          "\treturn <MyTable \n"\
          "\t\ttable_name={"+f"[\"{self.get_Object(module)}\",\"{module.capitalize()}\"]"+"}\n"\
          "\t\turl={"+f"\"{api_host}/{module}/\""+"}\n"\
          "\t\tcolumns={"+f"{[attr for attr in obj["attributes"]]}"+"}\n"\
          "\t\tcolumn_names={"+f"{[
            re.sub(
              r"([a-zA-Z])_([a-z])",lambda x: x.group(1) + " " + x.group(2).capitalize(),
              re.sub(r"^([a-z])",lambda x: x.group().capitalize(), attr))
                for attr in obj["attributes"]]}"+"}\n"\
          "\t\tpk={"+f"\"{self.get_pk(module)}\""+"}\n"\
          "\t\t/>\n"\
          "}\n\n"
        )
    
    #endregion

    #region Conftests

    with open(f"database/tests/conftest.py","w") as f:
      f.write(headers["conftest"](module,self))
      # Reset database function
      f.write(
        "@pytest.fixture(scope=\"function\", autouse=True)\n"\
        "def reset_database():\n"\
        "\tsql = \"DROP TABLE IF EXISTS "
      )
      for i,module in enumerate(self.modules):
        f.write(
          f"{module}{", " if i < len(self.modules)-1 else " CASCADE;\"\n"}"
        )
      f.write("\tdb_utils.exec_commit(sql)\n")
      for i,module in enumerate(self.modules):
        f.write(
          f"\tdb_utils.exec_sql_file(\"schema/{module}.sql\")\n"
        )
      
      f.write("\n\n")

      for i, module in enumerate(self.modules):
        singular = self.get_singular(module)
        parameters, dependencies = self.get_dependencies(module)

        f.write(
          f"from database.src.{module} import create_{module}\n\n"\
            "@pytest.fixture(scope=\"function\")\n"\
          f"def one_{singular}({parameters}):\n"\
          f"\tnew_{singular} = "+"{\n"
        )
        
        f.write(self.build_sample(module))

        f.write(
          "\t}\n\n"\
          f"\treturn create_{module}(new_{singular})\n\n"
        )

    with open("api/tests/conftest.py","w") as f:
      f.write("from database.tests.conftest import *\n\n")

    #endregion
    
    #region Server

    with open("api/server.py", "w") as f:
      f.write(headers["server"](module,self))

      for module in self.modules:
        f.write(f"from api.src.{module} import {module}_bp\n")
      f.write("\n")
        
      f.write(
        "app = Flask(__name__)\n"\
        "CORS(app, supports_credentials=True)\n\n"
      )

      for module in self.modules:
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

      #region Custom files

      for file, obj in custom.items():
        os.makedirs(file[:file.rfind('/')],exist_ok=True)
        with open(file, obj["mode"]) as f:
          for body in obj["body"](self.modules):
            f.write(body)

      #endregion

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("--file","-f",default="models.json",help="Input models file")
  args = parser.parse_args()

  stubber = Stubber(args.file)
  stubber.main()  
