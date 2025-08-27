from torch_geometric.datasets import Planetoid
from torch_geometric.transforms import NormalizeFeatures

def load_planetoid(root: str = "data", name: str = "Cora"):
    dataset = Planetoid(root=root, name=name, transform=NormalizeFeatures())
    data = dataset[0]
    return dataset, data
