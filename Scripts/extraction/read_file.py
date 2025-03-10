# reads the python files from jsonl
import json
from datetime import datetime

def deserialize_data(row):
    deserialized_row = json.loads(row)
    
    # Modify date fields to be ISO formatted strings
    # row["visit_date"] = datetime(row["visit_date"])
    # row["revision_date"] = datetime(row["revision_date"])
    # row["committer_date"] = datetime(row["committer_date"])

    # row["gha_created_at"] = datetime(row["gha_created_at"]) if row["gha_created_at"] else ""
    # row["gha_updated_at"] = datetime(row["gha_updated_at"]) if row["gha_updated_at"] else ""
    # row["gha_pushed_at"] = datetime(row["gha_pushed_at"]) if row["gha_pushed_at"] else ""
    return deserialized_row

# generator function to read the content of the file one by one
def read(path):
    '''
        Return the json data of the repository
    '''
    with open(path, 'r') as f:
        for line in f:
            line = f.readline()
            in_json = deserialize_data(line)
            yield in_json