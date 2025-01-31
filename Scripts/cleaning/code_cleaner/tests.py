from collections import defaultdict
import os
import ast
import ujson
import tokenize
from tokenize import STRING, COMMENT
from io import StringIO
from typing import Generator, List, Dict, Any


non_unique_repos = []

def check_unique(code_dir='./python-dataset/raw-code'):
    repo_names = set()
    file_paths = [os.path.join(code_dir, file) for file in os.listdir(code_dir)]
    total_data = 0
    prev_len = 0
    for file_path in file_paths:
        line_no = 0 # line no. in the file, zero based
        with open(file_path, 'r') as f:
            for l in f:
                repo_name = ""
                quote_count = 0
                for char in l:
                    if char == '"':
                        quote_count += 1
                    else: 
                        if quote_count == 3:
                            repo_name += char
                        elif quote_count == 4:
                            # print(repo_name)
                            break
                        
                        

                repo_names.add(repo_name)

                if len(repo_names) == prev_len:
                    print("The non unique repo is", repo_name, " at line ", line_no + 1)
                    non_unique_repos.append({"repo_name": repo_name, "file_path": file_path, "line_no": line_no})
                prev_len  = len(repo_names)
                total_data += 1
                line_no += 1
        
        print(f'{file_path} finished')

    with open('non_unique_repo.json', 'w') as f:
        f.write(ujson.dumps(non_unique_repos))
    
    
    print("Total repositories", total_data)
    print("Unique repositories", len(repo_names))
    
    return total_data == len(repo_names)

def check_syntax(code: str) -> bool:
    """Check if Python code is syntactically correct."""
    try:
        ast.parse(code, "<string>", "exec")
        return True
    except SyntaxError:
        return False
    except Exception:
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
        
    except IOError:
        print("IOError")
        return []

def remove_non_unique_files():
    # Load non-unique repositories data
    with open('non_unique_repo.json', 'r') as f:
        non_unique_repos = ujson.load(f)
    
    # Group line numbers by file_path (0-based line numbers)
    file_to_lines = defaultdict(set)
    for repo in non_unique_repos:
        file_to_lines[repo['file_path']].add(repo['line_no'])
    
    # Process each file
    for file_path, lines_to_remove in file_to_lines.items():
        tmp_file = f"tmp_{os.path.basename(file_path)}"
        
        with (
            open(file_path, 'r') as org,
            open(tmp_file, 'w') as cpy
        ):
            # Process line-by-line with 0-based index
            for line_number, line in enumerate(org):
                if line_number not in lines_to_remove:
                    cpy.write(line)  # Line already contains newline character
                    
def check_all_syntax():
    code_dir = './python-dataset/syntax_correct_data'
    file_paths = [os.path.join(code_dir, file) for file in os.listdir(code_dir)]

    for file_path in file_paths:
        with open(file_path, 'r') as f:
            for l in f:
                repo = ujson.loads(l)

                for file in repo['files']:
                    content = file.get('content', '')

                    try:
                        compile(content, "<string>", "exec")
            
                    except Exception as e:
                        print(content)
                        print("The cause \n", e)
                        raise Exception("Test failed")

def cleaned_data_tests():
    #  class to catch Invalid Syntax
    class InvalidSyntax(Exception):
        pass


    # class to catch Non English token occurrence
    class NonEnglish(Exception):
        pass
    def test_syntax(code):
        try:
            ast.parse(code)
            return True
        except Exception as e:
            raise InvalidSyntax("Syntax Error") from e
        
    def test_non_english(code):
        tokens = tokenize.generate_tokens(StringIO(code).readline)
        for token in tokens:
            if token.type in (STRING, COMMENT):
                if any( ord(char) > 127 for char in token.string):
                    raise NonEnglish("Token consists of non english character")

    cleaned_data_dir = './python-dataset/cleaned_data'
    
    files = os.listdir(cleaned_data_dir)
    file_paths = [os.path.join(cleaned_data_dir, file) for file in files]
    current_content = None
    try: 
        for file_path in file_paths:
            data_loader = load_data(file_path)
            for chunk in data_loader:
                for repo in chunk:
                    for file in repo['files']:
                        current_content= file['content']
                        test_syntax(current_content)
                        test_non_english(current_content)
        
        print("All test passed")
    except InvalidSyntax as e:
        with open("invalid_syntax.py", 'w') as f:
            f.write(current_content) 
    except NonEnglish as e:
        with open("nonenglish.py", 'w') as f:
            f.write(current_content)

    



                    
                    

if __name__ == '__main__':
    # print(check_unique())
    # try:
    #     check_all_syntax()
    #     print("Test passed")
    # except Exception as e:
    #     print("Test failed")
    cleaned_data_tests()

    # remove_non_unique_files()

