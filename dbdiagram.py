"""
For the purposes of transforming the .sql files into the format used by dbdiagram.io
"""

import os
import re

def translate():
    result = ""
    for file in os.listdir("database/schema"):
        if ".sql" not in file: continue
        with open("database/schema/"+file, "r") as f:
            while line := f.readline():
                line = re.sub(r"CREATE TABLE( IF NOT EXISTS)?","TABLE",line,flags=re.IGNORECASE)
                line = re.sub(r"\(\s*$","{\n",line,flags=re.IGNORECASE)
                line = re.sub(r"^\)","}",line,flags=re.IGNORECASE)
                line = re.sub(r"\s*,","",line,flags=re.IGNORECASE)
                line = re.sub(r"^\s+(?P<col>\w+)\s+(?P<type>[\w\(\)]+)\s*(?P<args>.*)\s*",r"\t\1\t\2\t[\3]\n",line,flags=re.IGNORECASE)
                line = re.sub(r"PRIMARY KEY","PK,",line,flags=re.IGNORECASE)
                line = re.sub(r"DEFAULT ([a-zA-Z_\(\)]+)",r"DEFAULT: '\1',",line,flags=re.IGNORECASE)
                line = re.sub(r"DEFAULT '(.*)'",r"DEFAULT: '\1',",line,flags=re.IGNORECASE)
                line = re.sub(r"REFERENCES (\w+) ",r"REF: - \1, ",line,flags=re.IGNORECASE) # Default to 1-1
                line = re.sub(r"CHECK\s*\(.*\)",r"",line,flags=re.IGNORECASE)
                line = re.sub(r"NOT NULL",r"NOT NULL,",line,flags=re.IGNORECASE)
                line = re.sub(r"UNIQUE",r"UNIQUE,",line,flags=re.IGNORECASE)
                line = re.sub(r"\s*,\s*\]","]",line,flags=re.IGNORECASE)
                line = re.sub(r";","",line,flags=re.IGNORECASE)

                result += line
        result += "\n"
    return result


if __name__ == "__main__":
    print(translate())