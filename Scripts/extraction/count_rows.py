def count(file_path):
    i = 0
    with open(file_path, 'r') as f:
        for _ in f:
            i += 1

    return i

if __name__ == '__main__':
    code_path = './new-python-dataset/code.jsonl'
    id_path = './repo-id/ids.jsonl'
    path = id_path
    # path = code_path
    c = count(path)
    print(c)