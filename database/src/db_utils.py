import os

import psycopg2
import psycopg2.extras
import yaml

psycopg2.extras.register_uuid()

def setup_database_schema():
    exec_sql_file("schema/reset_database.sql")

    exec_sql_file("schema/public/users.sql")
    exec_sql_file("schema/public/balance_events.sql")
    exec_sql_file("schema/public/budget_goals.sql")
    exec_sql_file("schema/public/expense_category.sql")
    exec_sql_file("schema/public/income_sources.sql")

# Attribution: Taken from past RIT classes and slightly modified

def connect_to_db(config_file_path: str = '../config/db.yml'):
    yml_path = os.path.join(os.path.dirname(__file__), config_file_path)

    with open(yml_path, 'r') as file:
        config = yaml.load(file, Loader=yaml.BaseLoader)

        return psycopg2.connect(
            dbname=config['database'],
            user=config['user'],
            password=config['password'],
            host=config['host'],
            port=config['port']
        )


def exec_sql_file(path):
    full_path = os.path.join(os.path.dirname(__file__), f'../{path}')
    conn = connect_to_db()
    cur = conn.cursor()
    with open(full_path, 'r') as file:
        cur.execute(file.read())
    conn.commit()
    conn.close()


def exec_get_one(sql, args={}):
    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute(sql, args)
    one = cur.fetchone()
    conn.close()
    return one


def exec_get_all(sql, args={}):
    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute(sql, args)
    list_of_tuples = cur.fetchall()
    conn.close()
    return list_of_tuples


def exec_commit(sql, args={}):
    conn = connect_to_db()
    cur = conn.cursor()
    result = cur.execute(sql, args)
    conn.commit()
    conn.close()
    return result


def exec_commit_returning(sql, args={}):
    """Execute a write query that RETURNS rows (e.g., INSERT ... RETURNING)."""
    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute(sql, args)
    rows = cur.fetchall()
    conn.commit()
    conn.close()
    return rows


def initialize_db():
    conn = connect_to_db()
    cur = conn.cursor()

    for path in os.listdir("database/schema/"):
        if ".sql" not in path: continue
        full_path = os.path.join(os.path.dirname(__file__), f'../schema/{path}')
        with open(full_path, 'r') as file:
            cur.execute(file.read())
    conn.commit()
    conn.close()
