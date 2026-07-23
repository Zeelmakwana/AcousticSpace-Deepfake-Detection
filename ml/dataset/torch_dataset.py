from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset

class DeepfakeDataset(Dataset):

    def __init__(self, dataset_folder):
        dataset_folder = Path(dataset_folder)

        self.features = np.load(dataset_folder / "features.npy")
        self.labels = np.load(dataset_folder / "labels.npy")

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, index):
        feature = torch.tensor(
            self.features[index], 
            dtype=torch.float32
        ).unsqueeze(0)

        label = torch.tensor(
            self.labels[index], 
            dtype=torch.long
        )

        return feature, label