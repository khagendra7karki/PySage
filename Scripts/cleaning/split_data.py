import os
import json
from typing import List, Dict, Any, Generator

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
                json_code = json.loads(line)
                code.append(json_code)
                
                if len(code) == chunk_size:
                    yield code
                    code = []
            if code:
                yield code
        
    except IOError as e:
        return []
    
def split(file_to_split: str, out_dir: str, file_prefix,  n_split: int):
    data_loader = load_data(file_to_split, 0, n_split * 1000)
    file_names = [os.path.join(out_dir, f'{file_prefix}_{i}.jsonl') for i in range(n_split)]

    for data in data_loader:
        chunks = [data[i::n_split] for i in range(n_split)]

        for chunk_i, chunk in enumerate(chunks):
            with open(file_names[chunk_i], 'a') as f:
                f.writelines([json.dumps(repo) + '\n' for repo in chunk])

if __name__ == '__main__':
    split('./python-dataset/code.jsonl', './python-dataset/raw-code/', 'code', 8)



    
