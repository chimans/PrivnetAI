import torch
from dataclasses import dataclass

@dataclass
class EncTensor:
    payload: torch.Tensor
    mask: torch.Tensor
    scale: float

class EncryptionShim:
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

    def matmul_linear_only(self, a: EncTensor, W: torch.Tensor) -> EncTensor:
        W_int = torch.round(W.to(torch.float64)).to(torch.int64)
        payload = a.payload.to(torch.int64) @ W_int
        mask    = a.mask.to(torch.int64)    @ W_int
        return EncTensor(payload=payload, mask=mask, scale=a.scale)

if __name__ == "__main__":
    torch.manual_seed(0)
    shim = EncryptionShim(scale=128.0, seed=1)
    x = torch.randn(4, 3)
    W = torch.randn(3, 2)
    enc_x = shim.encrypt_tensor(x)
    enc_y = shim.matmul_linear_only(enc_x, W)
    y_dec = shim.decrypt_tensor(enc_y)

    print(">>> DEMO OK")
    print("y_dec shape:", y_dec.shape)
