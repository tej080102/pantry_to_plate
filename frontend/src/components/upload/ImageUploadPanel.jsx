import { SectionCard } from "../common/SectionCard";
import { InlineMessage } from "../common/InlineMessage";

export function ImageUploadPanel({
  file,
  previewUrl,
  isDetecting,
  error,
  fallbackMode,
  onFileChange,
  onDetect,
  onLoadSample,
}) {
  return (
    <SectionCard
      title="1. Upload Pantry Photo"
      subtitle="Upload a photo or jump straight to sample detections."
      actions={
        <button className="button button--secondary" onClick={onLoadSample} type="button">
          Load Sample Detections
        </button>
      }
    >
      <div className="upload-panel">
        <label className="upload-dropzone">
          <input
            accept="image/*"
            className="sr-only"
            onChange={onFileChange}
            type="file"
          />
          <span className="upload-dropzone__title">
            {file ? file.name : "Choose a pantry photo"}
          </span>
        </label>

        {previewUrl ? (
          <div className="preview-card">
            <img alt="Selected pantry" className="preview-card__image" src={previewUrl} />
          </div>
        ) : (
          <div className="preview-placeholder">
            No image selected yet. Upload a photo or use sample detections to continue the demo.
          </div>
        )}
      </div>

      <div className="button-row">
        <button
          className="button"
          disabled={!file || isDetecting}
          onClick={onDetect}
          type="button"
        >
          {isDetecting ? "Detecting..." : "Detect Ingredients"}
        </button>
      </div>

      {fallbackMode ? (
        <InlineMessage tone="warning">
          Image detection is unavailable right now. Use sample detections or add items manually.
        </InlineMessage>
      ) : null}

      {error ? <InlineMessage tone="error">{error}</InlineMessage> : null}
    </SectionCard>
  );
}
