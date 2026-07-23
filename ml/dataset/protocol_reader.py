from pathlib import Path

def encode_label(label):
    if label == "bonafide":
        return 0
    elif label == "spoof": 
        return 1
    else:
        raise ValueError(f"Unknown label: {label}")
    

def load_protocol(protocol_path):
    samples = []
    
    p_path = Path(protocol_path)

    with open(p_path, "r") as f:
        for line in f:
            parts = line.strip().split()
            
            audio_file = parts[1] + ".flac"
            label = encode_label(parts[4])

            sample = {
                "audio_file": audio_file,
                "label": label
            }
            samples.append(sample)

    return samples

if __name__ == "__main__":
    
    protocol_path = r"E:\datasets\ASVspoof2019_LA_cm_protocols\ASVspoof2019.LA.cm.train.trn.txt"
    
    samples = load_protocol(protocol_path)
    
    print(f"Total Samples : {len(samples)}")
    print(samples[0])
    print(samples[1])