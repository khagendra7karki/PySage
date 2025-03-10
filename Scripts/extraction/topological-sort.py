import re
import os
from collections import defaultdict, deque
from read_file import read

def has_dependency(fileA_content, fileB_name):
    import_pattern = re.compile(rf'import\s+{re.escape(fileB_name)}|from\s+{re.escape(fileB_name)}\s+import')
    return bool(import_pattern.search(fileA_content))

def parse_files(directory_metadata):
    files = [file['path'] for file in directory_metadata['files'] if file['path'].endswith('.py')]
    graphs = defaultdict(list)
    in_degree = defaultdict(int)
    file_contents = {}

    for file in directory_metadata['files']:
        if file['path'].endswith('.py'):
            file_contents[file['path']] = file['content']  # Assuming 'content' field exists

    for fileA in files:
        for fileB in files:
            if fileA != fileB and has_dependency(file_contents[fileA], os.path.splitext(fileB)[0]):
                graphs[fileB].append(fileA)
                in_degree[fileA] += 1

    return files, graphs, in_degree 

def topological_sort(files, graphs, in_degree):
    sorted_files = []
    queue = deque([file for file in files if in_degree[file] == 0])
    remaining_files = set(files)

    while queue or remaining_files:
        if queue:
            file = queue.popleft()
            sorted_files.append(file)
            remaining_files.discard(file)

            for neighbor in graphs[file]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        else:
            file = min(remaining_files, key=lambda f: in_degree[f])
            sorted_files.append(file)
            remaining_files.discard(file)

            for neighbor in graphs[file]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

    return sorted_files

def analyze_project(directory_metadata):
    files, graphs, in_degree = parse_files(directory_metadata)
    sorted_files = topological_sort(files, graphs, in_degree)

    print(f"Analyzed repository: {directory_metadata['repo_name']}")
    print(f"Total Python files: {len(files)}")
    print("Sorted files (may contain approximations due to cycles):")
    for file in sorted_files:
        print(file)



for data in read('./test.jsonl'):
    analyze_project(data)