import json
import os
import subprocess

from database.src import db_utils

def remove(file_path, rf = False):
    try: # MacOS
        if rf:
            subprocess.run(["rm","-rf",file_path])
        else:
            subprocess.run(["rm",file_path])
    except: # Windows
        if rf:
            subprocess.run(["rd","/s","/q",file_path.replace("/","\\")],shell=True)
        else:
            subprocess.run(["del",file_path.replace("/","\\")],shell=True)


def main():
    dirs = ["api","database"]
    subdirs = ["src","tests"]
    with open("models.json","r") as f:
        modules = json.load(f)

    sql = "DROP TABLE IF EXISTS "
    for i,module in enumerate(modules):
        sql += module
        if i < len(modules)-1: sql += ", "
    db_utils.exec_commit(sql)

    gen = ((direct, subdir) for direct in dirs for subdir in subdirs)
    for (direct, subdir) in gen:
        for file in os.listdir(f"{direct}/{subdir}"):
            if file in ["db_utils.py","test_utils.py",".ignoreme"]: continue
            full_path = os.path.join(os.path.dirname(__file__), f'{direct}/{subdir}/{file}')
            if file == "__pycache__": remove(full_path, True)
            else: remove(full_path)
    

    for file in os.listdir(f"database/schema"):
        if file == ".ignoreme": continue
        full_path = os.path.join(os.path.dirname(__file__), f'database/schema/{file}')
        remove(full_path)

    full_path = os.path.join(os.path.dirname(__file__), 'api/server.py')
    remove(full_path)


if __name__ == "__main__":
    print("Are you sure you want to delete all files (y/n)?")
    put = input()
    if put == "y":
        main()
