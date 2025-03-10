from huggingface_hub import snapshot_download
snapshot_download(repo_id='cerebras/SlimPajama-627B',
                  repo_type='dataset',
                  allow_patterns=['test/*', 'validation/*', 'train/chunk1/1*', 'train/chunk1/2*'],
                  cache_dir='./'
                  )