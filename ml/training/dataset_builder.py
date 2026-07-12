from pathlib import Path

import numpy as np
import librosa
from ml.dataset.dataset_loader import DatasetLoader
from ml.preprocessing.audio_preprocessor import preprocess_audio
from ml.features.feature_extractor import extract_mfcc


class DatasetBuilder:

    def __init__(self, protocol_path, audio_folder, output_folder):

        self.dataset = DatasetLoader(
            protocol_path, 
            audio_folder
        )
        self.output_folder = Path(output_folder)

    def fix_feature_size(self, mfcc, target_frames=64):

        current_frames = mfcc.shape[1]

        if current_frames < target_frames:
            pad_width = target_frames - current_frames
            mfcc = np.pad(
                mfcc,
                ((0, 0), (0, pad_width)),
                mode="constant"
            )
        else:
            mfcc = mfcc[:, :target_frames]

        return mfcc

    def build(self):

        features = []
        labels = []
        
        total_samples = len(self.dataset)
        print(f"Processing {total_samples} audio files...\n")

        for index in range(total_samples):
            sample = self.dataset[index]

            audio = sample["audio"]
            sample_rate = sample["sample_rate"]
            label = sample["label"]

            audio = preprocess_audio(audio)
            mfcc = extract_mfcc(audio, sample_rate)
            mfcc = self.fix_feature_size(mfcc)

            features.append(mfcc)
            labels.append(label)

            if (index + 1) % 500 == 0:
                print(f"Processed {index+1}/{total_samples}")

        features = np.array(features)
        labels = np.array(labels)

        self.output_folder.mkdir(parents=True, exist_ok=True)

        np.save(
            self.output_folder / "features.npy", 
            features
        )
        np.save(
            self.output_folder / "labels.npy", 
            labels
        )

        print("\nDataset Saved Successfully!")
        print(features.shape)
        print(labels.shape)
        print(np.unique(labels))
        print(labels[:10])


if __name__ == "__main__":

    builder = DatasetBuilder(
        protocol_path=r"E:\datasets\ASVspoof2019_LA_cm_protocols\ASVspoof2019.LA.cm.train.trn.txt",
        audio_folder=r"E:\datasets\ASVspoof2019_LA_train\flac",
        output_folder=r"E:\my projects\AcousticSpace-Deepfake-Detection\processed_dataset"
    )

    builder.build()