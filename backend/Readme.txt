Steps to Generate requirements.txt Automatically
If you already have your Python environment set up and want to export all installed dependencies, run:

# pip freeze > requirements.txt
This will save all currently installed packages into requirements.txt.

Installing Dependencies from requirements.txt
To install dependencies from requirements.txt, use:

# pip install -r requirements.txt