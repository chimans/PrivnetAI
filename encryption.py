import torch
from dataclasses import dataclass

@dataclass
class EncTensor:
    payload: torch.Tensor  # quantized + masked (int64)
    mask: torch.Tensor     # random additive mask (int64)
    scale: float           # fixed-point scale

class EncryptionShim:
    """
    Version 0: Quantize + Random Additive Mask
    - encrypt(x):  round(x*scale) + mask
    - decrypt(c):  (c - mask) / scale
    Linear ops: add, mul_scalar, matmul_linear_only
    Note: This is not real cryptography; it's a PoC simulator.
    """
    def __init__(self, scale: float = 256.0, seed: int = 1337):
        self.scale = float(scale)
        self.rng = torch.Generator().manual_seed(seed)

    def encrypt_tensor(self, x: torch.Tensor) -> EncTensor:
        q = torch.round(x * self.scale).to(torch.int64)
        mask = torch.randint(low=-2**31, high=2**31-1, size=q.size(),
                             generator=self.rng, dtype=torch.int64, device=q.device)
        c = q + mask
        return EncTensor(payload=c, mask=mask, scale=self.scale)

    def decrypt_tensor(self, enc: EncTensor) -> torch.Tensor:
        q = enc.payload - enc.mask
        return q.to(torch.float32) / enc.scale

    def add(self, a: EncTensor, b: EncTensor) -> EncTensor:
        assert a.scale == b.scale
        return EncTensor(payload=a.payload + b.payload, mask=a.mask + b.mask, scale=a.scale)

    def mul_scalar(self, a: EncTensor, s: float) -> EncTensor:
        payload = torch.round(a.payload.to(torch.float64) * s).to(torch.int64)
        mask = torch.round(a.mask.to(torch.float64) * s).to(torch.int64)
        return EncTensor(payload=payload, mask=mask, scale=a.scale)

    def matmul_linear_only(self, a: EncTensor, W: torch.Tensor) -> EncTensor:
        W_int = torch.round(W.to(torch.float64)).to(torch.int64)
        payload = a.payload.to(torch.int64) @ W_int
        mask    = a.mask.to(torch.int64)    @ W_int
        return EncTensor(payload=payload, mask=mask, scale=a.scale)

if __name__ == "__main__":
    # Demo: linear matmul on masked ("encrypted-like") data and decrypt result
    torch.manual_seed(0)
    shim = EncryptionShim(scale=128.0, seed=1)
    x = torch.randn(4, 3)
    W = torch.randn(3, 2)

    enc_x = shim.encrypt_tensor(x)
    enc_y = shim.matmul_linear_only(enc_x, W)
    y_dec = shim.decrypt_tensor(enc_y)

    print("x (plain):\n", x)
    print("W:\n", W)
    print("y_dec (approx linear output):\n", y_dec)
