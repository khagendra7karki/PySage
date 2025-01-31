import jedi
import sys

# Add your project root to sys.path
# sys.path.append("/path/to/your/python/repo")

# Initialize Jedi Project
project = jedi.Project("./")

def get_context_aware_completions(code, line, column, path):
    # Create a Script with the Project reference
    script = jedi.Script(
        code=code,
        path=path,
        project=project
    )
    
    # Get context at cursor position
    context = script.get_context(line, column)
    
    # Get completions (with full project awareness)
    completions = script.complete(line, column)
    
    return {
        "context": context.description,
        "completions": [c.name for c in completions]
    }

code = """from random_class import Something

s = Something(10, 5)
print(s."""

result = get_context_aware_completions(
    code=code,
    line=4,  # Line number of the cursor (0-indexed)
    column=8,  # Column after "my_project.utils."
    path=""
)

print("Context:", result["context"])
print("Completions:", result["completions"])