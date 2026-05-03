"""
ML Benchmark — CSC Supercomputer vs Personal Computer
Run on both machines, compare the printed times.
"""

import time, socket
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.datasets import make_classification
from sklearn.preprocessing import StandardScaler
import numpy as np

# ── Config ────────────────────────────────────────────────────────
EPOCHS     = 20
BATCH_SIZE = 512
N_SAMPLES  = 100_000
N_FEATURES = 256
N_CLASSES  = 10
device     = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ── Data ──────────────────────────────────────────────────────────
X, y = make_classification(N_SAMPLES, N_FEATURES, n_classes=N_CLASSES,
                           n_informative=180, random_state=42)
X    = StandardScaler().fit_transform(X).astype(np.float32)
X, y = torch.tensor(X).to(device), torch.tensor(y).to(device)

# ── Residual Block ────────────────────────────────────────────────
class ResBlock(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.block = nn.Sequential(
            nn.Linear(dim, dim * 4), nn.GELU(), nn.Dropout(0.1),
            nn.Linear(dim * 4, dim), nn.Dropout(0.1),
        )
        self.norm = nn.LayerNorm(dim)
    def forward(self, x):
        return x + self.block(self.norm(x))

# ── Heavy Model (12 residual blocks, 1024 hidden dim) ─────────────
class HeavyNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.input_proj = nn.Sequential(
            nn.Linear(N_FEATURES, 1024), nn.LayerNorm(1024), nn.GELU()
        )
        self.blocks = nn.Sequential(*[ResBlock(1024) for _ in range(12)])
        self.head   = nn.Sequential(
            nn.LayerNorm(1024),
            nn.Linear(1024, 512), nn.GELU(), nn.Dropout(0.2),
            nn.Linear(512, 256),  nn.GELU(),
            nn.Linear(256, N_CLASSES)
        )
    def forward(self, x):
        return self.head(self.blocks(self.input_proj(x)))

model     = HeavyNet().to(device)
optimizer = optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-4)
scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
loss_fn   = nn.CrossEntropyLoss(label_smoothing=0.1)
total_params = sum(p.numel() for p in model.parameters())

# ── Training ──────────────────────────────────────────────────────
print(f"\nHost   : {socket.gethostname()}")
print(f"Device : {device}")
print(f"Params : {total_params:,}")
print(f"Data   : {N_SAMPLES:,} samples x {N_FEATURES} features")
print(f"{'─'*48}")
print(f"{'Epoch':<8}{'Loss':<12}{'Accuracy':<14}{'Time (s)'}")
print(f"{'─'*48}")

total_start = time.perf_counter()

for epoch in range(1, EPOCHS + 1):
    model.train()
    t0, correct, total_seen = time.perf_counter(), 0, 0

    for i in range(0, N_SAMPLES, BATCH_SIZE):
        xb, yb = X[i:i+BATCH_SIZE], y[i:i+BATCH_SIZE]
        optimizer.zero_grad(set_to_none=True)
        out  = model(xb)
        loss = loss_fn(out, yb)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        correct    += (out.argmax(1) == yb).sum().item()
        total_seen += yb.size(0)

    scheduler.step()
    acc = correct / total_seen * 100
    print(f"{epoch:<8}{loss.item():<12.4f}{acc:<14.2f}{time.perf_counter()-t0:.3f}")

total = time.perf_counter() - total_start
print(f"{'─'*48}")
print(f"\n  Total training time : {total:.2f}s")
print(f"  Avg time per epoch  : {total/EPOCHS:.2f}s")
print(f"\n  >>> Save this time and compare with the other machine! <<<\n")