import ujson
import os
import random
from typing import List, Dict, Optional
import transformers
from transformers import PreTrainedTokenizerFast
from collections import Counter
from typing import Generator, Any, List
import multiprocessing as mp
import os
# os.environ["TOKENIZERS_PARALLELISM"] = "false"

FIM_RATE=0.5
# tokenizer = PreTrainedTokenizerFast.from_pretrained("Qwen/Qwen2.5-Coder-0.5B-Instruct")
tokenizer = transformers.AutoTokenizer.from_pretrained("Qwen/Qwen2.5-Coder-0.5B-Instruct")
# Add FIM special tokens (convert to token IDs)
prefix_token_id = tokenizer.convert_tokens_to_ids("<|fim_prefix|>")
suffix_token_id = tokenizer.convert_tokens_to_ids("<|fim_suffix|>")
middle_token_id = tokenizer.convert_tokens_to_ids("<|fim_middle|>")


def load_data(
    file_path: str, 
    previous_idx: int = 0, 
    chunk_size: int = 500
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
    
def apply_fim(tokens: List[int]) -> Dict:
    """
    Apply Fill-in-the-Middle (FIM) transformation
    
    Args:
        tokens (List[int]): Input tokens    
    Returns:
        Dict with FIM-transformed tokens and metadata
    """
    # # If not applying FIM or tokens are too short
    if random.random() > FIM_RATE or len(tokens) < 3:
        return {
            'tokens': tokens,
            'is_fim': False
        }
    
    # Find a random split point
    split_point1 = random.randint(1, len(tokens) - 2)
    split_point2 = random.randint(split_point1 + 1, len(tokens) - 1)
    
    # Split tokens
    prefix = tokens[:split_point1]
    middle = tokens[split_point1:split_point2]
    suffix = tokens[split_point2:]
    
    
    
    # Construct FIM sequence
    fim_tokens = (
        [prefix_token_id] + prefix +
        [suffix_token_id] + suffix +
        [middle_token_id] + middle
    )
    
    return {
        'tokens': fim_tokens,
        'is_fim': True,
        'fim_type': 'fill_middle'
    }

def process_repository(repo_data: Dict) -> List[Dict]:
    """
    Process a repository's files
    
    Args:
        repo_data (Dict): Repository data with files
    
    Returns:
        List of processed training instances
    """
    all_instances = []
    if repo_data["files"] == None:
        return
    for file in repo_data.get('files', []):
        file_instances = tokenize_file(
            file['content']
        )
        
        # Add repository name to instances
        for instance in file_instances:
            instance['repo_name'] = repo_data["repo_name"]
        
        all_instances.extend(file_instances)
    
    return all_instances
    

from typing import List, Dict

def tokenize_file(content: str, chunk_size: int = 1024, overlap_size: int = 256) -> List[Dict]:
    """
    Tokenize a file incrementally to avoid memory spikes, with FIM and overlap handling.
    
    Args:
        content (str): File content.
        chunk_size (int): Target chunk size in tokens.
        overlap_size (int): Number of tokens to overlap between chunks.
        
    Returns:
        List[Dict]: List of tokenized chunks with FIM and chunk metadata.
    """
    all_instances = []
    tokens = []

    # Tokenize the content in manageable slices
    for i in range(0, len(content), 4096):
        tokens.extend(tokenizer.encode(content[i: i + 4096], add_special_tokens=False))

    previous_tokens = []
    buffer_tokens = []

    # Process tokens in chunks with overlap
    i = 0
    while i < len(tokens) or buffer_tokens:
        # Carry over buffer tokens from the previous iteration
        current_tokens = buffer_tokens + tokens[i:i + chunk_size]
        buffer_tokens = []

        # Apply FIM with previous tokens for context
        fim_result = apply_fim(previous_tokens + current_tokens)
        fim_tokens = fim_result["tokens"]

        # Check if the chunk exceeds size after FIM tokens
        if len(fim_tokens) > chunk_size:
            buffer_tokens = fim_tokens[chunk_size:]  # Carry excess tokens to the next chunk
            fim_tokens = fim_tokens[:chunk_size]     # Trim to fit chunk size

        # Handle last chunk with EOS token
        is_last_chunk = i + chunk_size >= len(tokens) and not buffer_tokens
        if is_last_chunk:
            fim_tokens.append(tokenizer.eos_token_id)

        all_instances.append({
            'tokens': fim_tokens,
            'num_tokens': len(fim_tokens),
            'is_fim': fim_result['is_fim'],
            'is_continuation': len(all_instances) > 0,
            'is_last_chunk': is_last_chunk
        })

        # Update previous tokens for the next chunk
        previous_tokens = current_tokens[-overlap_size:] if len(current_tokens) > overlap_size else current_tokens

        # Move to the next chunk
        i += chunk_size

    return all_instances


def process_jsonl_file(input_path: str, 
                        output_path: str,
                        prefix: str):
    """
    Process a JSONL file of repositories
    
    Args:
        input_path (str): Path to input JSONL file
        output_path (str): Path to output processed JSONL file
    """
    for chunk in load_data(input_path):
        processed = []
        for repo in chunk:
            if not (temp := process_repository(repo)):
                continue
        
            processed.extend(temp)

        write_repos(processed, os.path.join(output_path, f"{prefix}.jsonl"))

            


if __name__ == "__main__":

    code_path = './python-dataset/cleaned_scraped_python_code'
    out_dir = './python-dataset/tokenized_scraped_python_code'
    files = os.listdir(code_path)
    files =[os.path.join(code_path, file) for i, file in enumerate(files)]
    
    files = [ os.path.join(code_path, f"data_{i}.jsonl") for i in [2, 4]]
    os.makedirs(out_dir, exist_ok=True)
    for i, file in enumerate(files):

        process_jsonl_file(file, out_dir , f'data_{i + 3}')
