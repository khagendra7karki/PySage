import os
import requests
import dotenv

dotenv.load_dotenv()

def download_github_folder(repo_url, folder_path, destination_path, recursive=True):
    """
    Downloads a specified folder from a GitHub repository to a local directory recursively.
    
    Args:
        repo_url (str): URL of the GitHub repository
        folder_path (str): Path to the folder in the repository
        destination_path (str): Local path where the folder should be downloaded
        recursive (bool): Whether to download subfolders recursively (default: True)
    """
    # Extract owner and repo name from URL
    parts = repo_url.rstrip('/').split('/')
    owner = parts[-2]
    repo = parts[-1]
    
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{folder_path}"
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {os.getenv('GITHUB_ACCESS_TOKEN')}" if os.getenv("GITHUB_ACCESS_TOKEN") else None
    }
    headers = {k: v for k, v in headers.items() if v is not None}
    
    response = requests.get(api_url, headers=headers)
    
    if response.status_code == 200:
        items = response.json()
        
        # Create the local directory if it doesn't exist
        local_folder_path = os.path.join(destination_path, folder_path)
        os.makedirs(local_folder_path, exist_ok=True)
        
        for item in items:
            if item['type'] == 'file':
                # Download file
                file_url = item['download_url']
                file_name = item['name']
                file_path = os.path.join(local_folder_path, file_name)
                
                file_response = requests.get(file_url)
                if file_response.status_code == 200:
                    with open(file_path, 'wb') as f:
                        f.write(file_response.content)
                    print(f"Downloaded: {file_path}")
                else:
                    print(f"Failed to download {file_name}: {file_response.status_code}")
            
            elif item['type'] == 'dir' and recursive:
                # Recursively download subfolder
                subfolder_path = os.path.join(folder_path, item['name'])
                download_github_folder(repo_url, subfolder_path, destination_path, recursive)
    
    else:
        print(f"Error accessing folder {folder_path}: {response.status_code} - {response.text}")

# Example usage
repo_url = "https://github.com/khagendra7karki/PySage"
folders_to_download = ["Server/python-repo"]  # Can be multiple folders
local_path = '.'

for folder in folders_to_download:
    download_github_folder(repo_url, folder, local_path)