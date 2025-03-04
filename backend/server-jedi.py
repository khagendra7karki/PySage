from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer, StoppingCriteria
import os
from AutoCompletion import AutoCompletion
from threading import Thread
import jedi

# Autocompletion class object to facilitate autocompletion
a = AutoCompletion()

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
local_dir = "./models/Qwen2.5-Coder-0.5B-Instruct-GGUF"

# Download the model if not already present
download_and_save_model(model_id, gguf_file, local_dir)

# Load the model and tokenizer
tokenizer = AutoTokenizer.from_pretrained(local_dir)
model = AutoModelForCausalLM.from_pretrained(local_dir)

# Register special tokens explicitly
tokenizer.add_special_tokens({
    "additional_special_tokens": ["<|fim_prefix|>", "<|fim_middle|>", "<|fim_suffix|>"]
})

class EosStoppingCriteria(StoppingCriteria):
    def __init__(self, eos_token_id):
        self.eos_token_id = eos_token_id

    def __call__(self, input_ids, scores, **kwargs):
        return input_ids[0][-1] == self.eos_token_id

stopping_criteria = EosStoppingCriteria(tokenizer.eos_token_id)

# Initialize Flask app
app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.json
        if not data or "input" not in data:
            return jsonify({"error": "Invalid input. 'input' field is required."}), 400

        input_text = data["input"]

        # Simple mock response for testing
        return jsonify({"completions": [f"Suggested completion for: {input_text}"]})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@socketio.on('autoCompletion')
def handle_auto_completion(data):
    try:
        prefix = data.get("prefix", "")
        suffix = data.get("suffix", "")
        max_length = data.get("max_length", 512)
        temperature = max(0.1, min(data.get("temperature", 1.0), 2.0))
        top_k = data.get("top_k", 50)
        top_p = data.get("top_p", 0.95)

        script = jedi.Script(code=prefix + suffix)
        print(script,"here2 check")

        completions = [comp.name for comp in script.complete()]

        prompt = f"<|fim_prefix|>{prefix}<|fim_suffix|>{suffix}<|fim_middle|>"
        inputs = tokenizer(prompt, max_length=512, truncation=True, return_tensors="pt")
        streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, decode_kwargs={'skip_special_tokens': True})

        arg_dicts = dict(
            inputs,
            streamer=streamer,
            max_new_tokens=30,
            stopping_criteria=[stopping_criteria],
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
            top_p=top_p,
            top_k=top_k
        )

        thread = Thread(target=model.generate, kwargs=arg_dicts)
        thread.start()

        chunk_to_send = []
        for new_tok in streamer:
            chunk_to_send.append(new_tok)
            if len(chunk_to_send) >= 5:
                emit("response", {"response": "".join(chunk_to_send), "type": "chunk"})
                chunk_to_send = []

        if len(chunk_to_send) > 0:
            emit("response", {"response": "".join(chunk_to_send), "type": "done"})
        thread.join()

    except Exception as e:
        emit('error', {"error": str(e)})

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
