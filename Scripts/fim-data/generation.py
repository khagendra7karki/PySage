# Import model from hugging face and respond to generation request only via REST API
from fastapi import FastAPI, Request
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import uvicorn
import time 

# Initialize app
app = FastAPI()

# Load model and tokenizer
model_name = "../../models/PySage"  # Replace with your desired model from Hugging Face
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)
# Move to GPU if available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

model.to(device)
model = torch.compile(model)

# Request body schema
class GenerateRequest(BaseModel):
    prompt: str
    temperature: float = 1.0
    top_k: int = 50
    top_p: float = 1.0
    n_predict: int = 128

# Endpoint to handle generation
@app.post("/generate")
async def generate_text(request: GenerateRequest):
    from llama_cpp import Llama

    llm = Llama(
        model_path="/home/alpha/training-ground/llama.cpp/PySage.gguf",
        n_gpu_layers=-1, # Uncomment to use GPU acceleration
        # seed=1337, # Uncomment to set a specific seed
        # n_ctx=2048, # Uncomment to increase the context window
    )
    output = llm(
        "Q: Name the planets in the solar system? A: ", # Prompt
        max_tokens=100, # Generate up to 32 tokens, set to None to generate up to the end of the context window
        stop=["Q:", "\n"], # Stop generating just before the model would generate a new question
        echo=True # Echo the prompt back in the output
    ) # Generate a completion, can also call create_completion
    print(output)
    input_ids = tokenizer(request.prompt, return_tensors="pt").to(device)
    initial_length = input_ids.input_ids.shape[-1]

    if request.n_predict == 0:
        return {"genrated_text": ""}
    now  = time.time()
    output = model.generate(
        **input_ids,
        max_new_tokens=request.n_predict,
        temperature=request.temperature,
        top_k=request.top_k,
        top_p=request.top_p,
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id
    )
    time_taken  =time.time()
    print("Generation time: ", time_taken - now )
    generated_text = output[0][initial_length:]
    generated_text = tokenizer.decode(generated_text, skip_special_tokens=True)
    # print(generated_text)

    return {"generated_text": generated_text}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=1122)