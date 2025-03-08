from flask import Flask, request, jsonify
import os
import json
from ccfinder_utils import generate_cross_file_context

app = Flask(__name__)

def generate_context(project_path,output_folder,file_path,prompt,groundtruth):
    try:
        # Static project path, it can be dynamic if passed from the request
        project_path = "/home/shangkat5/Desktop/context/python-repo/"  # Path to the project
        output_folder = "/home/shangkat5/Desktop/context/cocomic/CONTEXTS/test"
        file_path = "/home/shangkat5/Desktop/context/python-repo/game.py"
        os.makedirs(output_folder, exist_ok=True)

        # Extracting repository name from the project_path
        repo_name = os.path.basename(project_path.rstrip("/"))
        
        # Run CoCoMIC context retrieval
        os.system(f"export PYTHONPATH=$(pwd); python build_crossfile_context.py --input_project {project_path} --output_dir {output_folder}")

        print(repo_name)
        retrieved_entity_file = os.path.join(output_folder, f"{repo_name}_retrieved_nodes.json")
        output_file = os.path.join(output_folder, f"{repo_name}_output.jsonl")
        
        # Prompt data can be passed directly instead of reading from a file
        prompts = [
            {
                "prompt": "...<IN-FILE CONTEXT>...",
                "groundtruth": "...",
                "metadata": {"file": file_path}
            }
        ]
        
        # Use the prompts directly and generate output using the cross-file context
        generated_output = generate_cross_file_context(retrieved_entity_file, prompts, output_file)
        
        return (generated_output)  # You can return the generated output as JSON here

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    # with app.app_context():  # Wrap the call in the application context
    print(generate_context())
    app.run(host="0.0.0.0", port=6000, debug=True)
