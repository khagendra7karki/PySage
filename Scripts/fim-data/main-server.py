from fastapi import FastAPI, Request
from pydantic import BaseModel
import requests
import time
import jedi

app = FastAPI()

INFILL_TAG_PREFIX = "<|fim_prefix|>"
INFILL_TAG_SUFFIX = "<|fim_suffix|>"

GENERATION_SERVER = "http://localhost:1122/generate"

class InfillRequest(BaseModel):
    input_prefix: str = ""
    input_suffix: str = ""
    input_extra: list = []
    prompt: str = ""
    n_indent: int = 0
    n_predict: int = 128
    top_k: int = 40
    top_p: float = 0.99
    t_max_predict_ms: int = 500


@app.post("/infill")
async def handle_infill(request: InfillRequest):
    prefix = request.input_prefix
    suffix = request.input_suffix
    prompt_hint = request.prompt
    n_indent = request.n_indent
    indent = " " * n_indent

    formatted_prompt = (
        INFILL_TAG_PREFIX + "\n" +
        indent + prefix.rstrip() + "\n" +
        INFILL_TAG_SUFFIX + "\n" +
        indent + suffix.lstrip() + "\n" +
        prompt_hint
    )

    t0 = time.time()
    prompt_length = len(formatted_prompt)
    t1 = time.time()
    prompt_ms = int((t1 - t0) * 1000)

    generation_payload = {
        "prompt": formatted_prompt,
        "n_predict": request.n_predict,
        "top_k": request.top_k,
        "top_p": request.top_p,
        "stream": False
    }

    print(request.n_predict)
    
    t2 = time.time()
    try:
        response = requests.post(
            GENERATION_SERVER,
            json=generation_payload,
            # timeout=request.t_max_predict_ms / 1000
        )
        response.raise_for_status()
        result = response.json()
        content = result.get("generated_text", "")
        print(content)
    except Exception as e:
        print("Exception occurred while generating", e)
        return {
            "content": None,
            "error": str(e),
            "generation_settings": generation_payload,
        }

    t3 = time.time()
    predict_ms = int((t3 - t2) * 1000)
    predicted_n = len(content.split())

    return {
        "content": content,
        "generation_settings": generation_payload,
        "tokens_cached": 0,
        "truncated": result.get("truncated", False),
        "timings": {
            "prompt_n": prompt_length,
            "prompt_ms": prompt_ms,
            "prompt_per_second": round(prompt_length / (prompt_ms / 1000 + 1e-6), 2),
            "predicted_n": predicted_n,
            "predicted_ms": predict_ms,
            "predicted_per_token_ms": predicted_n / predict_ms,
            "predicted_per_second": round(predicted_n / (predict_ms / 1000 + 1e-6), 2),
        }
    }


def extract_context(code, project_path, file_path, line, column):
    """
    Extract relevant definitions and context from a Python project.
    
    Args:
        project_path: Root path of the Python project
        file_path: Path to the file where you want context
        line: Line number in the file
        column: Column number in the file
    """
    # Create a Script object for the file
    script = jedi.Script(
        code,
        path=file_path,
        project=jedi.Project(project_path)
    )
    
    # Get completions at the given position
    completions = script.complete(line, column)
    print(f"\nCompletions at {file_path}:{line}:{column}:")
    for c in completions:
        print(f"- {c.name} (type: {c.type})")
    
    # Get all definitions in the file
    definitions = script.get_names()
    print("\nAll definitions in this file:")
    for d in definitions:
        if d.type in ('function', 'class'):
            print(f"- {d.name} (type: {d.type}, line: {d.line})")
    
    # Get goto definitions (what's defined at this position)
    definitions = script.goto(line, column)
    print("\nDefinitions at cursor position:")
    for d in definitions:
        print(f"- {d.name} (type: {d.type}, module: {d.module_name}, path: {d.module_path}, line: {d.line})")
    
    # Get references/usages
    usages = script.get_references(line, column)
    print("\nReferences/usages:")
    for u in usages:
        print(f"- {u.name} in {u.module_path} at line {u.line}")




