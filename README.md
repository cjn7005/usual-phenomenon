# usual-phenomenon

This is a tool for getting started creating a backend for a web application. It generates basic CRUD SQL queries and APIs based on your proposed backend schema. 

## Setup

This tool requires Python 3 and Postgres. To install the necessary Python packages run:

```zsh
pip install -r requirements.txt
```

Next you must set up your database. First, create a file in `database/config` named `db.yml` (you can copy from `git_db.yml`). Then create a database and user (login enabled) using pgAdmin, and enter the names and passwords into your `db.yml`.

Later when you are defining your attributes' python_types, if you are using imported types such as `UUID` or `datetime`, you must define these in `stubber.py`. Simply edit the `global_imports` variable at the top of the file (this will ensure your types are imported in every relevent file).

## Usage

To generate the code, first you must define your backend schema. To do this, you will enter in your desired models into `models.json`. Each "model" (or "module," I flip back and forth between the terms) will be a table in your Postgres database, and each attribute a column. 

### Model Definitions

1. `module_name`: The name of the module as it will appear in the database (the table name). Presumed to be plural.

2. `pk` or `primary key`: The name of the primary key attribute. The referenced attribute **must** be defined in `attributes`.

3. `singular`, optional: The singular of `module_name`. If omitted, the parser will assume a trailing "s" in `module_name` (i.e. "modules" -> "module" and "categories" -> "categorie").

4. `object_name`, optional: The name of the model as it will appear in Python. The stubber will create Python classes for each model, and this is the name of that class. If omitted, will take on the capitalized version of the singular.

### Attribute Definitions

1. `python_type`: The attribute type as it will appear in Python type hints (e.g. str, int, datetime, etc.). Imported types should be definied in `stubber.py` (see [Setup](#setup)).

2. `sql_type`: The attribute type as it will appear in PostgreSQL (e.g. INT, UUID, TIMESTAMP, etc.). 

3. `column_parameters`: Any additional parameters to define in the sql table (e.g. `DEFAULT: 'John Doe'`). **Note:** Do not define `PRIMARY KEY` here, that is automatically generated from the given attribute. If you define foreign keys (i.e. `REFERENCES`), then be sure that the table it references comes earlier in `models.json`.

4. `sample_value`, optional: An example value, used for testing. This is optional **unless** the attribute is required (i.e. `NOT NULL`).

```json
{
    "module_name": {
        "singular": "module",
        "object_name": "Module",
        "pk": "module_id",
        "attributes": {
            "module_id": {
                "python_type": "UUID",
                "sql_type": "UUID",
                "column_arguments": "DEFAULT gen_random_uuid()"
            },
            "module_attr1": {
                "python_type": "str",
                "sql_type": "TEXT",
                "column_arguments": "NOT NULL",
                "sample": "abc"
            },
            "module_attr2": {
                "python_type": "int",
                "sql_type": "INTEGER",
                "column_arguments": "DEFAULT 123"
            },
            "module_attr3" : "..."
        }
    },
    "module2": "..."
}
```

Once your models are defined, simply run the stubber:

```zsh
python stubber.py
```

This will generate `src` and `test` files in `database` and `api`, i.e.:

```ascii
root/
├── api/
│   ├── src/
│   │   └── [src_files]
│   └── src/
│       └── [test_api_files]
└── database/
    ├── src/
    │   └── [src_files]
    └── src/
        └── [test_db_files]
```

This will also intialize the database tables for you. All that's left for you to do is run the server. To do so simply run flask on `api/server.py`:

```zsh
python -m flask --app api/server.py run [--debug]
```

The stubber will also generate the text file `database/schema/schema.txt`. This is a translated .sql file of all the generated tables that can be copy-pasted into [dbdiagram.io](https://dbdiagram.io/) (my database visualizer of choice).

## Teardown

If you wish to remove your generated files, simply run the clearer. *This is mainly used for development and debugging purposes. If you have no intention of deleting everything at the press of a button then feel free to delete this file.*

> [!WARNING]
> This will **DELETE EVERY FILE** in the src and test directories (except for .ignoremes and utils) as well as **DROP ALL THE TABLES IN THE DATABASE**. Be **VERY** certain you do not have any valuable files in these directories before running the clearer.

```zsh
python clear.py
y
```

