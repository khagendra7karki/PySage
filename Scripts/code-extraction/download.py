import os
from dotenv import load_dotenv
import boto3
from smart_open import open

output_dir = './python-dataset'
load_dotenv()



session = boto3.Session(
    aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"])
s3 = session.client("s3")


# from file ids download the content of the files
def download_contents(files, supported_languages):
    out = []
    for file in files:
        if file['language'] not in supported_languages:    # remove non-python files
            continue
        s3_url = f"s3://softwareheritage/content/{file['blob_id']}"
        with open(s3_url, "rb", compression=".gz", transport_params={"client": s3}) as fin:
            file['content'] = fin.read().decode(file['src_encoding'])
            out.append({'path': file['path'], 'content': file['content']})
    return {"files": out}