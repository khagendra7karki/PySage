from flask import Flask, request, jsonify
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from datetime import datetime
def decorator_print(func):
    def wrapper_func():
        print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
        func()
        print("###################################")

    return wrapper_func()

app = Flask(__name__)

# Load a pre-trained language model and tokenizer
MODEL_NAME = "Qwen/Qwen2.5-Coder-0.5B"  # Replace with your model name
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)

# Ensure the model is in evaluation mode
model.eval()

def format_infill_prompt(prefix, suffix, extra_context=None):
    """
    Formats the input for infill tasks by combining prefix, suffix, and extra context.
    """
    prompt = prefix
    if extra_context:
        for chunk in extra_context:
            prompt += chunk.get("text", "")
    prompt += suffix
    return prompt

def generate_infill(prefix, suffix, extra_context=None, max_length=100):
    """
    Generates infill text using the language model.
    """
    # Format the prompt
    prompt = format_infill_prompt(prefix, suffix, extra_context)

    # Tokenize the input
    inputs = tokenizer(prompt, return_tensors="pt")

    # Generate infill text
    with torch.no_grad():
        outputs = model.generate(
            inputs.input_ids,
            pad_token_id=tokenizer.eos_token_id,
            max_new_tokens=max_length,
            num_return_sequences=1,
        )

    outputs = outputs[0, inputs.input_ids.shape[-1]: ]

    # Decode the generated text
    generated_text = tokenizer.decode(outputs, skip_special_tokens=True)
    return generated_text

@app.route("/infill", methods=["POST"])
def handle_infill():
    """
    Handles infill requests.
    """
    data = request.json
    print(data)
    # Validate input
    if not data or "input_prefix" not in data or "input_suffix" not in data:
        return jsonify({"error": "input_prefix and input_suffix are required"}), 400

    prefix = data.get("input_prefix", "")
    suffix = data.get("input_suffix", "")
    extra_context = data.get("input_extra", [])
    prompt = data.get("prompt", "")
    n_predict = data.get("n_predict", 100)  # Default to 100 tokens if not provided
    cache_prompt = data.get("cache_prompt", True)

    # Validate extra_context
    if extra_context and not isinstance(extra_context, list):
        return jsonify({"error": "input_extra must be a list of objects with 'text' field"}), 400

    # Generate infill text
    try:
        infill_text = generate_infill(prefix, suffix, extra_context, max_length=n_predict)

        # Prepare the response in LlamaResponse format
        response = {
            "content": infill_text,
            "generation_settings": {
                "model": MODEL_NAME,
                "created": datetime.now().timestamp(),
            },
            "tokens_cached": len(tokenizer.encode(prefix + suffix)),  # Example value
            "truncated": False,  # Example value
            "timings": {
                "prompt_n": len(tokenizer.encode(prefix + suffix)),  # Example value
                "prompt_ms": 100,  # Example value
                "prompt_per_second": 50,  # Example value
                "predicted_n": len(tokenizer.encode(infill_text)),  # Example value
                "predicted_ms": 200,  # Example value
                "predicted_per_second": 25,  # Example value
            },
        }

        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Run the server
    app.run(host="0.0.0.0", port=8012)