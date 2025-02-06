import ast
import tokenize
import multiprocessing as mp
import os
import sys
from typing import List, Dict, Any, Generator
import ujson
import logging
from io import StringIO

# Count number of leading blanks.
def getlspace(line):
    i, n = 0, len(line)
    while i < n and line[i] == " ":
        i += 1
    return i

def usage(msg=None):
    if msg is None:
        msg = __doc__
    print(msg, file=sys.stderr)


def errprint(*args):
    sys.stderr.write(" ".join(str(arg) for arg in args))
    sys.stderr.write("\n")




def _rstrip(line, JUNK='\n \t'):
    """Return line stripped of trailing spaces, tabs, newlines.

    Note that line.rstrip() instead also strips sundry control characters,
    but at least one known Emacs user expects to keep junk like that, not
    mentioning Barry by name or anything <wink>.
    """

    i = len(line)
    while i > 0 and line[i - 1] in JUNK:
        i -= 1
    return line[:i]

class Reindenter:
    def __init__(self):
        pass

    def run(self, code, space_per_indent):
        self.level=0    # current indent level
        self.find_stmt = 1 # next token begins a fresh stmt?
        self.index=1    # index into self.lines of next line

        # List of (lineno, indentlevel) pairs, one for each stmt and
        # comment line.  indentlevel is -1 for comment lines, as a
        # signal that tokenize doesn't know what to do about them;
        # indeed, they're our headache!
        self.stats=[]
        self.raw = code.splitlines()
        self.lines =[_rstrip(line).expandtabs() + "\n"
                    for line in self.raw]
        self.lines.insert(0, None)

        tokens = tokenize.generate_tokens(self.getline)
        try: 
    
            for _token in tokens:
                self.tokeneater(*_token)
        except Exception as e:
            raise Exception("An exception occurred ", e)
            
        # Remove trailing empty lines.
        lines = self.lines
        while lines and lines[-1] == "\n":
            lines.pop()
        # Sentinel.
        stats = self.stats
        stats.append((len(lines), 0))
        # Map count of leading spaces to # we want.
        have2want = {}
        # Program after transformation.
        after = self.after = []
        # Copy over initial empty lines -- there's nothing to do until
        # we see a line with *something* on it.
        i = stats[0][0]
        after.extend(lines[1:i])
        for i in range(len(stats) - 1):
            thisstmt, thislevel = stats[i]
            nextstmt = stats[i + 1][0]
            have = getlspace(lines[thisstmt])
            want = thislevel * space_per_indent
            if want < 0:
                # A comment line.
                if have:
                    # An indented comment line.  If we saw the same
                    # indentation before, reuse what it most recently
                    # mapped to.
                    want = have2want.get(have, -1)
                    if want < 0:
                        # Then it probably belongs to the next real stmt.
                        for j in range(i + 1, len(stats) - 1):
                            jline, jlevel = stats[j]
                            if jlevel >= 0:
                                if have == getlspace(lines[jline]):
                                    want = jlevel * space_per_indent
                                break
                    if want < 0:           # Maybe it's a hanging
                                           # comment like this one,
                        # in which case we should shift it like its base
                        # line got shifted.
                        for j in range(i - 1, -1, -1):
                            jline, jlevel = stats[j]
                            if jlevel >= 0:
                                want = have + (getlspace(after[jline - 1]) -
                                               getlspace(lines[jline]))
                                break
                    if want < 0:
                        # Still no luck -- leave it alone.
                        want = have
                else:
                    want = 0
            assert want >= 0
            have2want[have] = want
            diff = want - have
            if diff == 0 or have == 0:
                after.extend(lines[thisstmt:nextstmt])
            else:
                for line in lines[thisstmt:nextstmt]:
                    if diff > 0:
                        if line == "\n":
                            after.append(line)
                        else:
                            after.append(" " * diff + line)
                    else:
                        remove = min(getlspace(line), -diff)
                        after.append(line[remove:])
        return "".join(self.after)



    # Line-getter for tokenize.
    def getline(self):
        if self.index >= len(self.lines):
            line = ""
        else:
            line = self.lines[self.index]
            self.index += 1
        return line

    # Line-eater for tokenize.
    def tokeneater(self, type, token, slinecol, end, line,
                   INDENT=tokenize.INDENT,
                   DEDENT=tokenize.DEDENT,
                   NEWLINE=tokenize.NEWLINE,
                   COMMENT=tokenize.COMMENT,
                   NL=tokenize.NL):

        if type == NEWLINE:
            # A program statement, or ENDMARKER, will eventually follow,
            # after some (possibly empty) run of tokens of the form
            #     (NL | COMMENT)* (INDENT | DEDENT+)?
            self.find_stmt = 1

        elif type == INDENT:
            self.find_stmt = 1
            self.level += 1

        elif type == DEDENT:
            self.find_stmt = 1
            self.level -= 1

        elif type == COMMENT:
            if self.find_stmt:
                self.stats.append((slinecol[0], -1))
                # but we're still looking for a new stmt, so leave
                # find_stmt alone

        elif type == NL:
            pass

        elif self.find_stmt:
            # This is the first "real token" following a NEWLINE, so it
            # must be the first token of the next program statement, or an
            # ENDMARKER.
            self.find_stmt = 0
            if line:   # not endmarker
                self.stats.append((slinecol[0], self.level))

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
        logging.error(f"Error reading file {file_path}: {e}")
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

def is_not_english(s: str) -> bool:
    """
    Detect if s contains non-English characters (ASCII > 127).

    Parameters:
        s (str): Input string.

    Returns:
        bool: True if the string contains only English characters, False otherwise.
    """
    return any(ord(char) > 127 for char in s)

def normalize_string(token: str) -> str:
    """
    Normalizes a Python string token from the `tokenize` library, including f-strings.
    
    Converts single-quoted strings to double-quoted strings, preserves prefixes (e.g., u, r, b, f), 
    and replaces non-English strings with a placeholder.

    Parameters:
        token (str): String token from `tokenize`.

    Returns:
        str: Normalized string token.
    """
    # Identify the string prefix (if any)
    # prefixes = {"f", "u", "r", "b", "fr", "rf", "ur", "br", "rb"}
    # prefix_end = 0
    is_triple = False
    if len(token) >= 6 and token[-3] == token[-2] == token[-1]: 
        is_triple= True

    # Handle non-English content

    if is_not_english(token):
        return '"""<NON ENGLISH STRING>"""' if is_triple else '"<NON ENGLISH STRING>"'

    return token

def normalize_code(code: str) -> str:
    """
    Cleans and normalizes Python code.

    Parameters:
        code (str): Input Python code.

    Returns:
        str: Processed Python code with normalized strings, filtered comments, 
             and consistent spacing.
    """
    # remove all Line Separator and paragraph separator
    # code = code.replace()
    tokens = tokenize.generate_tokens(StringIO(code).readline)
    buffer = []  # Buffer to handle spaces or line breaks properly
    prev_end = (0, 0)
    for token in tokens:
        

        if  prev_end[0] == token.start[0]: # The tokens lie on the same line
            token = token._replace(start = (token.start[0], min(prev_end[1] + 2, token.start[1])))
        if token.type == tokenize.STRING:
            # Normalize strings
            new_token = token._replace(string=normalize_string(token.string))
            buffer.append(new_token)
        elif token.type == tokenize.COMMENT:
            # Filter comments with non-English characters
            if not is_not_english(token.string):
                buffer.append(token)
        else:
            # Include other tokens as-is
            buffer.append(token)
        
        prev_end = token.end
        out = tokenize.untokenize(buffer)
    return out

def task_process(idx,code_file,  out_dir, prefix, lock):
    out_file =os.path.join(out_dir, f'{prefix}_{idx}.jsonl')
    data_loader = load_data(code_file)
    r = Reindenter()
    for chunk in data_loader:
        # cleaned_repos = []
        for repo in chunk:
            files = []  # Stores the cleaned files
            try:
                for file in repo['files']:
                    code = normalize_code(file['content'])
                    code = r.run(code, SPACE_PER_INDENT)

                    files.append(file)
                
                repo['files'] = files


            except Exception as e:
                with lock:
                    print(e)
                    with open("errors.jsonl", 'a') as f:
                        f.write(ujson.dumps(repo) + '\n')

        write_repos(chunk, out_file)


def test ():
#     code = """
# def       hello_world():
#     x =     r'single"" quoted string'
#     y = '''triple
#     quoted
#     string'''
#     # This is an example comment
#     # 中文注释 (Non-English comment)
#     if True:
#         print('hello world')
#     return  x            + y
    
# """
    r = Reindenter()

    # code = r.run(code, SPACE_PER_INDENT)
    # code = normalize_code(code)
    # print(code)
    with open('./errors.jsonl', 'r') as f:
        for l in f:
            repo = ujson.loads(l)
        

            org = "".join(file['content'] for file in repo['files'])
            modified = ""
            for file in repo['files']:

                try:
                    code = normalize_code(file['content'])
                    ast.parse(code)
                    

                except Exception as e:
                    print(e)
                    with (

                        open('original.py', 'w') as o,
                        open('cleaned.py', 'w') as c
                    ):
                        o.write(file['content'])
                        c.write(code)
                    break


                code = r.run(code, 4)
                


            break

SPACE_PER_INDENT=4
# Example usage:
if __name__ == "__main__":
    # test()
    code_path = './python-dataset/syntax_correct_data'
    out_dir = './python-dataset/cleaned_data'
    files = os.listdir(code_path)
    num_workers = min(mp.cpu_count(), len(files))

    
    os.makedirs(out_dir, exist_ok=True)
    with mp.Manager() as manager:
        lock = manager.Lock()

        with mp.Pool(processes=num_workers) as pool:
            pool.starmap(task_process, [(i, os.path.join(code_path, file), out_dir, 'data', lock) for i, file in enumerate(files)])


