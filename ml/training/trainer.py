import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split

from ml.dataset.torch_dataset import DeepfakeDataset
from ml.models.cnn_model import DeepfakeCNN


BATCH_SIZE = 32
EPOCHS = 10
LEARNING_RATE = 0.001

dataset = DeepfakeDataset(
    r"E:\my projects\AcousticSpace-Deepfake-Detection\processed_dataset"
)

train_size = int(0.8 * len(dataset))
test_size = len(dataset) - train_size

train_dataset, test_dataset = random_split(
    dataset,
    [train_size, test_size]
)

train_loader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True
)
test_loader = DataLoader(
    test_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False
)

model = DeepfakeCNN()
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(
    model.parameters(),
    lr=LEARNING_RATE
)

best_accuracy = 0

for epoch in range(EPOCHS):
    model.train()
    running_loss = 0

    for features, labels in train_loader:
        optimizer.zero_grad()
        outputs = model(features)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        
        running_loss += loss.item()

    model.eval()
    correct = 0
    total = 0

    with torch.no_grad():
        for features, labels in test_loader:
            outputs = model(features)
            _, predicted = torch.max(outputs, 1)
            
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

    accuracy = 100 * correct / total
    print(f"Epoch {epoch+1}/{EPOCHS} | Loss: {running_loss:.2f} | Accuracy: {accuracy:.2f}%")

    if accuracy > best_accuracy:
        best_accuracy = accuracy
        torch.save(
            model.state_dict(),
            "deepfake_cnn.pth"
        )

print("\nTraining Completed")
print(f"Best Accuracy : {best_accuracy:.2f}%")