import numpy as np
import torch
import torch.nn.functional as F

from ml.dataset.audio_reader import load_audio
from ml.preprocessing.audio_preprocessor import preprocess_audio
from ml.features.feature_extractor import extract_mfcc
from ml.models.cnn_model import DeepfakeCNN


def fix_feature_size(mfcc, target_frames=64):
    current = mfcc.shape[1]

    if current < target_frames:
        mfcc = np.pad(
            mfcc,
            ((0, 0), (0, target_frames-current)),
            mode="constant"
        )
    else:
        mfcc = mfcc[:, :target_frames]

    return mfcc


model = DeepfakeCNN()
model.load_state_dict(torch.load("deepfake_cnn.pth"))
model.eval()

audio_path = r"E:\datasets\ASVspoof2019_LA_train\flac\LA_T_1138215.flac"

audio, sr = load_audio(audio_path)
audio = preprocess_audio(audio)
mfcc = extract_mfcc(audio, sr)
mfcc = fix_feature_size(mfcc)

feature = torch.tensor(
    mfcc, 
    dtype=torch.float32
).unsqueeze(0).unsqueeze(0)

with torch.no_grad():
    output = model(feature)
    probability = F.softmax(output, dim=1)
    confidence, prediction = torch.max(probability, dim=1)

if prediction.item() == 0:
    print("Prediction : BONAFIDE")
else:
    print("Prediction : SPOOF")

print(f"Confidence : {confidence.item()*100:.2f}%")