import os
import requests

def download_github_folder(repo_url, folder_name, destination_path):
    """
    Downloads a specified folder from a github repository to a local directory
    Args:
        repo_url
        folder_name
        destination_path
    """


    api_url = f"http://api.github.com/repos/{repo_url.split('/')[-2]}/{repo_url.split('/')[-1]}/contents/{folder_name}"


    response = requests.get(api_url, headers={"Accept": "application/vnd.github.raw+json", "Authorization":"Bearer <github_access_token"})

    if response.status_code == 200:
        data = response.json()


        os.makedirs(os.path.join(destination_path, folder_name), exist_ok=True)

        for item in data:
            if item['type'] == 'file':
                file_url = item['download_url']
                file_name = item["name"]
                file_path = os.path.join(destination_path, folder_name, file_name)

                # Download file
                file_response = requests.get(file_url)
                with open(file_path, "wb") as f:
                    f.write(file_response.content)
    
    else:
        print(f"Error downloading folder: {response.status_code}")



repo_url="https://github.com/unclecode/crawl4ai"
folder_to_download="crawl4ai"

local_path='./'
download_github_folder(repo_url, folder_to_download, local_path)