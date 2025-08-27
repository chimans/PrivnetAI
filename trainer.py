from dataclasses import dataclass
import time, torch, torch.nn.functional as F
from torch.optim import Adam

@dataclass
class TrainConfig:
    lr: float = 0.01
    weight_decay: float = 5e-4
    epochs: int = 100

def train_and_eval(model, data, cfg: TrainConfig, device: str = "cpu"):
    model, data = model.to(device), data.to(device)
    opt = Adam(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    best_val, best_state = 0.0, None
    t0 = time.time()

    for epoch in range(1, cfg.epochs + 1):
        model.train()
        opt.zero_grad()
        out = model(data.x, data.edge_index)
        loss = F.cross_entropy(out[data.train_mask], data.y[data.train_mask])
        loss.backward(); opt.step()

        model.eval()
        with torch.no_grad():
            logits = model(data.x, data.edge_index)
            pred = logits.argmax(1)
            tr = (pred[data.train_mask]==data.y[data.train_mask]).float().mean().item()
            va = (pred[data.val_mask]==data.y[data.val_mask]).float().mean().item()
            te = (pred[data.test_mask]==data.y[data.test_mask]).float().mean().item()
        if va > best_val:
            best_val, best_state = va, {k: v.cpu().clone() for k,v in model.state_dict().items()}
        if epoch % 10 == 0 or epoch == 1:
            print(f"Epoch {epoch:03d} | loss={loss.item():.4f} | train={tr:.3f} | val={va:.3f} | test={te:.3f}")

    if best_state: model.load_state_dict(best_state)
    total = time.time() - t0
    model.eval()
    with torch.no_grad():
        logits = model(data.x, data.edge_index)
        pred = logits.argmax(1)
        tr = (pred[data.train_mask]==data.y[data.train_mask]).float().mean().item()
        va = (pred[data.val_mask]==data.y[data.val_mask]).float().mean().item()
        te = (pred[data.test_mask]==data.y[data.test_mask]).float().mean().item()
    return {"train_acc": tr, "val_acc": va, "test_acc": te, "time_sec": total}


