from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer, StoppingCriteria
import os
import re
import ast
from context_server import generate_context

# from AutoCompletion import AutoCompletion
from threading import Thread

# Autocompletion class object to facilitate autocompletion
# a = AutoCompletion()

def generate_autocomplete_prompt(prefix, suffix, user_prompt, retrieved_nodes, file_path):
    """
    Generates an optimized prompt for code autocompletion.
    
    Args:
        prefix (str): Code preceding the cursor.
        suffix (str): Code following the cursor.
        user_prompt (str): User requirement for the completion.
        retrieved_nodes (list): Context of file dependencies in the repository.
        file_path (str): Path of the file where completion is required.

    Returns:
        str: Optimized prompt for the model.
    """
    prefix_tok = "<|fim_prefix|>"
    suffix_tok = "<|fim_suffix|>"
    middle_tok = "<|fim_middle|>"
    # Construct the enriched prompt with relevant context
    # enriched_prompt = (
    #     f"{prefix_tok}{prefix}{suffix_tok}{suffix}{middle_tok}\n"
    #     f"### File Path: {file_path}\n"
    #     f"### User Requirement: {user_prompt}\n"
    #     f"### Repository Context:\n"
    #     f"Retrieved Nodes: {', '.join(retrieved_nodes)}\n"
    #     f"### Task:\n"
    #     f"Complete the given code snippet while ensuring code correctness, readability, and best practices."
    # )
    # enriched_prompt = (
    #     f"""<|im_start|>system
    # You are an intelligent programming assistant. Complete the given code snippet while ensuring code correctness, readability, and best practices.<|im_end|>
    # <|im_start|>user
    # Can you complete the following Python function.
    # ```python
    # {prefix_tok}{prefix}{middle_tok}{suffix}{suffix_tok}"""
    # )
    # enriched_prompt = (
    # f"""<|im_start|>system
    # You are an intelligent programming assistant. Complete the given code snippet while ensuring code correctness, readability, and best practices. Additionally, take into account the existing configuration settings and class dependencies provided below:
    # Context and Dependencies: 
    # {', '.join(retrieved_nodes)}
    
    # <|im_end|>
    # <|im_start|>user
    # Can you complete the following Python function?
    # ```python
    # {prefix_tok}{prefix}{suffix}{suffix_tok}{middle_tok}"""
    # )
    enriched_prompt = (
    f"""<|im_start|>system
You are an intelligent programming assistant. Complete the given code snippet while ensuring code correctness, readability, and best practices. Additionally, take into account the existing configuration settings and class dependencies provided below:
Context and Dependencies: 
{', '.join(retrieved_nodes)}

<|im_end|>
<|im_start|>user
Can you complete the following Python function?
```python
{prefix_tok}{prefix}{suffix_tok}{suffix}{middle_tok}"""
    )
    return enriched_prompt



# Download and save the model locally
def download_and_save_model(model_name, gguf_file, local_dir):
    if not os.path.exists(local_dir):
        print(f"Downloading and saving {model_name} to {local_dir}...")
        tokenizer = AutoTokenizer.from_pretrained(model_name, gguf_file=gguf_file)
        tokenizer.save_pretrained(local_dir)


        model = AutoModelForCausalLM.from_pretrained(model_name, gguf_file=gguf_file)
        model.save_pretrained(local_dir)
        print("Download complete.")
    else:
        print(f"Model already downloaded in {local_dir}")

# Model details
model_id = "Qwen/Qwen2.5-Coder-0.5B-Instruct-GGUF"
gguf_file = "qwen2.5-coder-0.5b-instruct-q4_k_m.gguf"
local_dir = "./models/PySage-finetuned-Coder-0.5B-Instruct-GGUF"

# Download the model if not already present
download_and_save_model(model_id, gguf_file, local_dir)
# Load the model and tokenizer
tokenizer = AutoTokenizer.from_pretrained(local_dir)
model = AutoModelForCausalLM.from_pretrained(local_dir)

# Explicitly register FIM tokens as special tokens
tokenizer.add_special_tokens({
    "additional_special_tokens": ["<|fim_prefix|>", "<|fim_middle|>", "<|fim_suffix|>"]
})

class EosStoppingCriteria(StoppingCriteria):
    def __init__(self, eos_token_id):
        self.eos_token_id=eos_token_id
    def __call__(self, input_ids, scores, **kwargs):
        return input_ids[0][-1] == self.eos_token_id

stopping_criteria = EosStoppingCriteria(tokenizer.eos_token_id)
# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS
socketio = SocketIO(app, cors_allowed_origins="*")  # Enable WebSocket



def extract_code(text):
    """
    Extracts only valid Python code from the generated text, excluding comments and non-code text.
    
    Args:
        text (str): The raw model output.
    
    Returns:
        str: The cleaned code without comments or non-code text.
    """
    code_lines = text.split("\n")
    filtered_lines = []

    # Regex pattern to match only valid Python code
    code_pattern = re.compile(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*\s*[=()]?[a-zA-Z0-9_.,\[\]{}+=/*%-]*)")

    for line in code_lines:
        stripped_line = line.strip()
        if not stripped_line:
            continue  # Ignore empty lines

        # Skip comment lines (Python style)
        if stripped_line.startswith("#"):
            continue

        # Only keep lines that look like valid Python code
        if code_pattern.match(stripped_line):
            filtered_lines.append(line)

    return "\n".join(filtered_lines)

def extract_code_only(text):
    """
    Extracts only valid Python code from the generated text, excluding comments and non-code text.
    
    Args:
        text (str): The raw model output.
    
    Returns:
        str: The cleaned code without comments or non-code text.
    """
    # Regex pattern to match Python code blocks (between ```python and ```)
    code_block_pattern = re.compile(r"```python(.*?)```", re.DOTALL)
    code_blocks = code_block_pattern.findall(text)

    if code_blocks:
        # Join all code blocks into a single string
        code = "\n".join(code_blocks).strip()
        return code
    else:
        # If no code blocks are found, return an empty string
        return ""
    
    
@socketio.on('autoCompletion')
def handle_auto_completion(data):
    """
    Handles auto-completion requests, ensuring that only valid code and comments are returned.
    """
    print(data, "data from vscode")
    try:
        prefix = data.get("prefix", "")
        suffix = data.get("suffix", "")
        file_path = data.get("filePath", "")
        project_path = data.get("repositoryPath", "")
        user_prompt = data.get("prompt", "")
        max_length = data.get("max_length", 512)
        temperature = max(0.1, min(data.get("temperature", 1.0), 2.0))
        top_k = data.get("top_k", 50)
        top_p = data.get("top_p", 0.95)
        
        output_folder = "/home/shangkat5/Desktop/Major_Project/PySage/Server/cocomic/CONTEXTS/test"
        groundtruth = ""
        result = generate_context(project_path, output_folder, file_path, user_prompt, groundtruth)
        # result={}
        if isinstance(result, list) and len(result) > 0:
            result = result[0]  # Extract the first dictionary
            retrieved_edges = result["retrieved_edges"]
            retrieved_nodes = result["retrieved_nodes"]
        else:
            retrieved_nodes = ""

        enriched_prompt = generate_autocomplete_prompt(prefix, suffix, user_prompt, retrieved_nodes, file_path)

        print(enriched_prompt, "prompt to the model")
        inputs = tokenizer(
            enriched_prompt,
            max_length=512,
            truncation=True,
            return_tensors="pt"
        )

        streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, decode_kwargs={'skip_special_tokens': True})
        arg_dicts = dict(inputs,
                          streamer=streamer,
                          max_new_tokens=128,
                          stopping_criteria=[stopping_criteria],
                          do_sample=True,
                          pad_token_id=tokenizer.eos_token_id,
                          top_p=top_p,
                          top_k=top_k,
                          )

    #     thread = Thread(target=model.generate, kwargs=arg_dicts)
    #     thread.start()

    #     chunk_to_send = []
    #     for new_tok in streamer:
    #         chunk_to_send.append(new_tok)

    #         if len(chunk_to_send) >= 5:
    #             processed_chunk = extract_code("".join(chunk_to_send))
    #             if processed_chunk:
    #                 emit("response", {"response": processed_chunk, "type": "chunk"})
    #                 print(processed_chunk)
    #             chunk_to_send = []

    #     if len(chunk_to_send) > 0:
    #         processed_chunk = extract_code("".join(chunk_to_send))
    #         if processed_chunk:
    #             emit("response", {"response": processed_chunk, "type": "done"})
    #         chunk_to_send = []
        
    #     # processed_chunk = extract_code("".join(chunk_to_send))
    #     # print("eeeeeeeeeeeee",processed_chunk, "processsseddd")
    #     thread.join()

    # except Exception as e:
    #     print("An exception occurred ", e)
    #     emit('error', {"error": str(e)})

        thread = Thread(target=model.generate, kwargs=arg_dicts)
        thread.start()
        chunk_to_send = []
        for new_tok in streamer:
            chunk_to_send.append(new_tok)
            if len(chunk_to_send) >= 5:
                emit("response", {"response": "".join(chunk_to_send), "type": "chunk"})
                print("".join(chunk_to_send))
                chunk_to_send = []
        
        if len(chunk_to_send) > 0:
            emit("response", {"response": "".join(chunk_to_send), "type": "done"})
            chunk_to_send = []
        
        thread.join()

    except Exception as e:
        print("An exception occurred ", e)
        emit('error', {"error": str(e)})


@socketio.on("message")
def handle_message(data):
    try:
        print("Received WebSocket message:", data)
        input_text = data.get("input", "")
        max_length = data.get("max_length", 512)
        temperature = max(0.1, min(data.get("temperature", 1.0), 2.0))
        top_k = data.get("top_k", 50)
        top_p = data.get("top_p", 0.95)

        # Tokenize input
        inputs = tokenizer(
            input_text,
            max_length=512,
            truncation=True,
            return_tensors="pt"
        )

        # Stream the response
        streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, decode_kwargs={'skip_special_tokens': True})
        arg_dicts = dict(
            inputs,
            streamer=streamer,
            max_new_tokens=100,  # Adjust for better response control
            stopping_criteria=[stopping_criteria],
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
            top_p=top_p,
            top_k=top_k,
        )

        thread = Thread(target=model.generate, kwargs=arg_dicts)
        thread.start()

        chunk_to_send = []
        for new_tok in streamer:
            chunk_to_send.append(new_tok)
            if len(chunk_to_send) >= 5:
                emit("response", {"response": "".join(chunk_to_send), "type": "chunk"})
                print("Chunk sent:", "".join(chunk_to_send))
                chunk_to_send = []
        
        # Send final remaining tokens
        if len(chunk_to_send) > 0:
            emit("response", {"response": "".join(chunk_to_send), "type": "done"})
            print("Final chunk sent:", "".join(chunk_to_send))

        thread.join()

    except Exception as e:
        print("An exception occurred:", e)
        emit("error", {"error": str(e)})

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
