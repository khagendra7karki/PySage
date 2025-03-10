from cleaner import clean_python_code   # removes non english tokens
from normalize_code import format_code  # Normalizes code and removes whitespaces
from check_syntax import check_syntax
import ujson
from typing import Generator, List, Dict, Any
import os
import multiprocessing as mp


def load_data(
    file_path: str, 
    previous_idx: int = 0, 
    chunk_size: int = 30000
) -> Generator[List[Dict[str, Any]], None, None]:
    """
    Load data from JSONL file in chunks.
    
    Args:
        file_path (str): Path to JSONL file
        previous_idx (int): Index to start reading from
        chunk_size (int): Number of lines to read
    
    Returns:
        Generator yielding lists of repository data
    """
    try:
        with open(file_path, 'r') as f:
            # Skip to previous index
            for _ in range(previous_idx):
                next(f, None)
            
            code = []
            for line in f:
                json_code = ujson.loads(line)
                code.append(json_code)
                
                if len(code) == chunk_size:
                    yield code
                    code = []
            if code:
                yield code
        
    except IOError:
        print("IOError")
        return []

def write_repos(repos: List[str], output_path: str):
    """
    Write syntax-free repository names to a file.
    
    Args:
        repos (List[str]): Repository names
        output_path (str): Path to output file
    """


    with open(output_path, 'a') as f:
        for repo in repos:
            f.write(ujson.dumps(repo) + '\n')


def task_process(idx,code_file,  out_dir, prefix, lock):
    out_file =os.path.join(out_dir, f'{prefix}_{idx}.jsonl')
    data_loader = load_data(code_file)
    for chunk in data_loader:
        # cleaned_repos = []
        for repo in chunk:
            files = []  # Stores the cleaned files
            try:
                for file in repo['files']:
                    if not check_syntax(file['content']):
                        continue
                    clean_code=format_code(file["content"])
                    clean_code = clean_python_code(clean_code)

                    file['content'] = clean_code

                    files.append(file)
                
                repo['files'] = files


            except Exception as e:
                with lock:
                    print(e)
                    with open("errors.jsonl", 'a') as f:
                        f.write(ujson.dumps(repo) + '\n')

        write_repos(chunk, out_file)

if __name__ == "__main__":
    # test()
    # check_errors()
     code_path = './python-dataset/scraped_python_code'
     out_dir = './python-dataset/cleaned_scraped_python_code'
     files = os.listdir(code_path)
     num_workers = min(mp.cpu_count(), len(files))

    
     os.makedirs(out_dir, exist_ok=True)
     with mp.Manager() as manager:
         lock = manager.Lock()

         with mp.Pool(processes=num_workers) as pool:
             pool.starmap(task_process, [(i, os.path.join(code_path, file), out_dir, 'data', lock) for i, file in enumerate(files)])
