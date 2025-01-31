import ast
import multiprocessing as mp
from typing import List, Dict, Any, Generator
import os
import ujson
import tokenize
# format  of repository jsonl file
'''
{
    "repo_name": <str>,
    "files": [
        {
            "path": <str>,
            "content": <str>
        }
    ]
}
'''



def check_syntax(code: str ) -> bool:
    """
    Check Python syntax and attempt to fix if there's an error.
    
    Args:
        code (str): Python code to check
    
    Returns:
        tuple[bool, str]: (True if valid syntax, potentially fixed code)
    """
    try:
        ast.parse(code) 
        return True
    except Exception as e:
        return False

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
        
    except IOError as e:
        print("IOError")
        return []

def process_chunk(data: List[Dict[str, Any]]) -> List[str]:
    """
    Process a chunk of repository data and return syntax-free repos.
    """
    out = []
    for repo in data:
        valid = True
        for file in repo['files']:
            content = file.get('content', '')
            if not content or not check_syntax(content):
                valid = False

        if valid and repo['files']:
            out.append(repo)

    return out


def write_repos(repos: Dict[str, str], output_path: str):
    """Batch write with buffered output"""
    with open(output_path, 'a', buffering=64*1024) as f:
        batch = '\n'.join(ujson.dumps(repo) for repo in repos)
        f.write(batch + '\n')


# task for each process
def process_task(
    idx: int,
    code_path: str, 
    output_dir: str,
    out_file_prefix: str
) -> float:
    """
    Process data chunks using multiprocessing.
    
    Args:
        idx: Relative index of the process -> Range(0, num_workers)
        code_path (str): Path of the source code
        output_dir (str): Directory to write output files
        out_file_prefix (str): Prefix of the output file, usage -> out_file_prefix_{idx}.jsonl
    
    Returns:
        float: Total processing time
    """
    data_generator = load_data(code_path, 0, 8000)
    output_file = os.path.join(output_dir, f'{out_file_prefix}_{idx}.jsonl')

    for chunk in data_generator:
        processed_repos = process_chunk(chunk)
        # for each process, write to a different file
        write_repos(processed_repos, output_file)
    

def main():
    code_dir = './python-dataset/raw-code'
    output_dir = './python-dataset/syntax_correct_data'
    
    code_file_paths = [os.path.join(code_dir, file_name) for file_name in os.listdir(code_dir)]
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Determine optimal number of processes
    num_workers = min(mp.cpu_count(), len(code_file_paths))

    with mp.Pool(processes=num_workers) as pool:
        pool.starmap(
            process_task, 
            [(idx, file_path, output_dir, 'syntx_correct') for idx, file_path in enumerate(code_file_paths)],
            )



if __name__ == "__main__":
    main()

