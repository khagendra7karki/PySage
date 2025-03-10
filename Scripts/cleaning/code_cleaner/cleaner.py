import ujson
from typing import List, Generator, Dict, Any
import tokenize
import io
import os
import multiprocessing as mp
import re
import ast


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


def to_original(cleaned_file_name, repo_name, file_path):
    original_dir = './new-python-dataset/syntax_free_repos'
    prefix = 'syntax_free_repos'

    mapped_file = os.path.join(original_dir, f'{prefix}_{cleaned_file_name[-7]}.jsonl')
    with open(mapped_file, 'r') as f:
        for line in f:
            
            file_repo_name =""
            for char in line[15:]:
                # print(char)
                if char == '"':
                    break
                file_repo_name += char
            
            print(cleaned_file_name[-7], file_repo_name, repo_name)

            if file_repo_name != repo_name:
                continue
            

            repo = ujson.loads(line)
            for file in repo['files']:
                if file['path'] == file_path:
                    return file['content']





def is_english(text):
    """Check if text contains only ASCII characters."""
    return re.match(r'^[\x00-\x7F]*$', text) is not None


def clean_python_code(content: str):
    """
    Process Python code to replace non-English strings and remove non-English comments.
    
    Args:
        content: String content of a Python file
        output_file: File to write output to (stdout if None)
    """
    # Create a tokenizer for the source
    source_io = io.StringIO(content.expandtabs(4))
    tokens = tokenize.generate_tokens(source_io.readline)
    
    # Prepare the output
    output = io.StringIO()
    prev_token_end = (1, 0)
    
    for token in tokens:
        token_type = token.type
        token_string = token.string
        start_line, start_col = token.start
        end_line, end_col = token.end
        
        # Handle whitespace between tokens
        if start_line > prev_token_end[0]:
            # Add newlines for any skipped lines
            # output.write('\n' * (start_line - prev_token_end[0]))
            # Reset column position
            prev_token_end = (start_line, 0)
        
        # Add spaces to align with the current token
        if start_col > prev_token_end[1]:
            # print(start_col - prev_token_end[1])
            output.write(' ' * (start_col - prev_token_end[1]))
        
        # Process based on token type
        if token_type == tokenize.STRING:
            
            # Regular string
            if token_string[-3:] in ('"""', "'''"):
                           
                if not is_english(token_string):
                    output.write('"""<<<NON_ENGLISH_TEXT>>>"""')
                else:
                    output.write(token_string)
            else:
                if not is_english(token_string):
                    output.write('"<<<NON_ENGLISH_TEXT>>>"')
                else:
                    output.write(token_string)
        
        elif token_type == tokenize.COMMENT:
            # Handle comments
            comment_text = token_string[1:].strip()  # Remove the # character
            if is_english(comment_text):
                output.write(token_string)
        
        elif token_type != tokenize.NL and token_type != tokenize.INDENT\
              and token_type != tokenize.DEDENT:
            
            output.write(token_string)
            if token.line[token.end[1]:].lstrip() == '\\\n':

                output.write(' \\\n')
            
            

        
        else:
            # Other token types remain unchanged
            output.write(token_string)
        
        prev_token_end = end_line, end_col
    
    # Get the processed content
    result = output.getvalue()
    
    return result

def task_process(idx,code_file,  out_dir, prefix, lock):
    out_file =os.path.join(out_dir, f'{prefix}_{idx}.jsonl')
    data_loader = load_data(code_file)
    for chunk in data_loader:
        # cleaned_repos = []
        for repo in chunk:
            files = []  # Stores the cleaned files
            try:
                for file in repo['files']:
                    code = clean_python_code(file['content'])
                    file['content'] = code

                    files.append(file)
                
                repo['files'] = files


            except Exception as e:
                with lock:
                    print(e)
                    with open("errors.jsonl", 'a') as f:
                        f.write(ujson.dumps(repo) + '\n')

        write_repos(chunk, out_file)


def test ():
    code = """
def       hello_world():
    x =     r'single"" quoted string'
    y = '''triple
    quoted
    string'''
    # This is an example comment
    # 中文注释 (Non-English comment)
    if True:
        print('hello world')
    return  x            + y
    
"""

    code_path = './python-dataset/syntax_correct_data'
    out_dir = './python-dataset/cleaned_data'
    files = os.listdir(code_path)
    

    # max = 100
    # count = 0
    f = open("errors.jsonl", 'w')    
    for file in files:
        data_loader = load_data(os.path.join(code_path, file))
        for chunk in data_loader:
            for repo in chunk:
                for file in repo['files']:
                    # if count == max:
                    #     return
                    # count += 1
                    cleaned_code =  clean_python_code(file['content'])
                    try:
                        ast.parse(cleaned_code)

                    except Exception as e:
                        print(e)
                        f.write(ujson.dumps(file) + '\n')
        break
    f.close()


def check_errors():
    data_loader = load_data('errors.jsonl')
    for chunk in data_loader:
        file = chunk[0]
    # for i, file in enumerate(chunk):
        with open('original.py', 'w') as o, open('sanitized.py', 'w') as s:
            o.write(file['content'])
            s.write(clean_python_code(file['content']))
            break
        break

        

# Example usage:
if __name__ == "__main__":
    # test()
    # check_errors()
     code_path = './python-dataset/normalized_data'
     out_dir = './python-dataset/cleaned_data'
     files = os.listdir(code_path)
     num_workers = min(mp.cpu_count(), len(files))

    
     os.makedirs(out_dir, exist_ok=True)
     with mp.Manager() as manager:
         lock = manager.Lock()

         with mp.Pool(processes=num_workers) as pool:
             pool.starmap(task_process, [(i, os.path.join(code_path, file), out_dir, 'data', lock) for i, file in enumerate(files)])


