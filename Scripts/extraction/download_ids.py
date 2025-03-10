from datasets import load_dataset
import json

if __name__  == '__main__':
    supported_languages = ['Python']
    # Load the dataset
    ds = load_dataset("bigcode/the-stack-v2-train-smol-ids", streaming=True, split="train")
    # Filter to only keep supported languages
    ds = ds.filter(lambda row: row['gha_language'] in supported_languages)
    i = 0
    with open('./repo-id/ids.jsonl', 'a') as f:
        for row in ds:
            row["visit_date"] = row["visit_date"].isoformat()
            row["revision_date"] = row["revision_date"].isoformat()
            row["committer_date"] = row["committer_date"].isoformat()

            row["gha_created_at"] = row["gha_created_at"].isoformat() if row["gha_created_at"] else ""
            row["gha_updated_at"] = row["gha_updated_at"].isoformat() if row["gha_updated_at"] else ""
            row["gha_pushed_at"] = row["gha_pushed_at"].isoformat() if row["gha_pushed_at"] else ""
            
            json_content = json.dumps(row)

            f.write(json_content+'\n')
            i+=1
            print(i, row['repo_name'])

# Maxklos/WeatherProjekt