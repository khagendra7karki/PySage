from dataset_prep import tokenize_file, load_data
import os
import transformers

tokenizer = transformers.AutoTokenizer.from_pretrained("Qwen/Qwen2.5-Coder-0.5B-Instruct")
if __name__ == "__main__":
    code_path = './python-dataset/cleaned_scraped_python_code'
    out_dir = './python-dataset/tokenized_scraped_python_code'
    files = os.listdir(code_path)
    file =[os.path.join(code_path, file) for i, file in enumerate(files)][0]
    data_loader = load_data(file)

    test_file = open("test.py","w")
    max_test = 10
    n_test = 0
    end = False
    for chunk in data_loader:
        if end:
            break
        for repo in chunk:
            if end:
                break
            for file in repo['files']:
                if len(file['content']) > 8192:
                    n_test += 1
                    print("i am here")
                    tokenized = tokenize_file(file['content'])
                    test_file.truncate()
                    print("New File")
                    for item in tokenized:
                    
                        print("#" * 10 , "chunk ", "#" * 10, file=test_file)
                        print(tokenizer.decode(item["tokens"]), file=test_file)
                        print(item["num_tokens"])
                    if n_test == max_test: 
                        end = True
                    break
    test_file.close()

