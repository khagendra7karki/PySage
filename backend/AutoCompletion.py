import jedi
import sys


class AutoCompletion():
    def __init__(self):
        pass

    def initialize_repo(self, project_path):
        self.project_path = project_path
        self.project = jedi.Project(self.project_path)



    def _get_context(self, code, line, column, path):
        # Create a Script with the Project reference
        script = jedi.Script(
            code=code,
            path=path,
            # project=self.project
        )
        
        # Get context at cursor position
        context = script.get_context(line, column)
        
        # Get completions (with full project awareness)
        completions = script.complete(line, column)
        
        return {
            "context": context.description,
            "completions": [c.name for c in completions]
        }
    

    def _segregate(self, generated_output):
        prefix = generated_output.split("<|fim_suffix|>")[0]
        prefix = prefix.replace("<|fim_prefix|>", "")
        middle = generated_output.split("<|fim_middle|>")[-1]
        middle = middle.replace("<|fim_middle|>", "")
        suffix = generated_output.split("<|fim_suffix|>")[-1].split("<fim_middle>")[0]
        suffix = suffix.replace("<|fim_suffix|>", "")
        
        return prefix, middle, suffix

    
    # def _get_reference(self, code):
    #     script = jedi.Script(
    #         code=code,
    #         path=path,
    #         project=self.project
    #     )



        
        

