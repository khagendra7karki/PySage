# PySage: Fine-Tuned Code Model for Python (Qwen2.5-Coder-0.5B)

> Some components described in our [project report](PySage_Report.pdf) **do not have working code in this repo**, either because they were built in isolated environments, lost during cleanup, or never fully committed.

But that’s okay. This is how real learning happens.

---

## Project Overview

Our original ambition was bold: **train a code language model from scratch**, akin to a tiny Code Llama, but optimized purely for Python.

We quickly realized that even a 200M-parameter model demanded more compute, storage, and iteration time than we could sustain. So we pivoted.

The final system uses **Qwen2.5-Coder-0.5B**, fine-tuned on fresh Python code, pruned for efficiency, and served via a **custom C++ backend** using `llama.cpp`, all wrapped in a **VS Code extension**.

The goal? **Context-aware, cross-file, Fill-in-the-Middle (FIM) completions**—running entirely offline on modest hardware.

---

## Phase 1 — The Dream: Training From Scratch

We started by implementing a **decoder-only transformer (~200M params)** inspired by LLaMA.

* **Dataset**: Processed *The Stack* (Python subset) — ~40 GB raw, ~20 GB cleaned.
* **Tokenization**: Built a custom BPE tokenizer.
* **Reality check**:

  * Preprocessing took **days**.
  * Any change (e.g., new normalization rule) meant **re-tokenizing everything**.
  * Training was **too slow** on available GPUs (even with gradient accumulation).
  * We never completed a full pretraining run.

> 💡 **Lesson**: From-scratch pretraining is **not feasible** for small academic teams without institutional compute support.

---

## Phase 2 — Pragmatism: Fine-Tuning & Pruning

We switched to **adapting existing open models**. After testing several, we chose **Qwen2.5-Coder-0.5B** for its:

* Strong baseline performance on code,
* Support for FIM,
* Clean architecture and recent release (2024).

### Key Experiments

#### Vocabulary Pruning

* Qwen’s tokenizer had **151k+ tokens**, many irrelevant to Python.
* We **pruned it to ~90k tokens** by analyzing token usage over 1B+ tokens of Python code.
* **Result**:

  * Model size ↓ by **~209 MB**
  * Embedding params ↓ by **~40%**
  * Slight throughput improvement (~8% faster token generation)

> **Caveat**: The pruning script exists in `/Scripts/downsize/`, but the exact pruned tokenizer used in the final model **may not be in this repo**.

#### 📚 Dataset Curation

* Scraped **~4,500 fresh GitHub repos** (Feb 2024 – Apr 2025) to avoid overlap with Qwen’s pretraining cutoff (Jan 2024).
* Used **Tree-sitter** to extract cross-file contexts (e.g., class definitions from imports).
* Built **FIM-style samples** where the model predicts missing middle spans given prefix + suffix + external context.
* Normalized code using **Ruff** (tabs → spaces, trailing whitespace, etc.).

> 🗂️ Most preprocessing scripts are in `/Scripts/pipeline/`, but **not all are runnable**—some depend on now-missing config files or internal paths.

#### Fine-Tuning Strategy

* **Stage 1**: Further pretraining on fresh Python code (1 epoch, cosine LR).
* **Stage 2**: Task-specific fine-tuning on ~30k FIM samples with cross-file context (3 epochs, constant LR).
* Used **loss masking** so only the “middle” tokens contributed to loss.
* Evaluated using **HumanEval-Infill** and **Exact Match** on held-out test sets.

> 📉 Training logs and metrics are in the report (Section 6), but **training scripts may be incomplete or uncommitted**.

---

## Phase 3 — Deployment: Local, Fast, Offline

We built two main components:

### 1. **C++ Inference Server (via llama.cpp)**

* Quantized model to **GGUF INT8** format.
* Added **HTTP API** for communication.
* Implemented **KV caching**, **prompt reuse**, and **RoPE shifting** for low-latency completions.
* Handled **FIM prompt formatting** and **context stitching**.

> 🔧 The server code **was built using CMake and llama.cpp**, but the exact version used **is not pinned** in this repo. You may need to rebuild from a specific `llama.cpp` commit.

### 2. **VS Code Extension**

* Written in **TypeScript**.
* Triggers completions on typing.
* Sends **prefix**, **suffix**, and **cross-file context chunks** to the backend.
* Supports **chat-based queries** (Ctrl+Alt+A).

> The extension is in a different repository `/extension/` **should work if the backend is running**, but setup is manual and **not well-documented**.

---

## Results Summary

| **Metric / Component**       | **Before**      | **After**                                    | **Improvement / Notes**                                                             |
| ---------------------------- | --------------- | -------------------------------------------- | ----------------------------------------------------------------------------------- |
| **Vocabulary Size**          | 151,658 tokens  | **90,869 tokens**                            | ↓ **60,789 tokens** (≈40% reduction)                                                |
| **Embedding Parameters**     | 135,885,568     | **54,547,584**                               | ↓ **81,337,984** (≈60% fewer)                                                       |
| **Total Model Parameters**   | 548,428,032     | **439,332,864**                              | ↓ **109,095,168**                                                                   |
| **Model Size (FP32)**        | 1,884 MB        | **1,675 MB**                                 | ↓ **209 MB**                                                                        |
| **Token Throughput (CPU)**   | 7.25 tokens/sec | **8.10 tokens/sec**                          | ↑ **0.85 tokens/sec** (≈12% faster)                                                 |
| **Training Dataset (Fresh)** | —               | **4.5 GB** Python code                       | Scraped from **4,500 GitHub repos** (Feb 2024 – Feb 2025)                           |
| **Fine-tuning Dataset**      | —               | **~30,000 FIM samples**                      | Built using **Tree-sitter** for cross-file context (e.g., class imports, API usage) |
| **Fine-tuning Epochs**       | —               | **3 epochs**                                 | Focused on **cross-file-aware FIM completions**                                     |
| **Quantization**             | FP32 / BF16     | **INT8 (GGUF)**                              | Enabled **CPU-only inference** via `llama.cpp`                                      |
| **Latency (Backend)**        | —               | **Median: 19.88 ms**<br>**Mean: 18.56 ms**   | Measured per completion sample (see Fig 6.14)                                       |
| **Evaluation**               | —               | **HumanEval-Infill**<br>**Exact Match (EM)** | Pass@k scores improved post-FIM training; EM tracked during fine-tuning (Fig 6.8)   |

> 💡 **Note**: All results reflect the **final fine-tuned Qwen2.5-Coder-0.5B** model with pruned vocabulary, quantized to INT8, and evaluated on local CPU (no GPU).

---

## Repository Structure (As-Is)

> **Warning**: This is a **research dump**, not a product. Expect:
>
> * Broken imports
> * Hardcoded paths
> * Notebooks that don’t run
> * Scripts that depend on missing data
> * Multiple versions of the same idea

| Path                   | Status                                                                            |
| ---------------------- | --------------------------------------------------------------------------------- |
| `/Scripts/model.py/`   | Early LLaMA-like architecture (never trained to convergence)                      |
| `/Scripts/tokenizer/`  | BPE tokenizer experiments (largely unused after switching to Qwen)                |
| `/Scripts/pipeline/`   | Data scraping, cleaning, FIM formatting (partially functional)                    |
| `/Scripts/downsize/`   | Vocabulary pruning & model slimming (core logic present, but integration unclear) |
| `/Scripts/evaluation/` | HumanEval/MBPP runners (may require manual path fixes)                            |
| `./**.ipynb`           | Exploratory analysis (mostly obsolete)                                            |
| `/models/`             | **Empty or placeholder** — actual model weights **not included** (too large)      |

---

## Key Takeaways (From Report & Experience)

* ✅ **Fine-tuning > Pretraining** for small teams.
* ✅ **Vocabulary pruning** is low-hanging fruit for domain-specific models.
* ✅ **FIM + cross-file context** significantly improves suggestion relevance.
* ✅ **llama.cpp + quantization** makes sub-1B models viable on CPU.
* ❌ **Training from scratch** is a trap without serious resources.
* ❌ **Research code ≠ production code** — and that’s fine.

---

## Current Status

**Development has ended.**
This repo is archived as a **learning artifact**, not a maintained tool.

But if you’re curious about:

* On-device code LLMs,
* Vocabulary pruning,
* FIM fine-tuning,
* Local VS Code AI assistants,

…then **dig in!** Fork it, fix it, learn from our mistakes.

Just don’t expect it to “just work.”

---

## Documentation

For full technical details, see our final report:
**[PySage_Report.pdf](PySage_Report.pdf)**

---

## 🙏 Acknowledgements

This project was made possible by:

* Open models (**Qwen**, **llama.cpp**)
* Open datasets (**The Stack**, **HumanEval**)
* Open tools (**Tree-sitter**, **Ruff**, **Hugging Face**)
* And a lot of coffee
