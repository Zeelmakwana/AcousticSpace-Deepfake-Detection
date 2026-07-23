import { useRef, useState } from "react";

interface Props {
  onFileSelected: (file: File) => void;
  isLoading: boolean;
}

const ACCEPTED = ".wav,.mp3,.flac,.ogg,.m4a";
const ACCEPTED_MIME = [
  "audio/wav", "audio/wave", "audio/mpeg", "audio/mp3",
  "audio/flac", "audio/ogg", "audio/mp4", "audio/x-m4a",
];

function isAudioFile(file: File): boolean {
  return (
    ACCEPTED_MIME.includes(file.type) ||
    ACCEPTED.split(",").some((ext) =>
      file.name.toLowerCase().endsWith(ext)
    )
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export default function UploadAudio({ onFileSelected, isLoading }: Props) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [typeError, setTypeError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropRef  = useRef<HTMLDivElement>(null);

  const handleFiles = (files: FileList | null) => {
    setTypeError(null);
    if (!files || files.length === 0) return;
    const file = files[0];
    if (!isAudioFile(file)) {
      setTypeError(`"${file.name}" is not a supported audio format. Please upload WAV, MP3, FLAC, OGG, or M4A.`);
      return;
    }
    setSelectedFile(file);
    onFileSelected(file);
  };

  // Keyboard activation of the drop zone
  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      if (!isLoading) inputRef.current?.click();
    }
  }

  const isDragOver = dragActive && !isLoading;

  return (
    <div className="upload-section">
      {/* Visually hidden label for the invisible file input */}
      <label htmlFor="audio-file-input" className="sr-only">
        Upload audio file for deepfake analysis
      </label>

      {/* Dropzone */}
      <div
        ref={dropRef}
        role="button"
        tabIndex={isLoading ? -1 : 0}
        aria-disabled={isLoading}
        aria-label={
          isLoading
            ? "Analysing audio, please wait"
            : "Drop an audio file here or press Enter to browse"
        }
        className={[
          "upload-dropzone",
          isDragOver ? "active" : "",
          isLoading  ? "upload-dropzone--loading" : "",
          selectedFile && !isLoading ? "upload-dropzone--has-file" : "",
        ]
          .filter(Boolean)
          .join(" ")}
        onDragOver={(e) => {
          if (isLoading) return;
          e.preventDefault();
          setDragActive(true);
        }}
        onDragEnter={(e) => {
          if (isLoading) return;
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={(e) => {
          // Only clear if leaving the drop zone itself, not a child
          if (!dropRef.current?.contains(e.relatedTarget as Node)) {
            setDragActive(false);
          }
        }}
        onDrop={(e) => {
          e.preventDefault();
          if (isLoading) return;
          setDragActive(false);
          handleFiles(e.dataTransfer.files);
        }}
        onClick={() => {
          if (isLoading) return;
          inputRef.current?.click();
        }}
        onKeyDown={handleKeyDown}
      >
        <input
          ref={inputRef}
          id="audio-file-input"
          type="file"
          accept={ACCEPTED}
          hidden
          aria-hidden="true"
          tabIndex={-1}
          onChange={(e) => handleFiles(e.target.files)}
        />

        {isLoading ? (
          /* Loading state */
          <div className="upload-loading-state" aria-live="polite">
            <div className="upload-spinner" aria-hidden="true">
              {/* Animated waveform bars */}
              <span className="upload-bar upload-bar--1" />
              <span className="upload-bar upload-bar--2" />
              <span className="upload-bar upload-bar--3" />
              <span className="upload-bar upload-bar--4" />
              <span className="upload-bar upload-bar--5" />
            </div>
            <p className="upload-title">Analysing audio…</p>
            <p className="upload-subtitle">
              Extracting room acoustics, RT60, and breathing patterns
            </p>
          </div>
        ) : selectedFile ? (
          /* File selected state */
          <div className="upload-file-state">
            <span className="upload-file-icon" aria-hidden="true">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 18V5l12-2v13"/>
                <circle cx="6" cy="18" r="3"/>
                <circle cx="18" cy="16" r="3"/>
              </svg>
            </span>
            <p className="upload-title">{selectedFile.name}</p>
            <p className="upload-subtitle">
              {formatBytes(selectedFile.size)} · Click or drop to replace
            </p>
          </div>
        ) : (
          /* Idle state */
          <div className="upload-idle-state">
            <span className="upload-idle-icon" aria-hidden="true">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="16 16 12 12 8 16"/>
                <line x1="12" y1="12" x2="12" y2="21"/>
                <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/>
              </svg>
            </span>
            <p className="upload-title">
              {isDragOver ? "Release to analyse" : "Drop an audio file here"}
            </p>
            <p className="upload-subtitle">
              or <span className="upload-browse-text">click to browse</span>
              <br />
              WAV · MP3 · FLAC · OGG · M4A
            </p>
          </div>
        )}
      </div>

      {/* Type error */}
      {typeError && (
        <p className="upload-type-error" role="alert" aria-live="assertive">
          <span aria-hidden="true">⚠ </span>{typeError}
        </p>
      )}
    </div>
  );
}
