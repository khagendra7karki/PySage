import os
import json
import asyncio
import aiofiles
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from download import download_contents

async def save(output_file_path, backup_file_path, rows, current_idx, chunk_size, save_interval):
    async with aiofiles.open(output_file_path, 'a') as o, aiofiles.open(backup_file_path, 'r+') as b:
        
        str_progress = '{"idx": '+str(current_idx)+', "chunk_size": '+str(chunk_size)+', "save_interval": '+str(save_interval)+'}' 

        # write the output
        await o.writelines(rows)
        
        # save the current progress
        await b.seek(0)
        await b.write(str_progress)
        await b.truncate()
        await b.flush()
        print("File and progress saved")
        print("Current idx = ", current_idx)

# Generator to load the dataset in chunks
def load_dataset(file_path, previous_idx=0, chunk_size=1000):
    with open(file_path, 'r') as f:
        code = []

        for _ in range(previous_idx + 1):      # skip including previous_idx
            next(f, None)

        for line in f:
            json_code = json.loads(line)
            code.append(json_code)

            if len(code) == chunk_size:
                yield code
                code = []
        if code:
            yield code


# Function to process a single row
def process_row(i, row, supported_languages):
    try:

        allowed_fields = ['repo_name','files']
        row = {k: row[k] for k in row if k in allowed_fields}  # Filter allowed fields

        # Download file contents
        content = download_contents(row['files'], supported_languages)
        row['files'] = content['files']

        # print(i, row['repo_name'])
        return json.dumps(row) + '\n'
    
    except Exception as e:
        print(f'An error occurred, {str(e)} \nRepo Name: {row["repo_name"]}, id: {i}')
        return None


# Save progress periodically (with buffered approach)
def save_progress(backup_file, idx, chunk_size, save_interval):
    # Write progress periodically to the already opened backup file
    progress = {
        "idx": idx,
        "chunk_size": chunk_size,
        "save_interval": save_interval
    }
    backup_file.seek(0)  # Ensure writing from the beginning
    json.dump(progress, backup_file)
    backup_file.truncate()
    backup_file.flush()  # Force the write to disk

# Load progress from a backup file (handle case if file doesn't exist)
def load_progress(backup_file_path):
    if os.path.exists(backup_file_path):
        with open(backup_file_path, 'r') as f:
            try:
                data = json.load(f)
                return data
            except json.JSONDecodeError:
                # If the backup file is corrupted, return 0, 0 to start from the beginning
                return create_backup_file_if_not_exists(backup_file_path)
    # If no backup file exists, return initial values (start from the beginning)
    return create_backup_file_if_not_exists(backup_file_path)

# Create an empty backup file if it doesn't exist
def create_backup_file_if_not_exists(backup_file_path):
    if not os.path.exists(backup_file_path):
        initial_state={"idx": -1, "chunk_size": 1000, "save_interval": 100}
        # Create an empty backup file with initial progress
        with open(backup_file_path, 'w') as f:
            json.dump(initial_state, f)
            return initial_state



# Parallel processing function with buffered writing approach
async def process_dataset(dataloader, supported_languages, output_dir, backup_file_path, max_threads=5, chunk_size=1000, save_interval=1000):
    # Set the output file path
    output_file_path = os.path.join(output_dir, "code.jsonl")

    previous_state=load_progress(backup_file_path)
    previous_idx=previous_state["idx"]       # row index to start from
    print(f"Resuming from index {previous_idx}")
    generator=dataloader('repo-id/ids.jsonl',chunk_size=chunk_size, previous_idx=previous_idx)
    

    buffered_rows = []  # Buffer for efficient writing
    async with aiofiles.open(output_file_path, 'a') as o, aiofiles.open(backup_file_path, 'r+') as b:
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            loop=asyncio.get_event_loop()
            futures = []
            for chunk_index, chunk in enumerate(generator):            
                for row_index, row in enumerate(chunk):
                    n_rows =chunk_index * chunk_size + row_index

                    # Submit the processing task to the thread pool
                    future = loop.run_in_executor(executor,process_row, n_rows, row, supported_languages )
                    futures.append(future)

                    # Periodically save progress and write buffered rows to the output file
                    if (n_rows + 1) % save_interval==0:

                        results = await asyncio.gather(*futures)

                        buffered_rows.extend([result for result in results if result] )

                        futures.clear()

                        current_idx = previous_idx + n_rows + 1    # as n_rows is 1 less than the actual number
                        # Save the files
                        str_progress = '{"idx": '+str(current_idx)+', "chunk_size": '+str(chunk_size)+', "save_interval": '+str(save_interval)+'}' 

                        # write the output
                        await o.writelines(buffered_rows)
                        
                        # save the current progress
                        await b.seek(0)
                        await b.write(str_progress)
                        await b.truncate()
                        await b.flush()
                        buffered_rows.clear()
            
            results = await asyncio.gather(*futures)
            buffered_rows.extend(results)

            
            current_idx = previous_idx + n_rows    # no decrement as the row would have been increased
            
            str_progress = '{"idx": '+str(current_idx)+', "chunk_size": '+str(chunk_size)+', "save_interval": '+str(save_interval)+'}' 

            # write the output
            await o.writelines(buffered_rows)
            
            # save the current progress
            await b.seek(0)
            await b.write(str_progress)
            await b.truncate()
            await b.flush()
            buffered_rows.clear()

# Main script
if __name__ == "__main__":
    # Supported languages
    supported_languages = ['Python']

    # Set the output directory
    output_dir = "./python-dataset"

    # Backup file to save progress
    backup_file_path = os.path.join(output_dir, "backup.json")

    # Process the dataset in parallel from the last saved position
    asyncio.run(process_dataset(load_dataset, 
                    supported_languages, 
                    output_dir,
                    backup_file_path, 
                    max_threads=12, 
                    chunk_size=30000, 
                    save_interval=10000))
