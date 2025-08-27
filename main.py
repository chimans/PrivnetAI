import argparse, torch
from utils import set_seed
from datasets import load_planetoid
from models import GCN
from trainer import TrainConfig, train_and_eval

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset", type=str, default="cora", choices=["cora","citeseer","pubmed"])
    p.add_argument("--hidden", type=int, default=64)
    p.add_argument("--dropout", type=float, default=0.5)
    p.add_argument("--lr", type=float, default=0.01)
    p.add_argument("--weight_decay", type=float, default=5e-4)
    p.add_argument("--epochs", type=int, default=100)
    p.add_argument("--enc_eval", action="store_true", help="Run encrypted linear head eval")
    p.add_argument("--enc_scale", type=float, default=256.0)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--device", type=str, default="auto", choices=["auto","cpu","cuda"])
    return p.parse_args()

def main():
    args = parse_args()
    set_seed(args.seed)
    device = "cuda" if (args.device in ["auto","cuda"] and torch.cuda.is_available()) else "cpu"
    ds_name = {"cora":"Cora","citeseer":"CiteSeer","pubmed":"PubMed"}[args.dataset]
    dataset, data = load_planetoid(name=ds_name)
    model = GCN(dataset.num_node_features, args.hidden, dataset.num_classes, args.dropout)
    stats = train_and_eval(model, data, TrainConfig(args.lr,args.weight_decay,args.epochs), device)
    print("\n=== Final ===")
    print(f"Device: {device}")
    print(f"Dataset: {ds_name}")
    print(f"Train Acc: {stats['train_acc']:.3f}")
    print(f"Val   Acc: {stats['val_acc']:.3f}")
    print(f"Test  Acc: {stats['test_acc']:.3f}")
    print(f"Time (sec): {stats['time_sec']:.1f}")

    if args.enc_eval:
        from encryption import EncryptionShim
        import torch.nn.functional as F
        model.eval()
        with torch.no_grad():
            H = model.forward_hidden(data.x.to(device), data.edge_index.to(device))
        # Train a plain linear head W on plaintext hidden features for stability
        W = torch.zeros(H.size(1), dataset.num_classes, device=device, dtype=torch.float32)
        b = torch.zeros(dataset.num_classes, device=device, dtype=torch.float32)
        # Simple closed-form ridge regression on logits per class (one-vs-rest)
        X = H[data.train_mask]
        Y = F.one_hot(data.y[data.train_mask], num_classes=dataset.num_classes).to(torch.float32)
        lambda_ridge = 1e-3
        XtX = X.T @ X + lambda_ridge * torch.eye(X.size(1), device=device)
        XtY = X.T @ Y
        W = torch.linalg.solve(XtX, XtY)
        # Bias as mean residual on train
        logits_tr = X @ W
        b = (Y - logits_tr).mean(dim=0)

        # Encrypted linear pass: encrypt H and apply linear-only matmul via shim
        shim = EncryptionShim(scale=float(args.enc_scale))
        enc_H = shim.encrypt_tensor(H.cpu())
        enc_logits = shim.matmul_linear_only(enc_H, W.cpu())
        logits_dec = shim.decrypt_tensor(enc_logits).to(device) + b
        pred_enc = logits_dec.argmax(1)
        test_acc_enc = (pred_enc[data.test_mask]==data.y[data.test_mask]).float().mean().item()
        print("Encrypted linear head test acc:", f"{test_acc_enc:.3f}")

if __name__ == "__main__":
    main()
