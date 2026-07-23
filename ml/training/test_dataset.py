import numpy as np

features = np.load(
    r"E:\my projects\AcousticSpace-Deepfake-Detection\processed_dataset\features.npy",
    allow_pickle=True
)

labels = np.load(
    r"E:\my projects\AcousticSpace-Deepfake-Detection\processed_dataset\labels.npy"
)

print(features.shape)

print(labels.shape)

print(np.unique(labels))

print(labels[:10])