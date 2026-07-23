import { useState } from "react";
import { analyzeAudio } from "../api/client";
import UploadAudio from "../components/UploadAudio";
import ResultsPanel from "../components/ResultsPanel";
import { SkeletonResultsPanel } from "../components/Skeleton";
import { useToast } from "../contexts/ToastContext";
import type { AnalyzeResponse } from "../types";

export default function Home() {
  const { error: toastError, success: toastSuccess } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);

  const handleFileSelected = async (file: File) => {
    // Revoke previous object URL to avoid memory leaks
    if (audioUrl) URL.revokeObjectURL(audioUrl);

    setIsLoading(true);
    setResult(null);
    setAudioUrl(URL.createObjectURL(file));

    try {
      const response = await analyzeAudio(file);
      setResult(response);
      toastSuccess(
        response.prediction === "Deepfake"
          ? "Deepfake detected"
          : "Audio authenticated",
        `${response.confidence.toFixed(1)}% confidence — ${file.name}`
      );
    } catch (err) {
      console.error(err);
      toastError(
        "Analysis failed",
        "Check that the backend is running and try again."
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="home-page page-enter">
      {/* Hero */}
      <section className="hero">
        <h1>Detect Deepfake Audio<br />Through Room Acoustics</h1>
        <p>
          AcousticSpace analyzes Room Impulse Response, environmental
          reverberation, breathing patterns, and spatial acoustics — not just
          the voice — to catch synthetic audio that traditional detectors miss.
        </p>

        {/* Feature pills */}
        <div className="hero-features" aria-label="Key features">
          {[
            { icon: "〰", label: "RIR Analysis" },
            { icon: "🔊", label: "RT60 Measurement" },
            { icon: "🫁", label: "Breathing Detection" },
            { icon: "🔍", label: "Explainable AI" },
          ].map((f) => (
            <span key={f.label} className="hero-feature-pill">
              <span aria-hidden="true">{f.icon}</span> {f.label}
            </span>
          ))}
        </div>
      </section>

      {/* Upload */}
      <UploadAudio onFileSelected={handleFileSelected} isLoading={isLoading} />

      {/* Skeleton while loading */}
      {isLoading && <SkeletonResultsPanel />}

      {/* Results — animate in */}
      {result && audioUrl && !isLoading && (
        <div className="results-enter">
          <ResultsPanel result={result} audioUrl={audioUrl} />
        </div>
      )}
    </div>
  );
}
