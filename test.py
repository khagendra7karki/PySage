import json
import os
import glob
import random
from typing import List, Iterator

def stream_tokens(data_dir: str, chunk_size: int = 1024) -> Iterator[List[int]]:
    """
    Stream tokens from files with minimal memory usage.
    
    Args:
        data_dir (str): Directory containing JSONL files
        chunk_size (int): Size of each token chunk
    
    Yields:
        List[int]: Chunks of tokens
    """
    files = sorted(glob.glob(os.path.join(data_dir, "*.jsonl")))
    buffer = []
    
    for file_path in files:
        try:
            print(f"Processing file: {file_path}")
            file_chunks_count = 0
            
            with open(file_path, 'r') as f:
                for line in f:
                    try:
                        example = json.loads(line)
                        tokens = example.get('tokens', [])
                        
                        # Accumulate tokens
                        buffer.extend(tokens)
                        
                        # Yield full chunks
                        while len(buffer) >= chunk_size:
                            yield buffer[:chunk_size]
                            buffer = buffer[chunk_size:]
                            file_chunks_count += 1
                    
                    except json.JSONDecodeError:
                        print(f"Skipping invalid JSON in {file_path}")
            
            # Handle remaining tokens
            
            print(f"Processed file {file_path}: {file_chunks_count} chunks")
        
        except IOError as e:
            print(f"Error reading file {file_path}: {e}")
        # if buffer:
        #     yield buffer
        #     buffer = []

def stratified_split_write(
    data_dir: str, 
    train_path: str, 
    val_path: str, 
    val_ratio: float = 0.05,
    chunk_size: int = 1024
) -> None:
    """
    Split and write tokens using minimal memory.
    
    Args:
        data_dir (str): Directory containing input JSONL files
        train_path (str): Path to save training data
        val_path (str): Path to save validation data
        val_ratio (float): Ratio of validation data
        chunk_size (int): Size of each token chunk
    """
    # Open output files
    with open(train_path, 'w') as train_file, open(val_path, 'w') as val_file:
        for tokens in stream_tokens(data_dir, chunk_size):
            # Probabilistic split
            if random.random() < val_ratio:
                val_file.write(json.dumps({
                    "tokens": tokens, 
                    "num_tokens": len(tokens)
                }) + '\n')
            else:
                train_file.write(json.dumps({
                    "tokens": tokens, 
                    "num_tokens": len(tokens)
                }) + '\n')
    
    # Verify output file sizes
    train_size = os.path.getsize(train_path) / (1024 * 1024)
    val_size = os.path.getsize(val_path) / (1024 * 1024)
    
    print(f"Training data saved: {train_size:.2f} MB")
    print(f"Validation data saved: {val_size:.2f} MB")

def main():
    data_dir = "python-dataset/tokenized_scraped_python_code"
    train_path = "train_data.jsonl"
    val_path = "val_data.jsonl"
    
    stratified_split_write(
        data_dir, 
        train_path, 
        val_path,
        val_ratio=0.1,
        chunk_size=1024
    )
    # max = 10
    # i = 0
    # with open(train_path, 'r') as f:
    #     for l in f:
    #         x = json.loads(l)
    #         if len(x["tokens"]) != 1024:
    #             print("Not 1024")


if __name__ == "__main__":
    main()

'''
import json
import torch
import matplotlib.pyplot as plt
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments

def load_training_data(data_path):
    dataset = load_dataset("json", data_files=data_path, split="train")
    return dataset

def tokenize_function(example, tokenizer):
    task = example["task"]

    if task == "fim":
        inputs = tokenizer(
            example["prefix"] + tokenizer.sep_token + example["suffix"],
            padding=True,
            truncation=True,
            max_length=1024,  # Adjust as needed
            return_tensors="pt"
        )
    else:
        inputs = tokenizer(
            example["prefix"],
            padding=True,
            truncation=True,
            max_length=1024,
            return_tensors="pt"
        )
    # Shift labels by 1 for causal LM loss
    inputs["labels"] = inputs["input_ids"].clone() # No shifting of labels
    return {k: v.squeeze(0) for k, v in inputs.items()}


def plot_loss_curve(log_file, output_path):
    losses = []
    steps = []

    with open(log_file, "r") as f:
        for line in f:
            log = json.loads(line)
            if "loss" in log:
                losses.append(log["loss"])
                steps.append(log["step"])

    plt.figure(figsize=(10, 6))
    plt.plot(steps, losses, label="Training Loss")
    plt.xlabel("Steps")
    plt.ylabel("Loss")
    plt.title("Training Loss Curve")
    plt.legend()
    plt.savefig(output_path)
    plt.show()
from tensorboard.backend.event_processing import event_accumulator

def plot_loss_from_tensorboard(event_file, output_path):
    ea = event_accumulator.EventAccumulator(event_file)
    ea.Reload()

    # Get the loss values and steps
    if 'loss' in ea.scalars.Keys():
        loss_events = ea.scalars.Items('loss')
        steps = [event.step for event in loss_events]
        losses = [event.value for event in loss_events]

        plt.figure(figsize=(10, 6))
        plt.plot(steps, losses, label="Training Loss")
        plt.xlabel("Steps")
        plt.ylabel("Loss")
        plt.title("Training Loss Curve")
        plt.legend()
        plt.savefig(output_path)
        plt.show()
        print(f"Loss curve saved to {output_path}")
    else:
        print("No 'loss' metric found in TensorBoard logs")
def train_model(dataset_path, model_name, output_dir, batch_size=8, epochs=3, lr=8e-5):
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)

    dataset = load_training_data(dataset_path)
    tokenized_dataset = dataset.map(lambda x: tokenize_function(x, tokenizer), batched=True)

    training_args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        gradient_accumulation_steps=1,
        fp16=True,
        num_train_epochs=epochs,
        learning_rate=lr,
        weight_decay=0.01,
        save_total_limit=1,
        save_strategy="epoch",
        logging_dir="./logs",
        logging_steps=100,
        logging_strategy="steps",
        logging_first_step=True,
        report_to=["tensorboard"],
        push_to_hub=False,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
        tokenizer=tokenizer,
    )

    try:
        trainer.train()
    except torch.cuda.OutOfMemoryError:
        torch.cuda.empty_cache()
        print("CUDA out of memory! Cleared cache. Try reducing batch size or sequence length.")

    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"Model saved to {output_dir}")

    # plot_loss_curve("./logs/trainer_log.jsonl", f"{output_dir}/loss_curve.png")

if __name__ == "__main__":
    dataset_path = "formatted_training_data.jsonl"
    model_name = "Qwen/Qwen2.5-Coder-0.5B-Instruct"


    train_model(dataset_path, model_name, output_dir)

'''