import torch

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)
from torch.utils.data import DataLoader

from ml.dataset.torch_dataset import DeepfakeDataset
from ml.models.cnn_model import DeepfakeCNN


dataset = DeepfakeDataset(
    r"E:\my projects\AcousticSpace-Deepfake-Detection\processed_dataset"
)

loader = DataLoader(
    dataset,
    batch_size=32,
    shuffle=False
)

model = DeepfakeCNN()
model.load_state_dict(torch.load("deepfake_cnn.pth"))
model.eval()

true_labels = []
predictions = []

with torch.no_grad():
    for features, labels in loader:
        outputs = model(features)
        _, predicted = torch.max(outputs, 1)

        true_labels.extend(labels.numpy())
        predictions.extend(predicted.numpy())

print("\nAccuracy")
print(accuracy_score(true_labels, predictions))

print("\nClassification Report")
print(classification_report(true_labels, predictions))

print("\nConfusion Matrix")
print(confusion_matrix(true_labels, predictions))