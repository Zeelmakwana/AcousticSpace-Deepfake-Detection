from pathlib import Path

from ml.dataset.protocol_reader import load_protocol
from ml.dataset.audio_reader import load_audio


class DatasetLoader:

    def __init__(self, protocol_path, audio_folder):

        self.protocol_path = Path(protocol_path)
        self.audio_folder = Path(audio_folder)
        
        self.samples = load_protocol(self.protocol_path)

    def __len__(self):

        return len(self.samples)

    def __getitem__(self, index):

        sample = self.samples[index]

        audio_path = self.audio_folder / sample["audio_file"]

        audio, sample_rate = load_audio(audio_path)

        return {
            "audio": audio,
            "sample_rate": sample_rate,
            "label": sample["label"]
        }


if __name__ == "__main__":

    protocol_path = r"E:\datasets\ASVspoof2019_LA_cm_protocols\ASVspoof2019.LA.cm.train.trn.txt"
    audio_folder = r"E:\datasets\ASVspoof2019_LA_train\flac"

    dataset = DatasetLoader(protocol_path, audio_folder)

    print(f"Total Samples: {len(dataset)}")

    print("\nFirst 5 Samples:\n")

    for i in range(5):

        sample = dataset[i]

        print(f"Sample {i+1}")
        print(f"Label       : {sample['label']}")
        print(f"Sample Rate : {sample['sample_rate']}")
        print(f"Shape       : {sample['audio'].shape}")
        print(f"First 10 Values : {sample['audio'][:10]}")
        print("-" * 50)