from huggingface_hub import snapshot_download

# download the repo
snapshot_download(repo_id='hoskinson-center/proof-pile',
                  repo_type='dataset',
                  allow_patterns=['dev/*', 'test/*', 'train/*'],
                  ignore_patterns=['.gitattributes'],
                  cache_dir='./'
                  )