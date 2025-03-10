import os
import json
from ccfinder_utils import generate_cross_file_context

def generate_context(project_path, output_folder, file_path, prompt, groundtruth):
    try:
        # Ensure the output folder exists
        os.makedirs(output_folder, exist_ok=True)
        print("here1")
        # Extracting repository name from the project_path
        repo_name = os.path.basename(project_path.rstrip("/"))
        # print(repo_name)
        # Run CoCoMIC context retrieval
        # os.system(f"export PYTHONPATH=$(pwd); python build_crossfile_context.py --input_project {project_path} --output_dir {output_folder}")

        command = f"export PYTHONPATH=$(pwd); python build_crossfile_context.py --input_project {project_path} --output_dir {output_folder} || true"
        os.system(command)
        print("here2")

        retrieved_entity_file = os.path.join(output_folder, f"{repo_name}_retrieved_nodes.json")
        output_file = os.path.join(output_folder, f"{repo_name}_output.jsonl")
        
        # Prepare the prompt data
        prompts = [
            {
                "prompt": prompt,
                "groundtruth": groundtruth,
                "metadata": {"file": file_path}
            }
        ]
        
        # Use the prompts directly and generate output using the cross-file context
        generated_output = generate_cross_file_context(retrieved_entity_file, prompts, output_file)
        print(generated_output,"generated output")
        return generated_output  # Return the generated output

    except Exception as e:
        return {"error": str(e)}