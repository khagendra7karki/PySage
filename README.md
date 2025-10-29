# PySage - Python Coding Assistant

PySage is a final-year project that explored **building and fine-tuning a code language model** specialized for Python.
The repository is left mostly in its experimental state — messy, unoptimized, but real.
It documents our process of **training, fine-tuning, and deploying** a small open-source model for local code understanding and generation.

---

## 🧩 Project Overview

Our original goal was to **train our own code model from scratch** — similar to a lightweight version of Code Llama — and then adapt it for Python-specific tasks.

We experimented with dataset preparation, tokenizer adjustments, vocabulary pruning, and local inference optimization.

---

## 🧪 Phase 1 — Building Our Own Model

We began by creating a **~200M parameter decoder-only model** based on the LLaMA architecture.

* **Dataset:** We downloaded and prepared *The Stack* dataset for pretraining.
* **Challenge:** The data preprocessing alone took days. Any change in preprocessing or tokenization would invalidate progress, forcing full restarts.
* **Takeaway:** Training from scratch quickly proved computationally infeasible for our available resources.

---

## 🔧 Phase 2 — Fine-Tuning Existing Models

We shifted focus to fine-tuning smaller, pre-trained models.

After testing a few candidates, we selected **Qwen 2.5 (0.5B)** — a multilingual model known for good efficiency and adaptability.

### Key Experiments:

* **Vocabulary Pruning:**
  Since Qwen was multilingual, we pruned its vocabulary to retain mostly Python-relevant tokens.
  This reduced:

  * Model size by ~20%
  * Latency by ~1–2%
* **Fine-Tuning Dataset:**

  * Collected fresh Python code from GitHub repositories.
  * Preprocessed and normalized code (removed comments, unified indentation, etc.).
  * Fine-tuned over multiple epochs.
* **Final Stage:**

  * Focused fine-tuning on **high-quality, human-reviewed Python code** to improve syntax consistency and logical coherence.

---

## ⚙️ Phase 3 — Inference & Deployment

We built:

* A **local C-based inference server** for minimal latency.
* A **VS Code extension** to interface with the local model for inline code completion and generation.

---

## 📂 Repository Structure

> ⚠️ Note: The repo is research-grade, not production-grade. Expect messy directories, experimental notebooks, and mixed prototypes.

| Directory       | Purpose                                                           |
| --------------- | ----------------------------------------------------------------- |
| `/Scripts/model.py/`    | Model architecture experiment (initial LLaMA decoder prototype). |
| `/Scripts/tokenizer/`    | BPE based tokenizer implementation for the model  |
| `/Scripts/pipeline/`        | Data preprocessing and normalization pipelines.                   |
| `/Scripts/downsize/`        | Model Pruning Code along with tests.                   |
| `/Scripts/evaluation/`        | MBPP and HumanEval evaluaion code.                   |
| `/extension/`   | VS Code extension for local model integration.                    |
| `**remaining**` | Miscellaneous tests, ablations, and prototype scripts.            |

---

## 📊 Key Findings

* Training even a 200M model from scratch requires massive compute (storage + iteration cost).
* Fine-tuning and pruning offer *much higher ROI* than pretraining in small teams.
* Vocabulary pruning is an underexplored but *effective* optimization for domain-specific LLMs.
* Local inference is very feasible for sub-billion-parameter models.

---

## 🚧 Status

This project is **no longer under active development**, but the repository is kept public as an open record of the journey and insights.

Contributions or forks are welcome for anyone interested in small-scale LLM optimization, fine-tuning, or on-device inference.

---

## 📜 License

MIT License — open for research and educational use.

---
