# check how many file, and which files have been downloaded
import os
import json

file_dir = './new-python-dataset'
file_name = 'code.jsonl'

log_dir = file_dir
log_file_name = 'repo_names.jsonl'

metadata_dir = file_dir
metadata_file_name = 'metadata.json'


last=""

def update_metadata(data, metadata):
#update_metadata
    metadata['total_repos'] +=1
    metadata['min_no_file']=min(metadata['min_no_file'], data['num_files'])
    metadata['max_no_file']=max(metadata['min_no_file'], data['num_files'])
    metadata['total_files']=data['num_files']

    for file in data['files']:
        metadata['total_python_files'] += (1 if file['language'] == 'Python' else 0)
        metadata['size_of_python_files'] += int(file['length_bytes'])

    print(metadata)

def check_files(data_file, log_path, meta_path):
    metadata = {
    'total_repos': 0,
    'min_no_file': 100000000,
    'max_no_file': -100000000,
    'total_files': 0,
    'avg_files': 0,
    'total_python_files': 0,
    'avg_python_files': 0,
    'size_of_python_files': 0       # in bytes
    }
    lines_to_skip = 0

    # load the data if they exists
    if os.path.exists(log_path): 
        
        # if metadata path doesn't exist erase it
        if not os.path.exists(meta_path):
            with open(log_path, 'w'):
                pass
        else:
            with open(meta_path, 'r') as m: # load the metadata
                metadata=json.loads(m)

        l=open(log_path, 'r')
        lines_to_skip=sum(1 for _ in l)
    

    with open(data_file, 'r') as f, open(log_path, 'a') as l:
        for _ in range(lines_to_skip):
            next(f, None)

        for line in f:
            json_content = json.loads(line)
            last=json_content

            # write the repository name
            l.write(json_content['repo_name'] + '\n')
            
            #update_metadata
            print('invoking')
            update_metadata(json_content, metadata)
            break
    # print(metadata)
    metadata['avg_files'] = metadata['total_files'] / metadata['total_repos']
    metadata['avg_python_files'] = metadata['total_python_files'] / metadata['total_repos']
    
    with open(meta_path, 'w') as m:
        m.write(json.dumps(metadata))


file_path=os.path.join(file_dir, file_name)
log_path=os.path.join(log_dir, log_file_name)
meta_path=os.path.join(metadata_dir, metadata_file_name)

if __name__=='__main__':

    check_files(file_path, log_path, meta_path)
    