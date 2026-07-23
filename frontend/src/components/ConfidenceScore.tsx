interface Props {
  prediction: "Real" | "Deepfake";
  confidence: number;
}

export default function ConfidenceScore({ prediction, confidence }: Props) {
  const isFake = prediction === "Deepfake";

  return (
    <div className={`confidence-card ${isFake ? "fake" : "real"}`}>
      <div className="confidence-label">{prediction === "Deepfake" ? "⚠️ Deepfake Detected" : "✅ Real Audio"}</div>
      <div className="confidence-bar-track">
        <div
          className="confidence-bar-fill"
          style={{ width: `${confidence}%` }}
        />
      </div>
      <div className="confidence-value">{confidence.toFixed(2)}% confidence</div>
    </div>
  );
}
