## PrivNet.AI PoC — Learning on "quasi-encrypted" graphs

This repository is a small proof-of-concept showing how part of a graph learning pipeline can be executed without directly exposing raw values. The core idea is to use a simple cryptography simulator layer called `EncryptionShim` so we can run at least one linear computation path on "masked" data.

Note: This is not real cryptography and is only used for a proof of concept.

### Why this PoC?
- **Goal**: Quickly produce a demonstrable result indicating we can perform part of inference without direct access to raw data.
- **Setup**: A basic GCN on Planetoid datasets (e.g., Cora). Then we apply a linear head using `EncryptionShim` on the hidden features.

## Architecture and data flow
- **Data loading**: Using `torch_geometric`, the Cora/CiteSeer/PubMed datasets are loaded and normalized.
- **Model training**: A simple two-layer `GCNConv` model is trained and Train/Val/Test accuracies are reported.
- **Hidden features**: The output of the first GCN layer (after ReLU and Dropout) is extracted as the hidden feature matrix \(H\).
- **Linear head (plain)**: A linear head is learned on \(H\) via a simple ridge regression for stability.
- **Masked linear path**: \(H\) is processed with `EncryptionShim` (quantization + additive mask). Then the matrix product \(H W\) is computed linearly on the masked data, the result is "decrypted," and test accuracy is measured.

Reminder: In this PoC, feature extraction \(H\) is done in plaintext. Only the linear head is computed on masked data. This is a small but presentable step toward privacy-preserving learning.

## Installation and run
Prerequisite: Python 3.12+ (tested with 3.13 on macOS/arm64)

```bash
python3 -m venv /Users/chimansoltanian/poc-encrypted-graphs/.venv
source /Users/chimansoltanian/poc-encrypted-graphs/.venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r /Users/chimansoltanian/poc-encrypted-graphs/requirements.txt

# Train + evaluate the masked linear path
python /Users/chimansoltanian/poc-encrypted-graphs/main.py \
  --epochs 50 --dataset cora --device auto --enc_eval
```

### Important flags
- `--dataset {cora|citeseer|pubmed}`: target dataset
- `--epochs N`: number of training epochs
- `--device {auto|cpu|cuda}`: device selection
- `--enc_eval`: enable masked linear path evaluation
- `--enc_scale FLOAT`: quantization scale in `EncryptionShim` (default: 256.0)

## Example output and interpretation
Sample run log:

```text
Epoch 001 | loss=1.9463 | train=0.229 | val=0.138 | test=0.158
...
Epoch 050 | loss=0.5108 | train=0.979 | val=0.806 | test=0.831

=== Final ===
Device: cpu
Dataset: Cora
Train Acc: 0.979
Val   Acc: 0.810
Test  Acc: 0.827
Time (sec): 0.6
Encrypted linear head test acc: 0.492
```

- **Train/Val/Test Acc**: Baseline GCN accuracies on plaintext data.
- **Encrypted linear head test acc**: Accuracy when \(H\) is masked and only the linear head is applied on masked data. It is usually lower because:
  - Quantization and masking introduce approximation error.
  - No nonlinearity is present in the masked path (only linear matmul).

This demonstrates that part of inference can be performed without seeing raw values, though this is not real cryptography and the pipeline remains hybrid.

## Limitations (important)
- `EncryptionShim` is not real cryptography; it is merely quantization + additive masking to simulate linear operations on masked data.
- Only linear operations are supported; nonlinearities (ReLU, Softmax, etc.) are not executed in the masked domain.
- Cryptographic security, ZKPs, and post-quantum resistance are not implemented at this stage.

## Next steps (roadmap summary)
- Replace `EncryptionShim` with real schemes like CKKS/BFV for add/mul.
- Design a fully masked inference path (including approximated nonlinearities).
- Add ZKPs to prove correctness without revealing data.
- Mask/encrypt graph structure (features and edges) and evaluate performance.

## Repository structure
- `main.py`: CLI script for GCN training and masked path evaluation
- `models.py`: `GCN` model and `forward_hidden`
- `datasets.py`: Planetoid loading with `NormalizeFeatures`
- `trainer.py`: Train/eval loop with best-on-Val selection
- `encryption.py`: `EncryptionShim` and `EncTensor`
- `utils.py`: Seed setup and CUDA/CUDNN configuration
- `requirements.txt`: Dependencies (with `torch>=2.6`)

## Disclaimer
This code is for demonstrating the idea and facilitating technical discussion; it makes no real-world cryptographic/security claims. For sensitive applications, use homomorphic cryptography and vetted protocols.


