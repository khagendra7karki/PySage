import ujson
import subprocess
from typing import List, Dict, Any, Generator
from pathlib import Path
import multiprocessing as mp
import os
compile()
def format_code(code: str) -> str:
    """Format code with a dedicated Ruff process per call (safe and simple)."""
    try:
        result = subprocess.run(
            ["ruff", "format", "-"],
            input=code,
            text=True,
            capture_output=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        # print(f"Error: {e.stderr}")
        raise(Exception(e.stderr))


def load_data(
    file_path: str, 
    previous_idx: int = 0, 
    chunk_size: int = 3000
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
        
    except IOError as e:
        # logging.error(f"Error reading file {file_path}: {e}")
        return []
    
def task_process(idx,code_file,  out_dir, prefix, lock):
    out_file =os.path.join(out_dir, f'{prefix}_{idx}.jsonl')
    data_loader = load_data(code_file)
    break_flag = False      # Flag to end the loop
    for chunk in data_loader:
        if break_flag:
            break
        # cleaned_repos = []
        for repo in chunk:
            if break_flag:
                break
            files = []  # Stores the cleaned files
            try:
                for file in repo['files']:
                    code = format_code(file['content'])
                    files.append(code)
                

                repo['files'] = files


            except Exception as e:
                # with lock:
                print(e)
                # with open(f'original_{idx}.py', 'w') as o:
                #     o.write(file['content'])
                #     # r.write()
                #     break_flag = True
                    # with open("errors.jsonl", 'a') as f:
                    #     f.write(ujson.dumps(repo) + '\n')

        write_repos(chunk, out_file)


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

def test(code: str) -> str:
    formatted_code = format_code(code)
    return formatted_code

def main():
    code_path = './python-dataset/syntax_correct_data'
    out_dir = './python-dataset/normalized_data'
    files = os.listdir(code_path)
    num_workers = min(mp.cpu_count(), len(files))

    os.makedirs(out_dir, exist_ok=True)

    with mp.Manager() as manager:
        lock = manager.Lock()

        with mp.Pool(processes=num_workers) as pool:
            pool.starmap(task_process, [(i, os.path.join(code_path, file), out_dir, 'data', lock) for i, file in enumerate(files)])


if __name__ == "__main__":
    code = """import random

print("Hello world")
if True:
  print("Hey World")
else:
  print("Nothing")
"""
    # print(test(code))
    main()