import { SectionCard } from "../common/SectionCard";
import { InlineMessage } from "../common/InlineMessage";

function createBlankRow() {
  return {
    id: crypto.randomUUID(),
    detected_name: "",
    corrected_name: "",
    quantity: "",
    unit: "",
    detected_confidence: "",
  };
}

export function DetectionReviewPanel({
  rows,
  ingestResult,
  isSubmitting,
  ingredients,
  error,
  onChangeRow,
  onAddRow,
  onRemoveRow,
  onSubmit,
}) {
  return (
    <SectionCard
      title="2. Review Detections"
      subtitle="Adjust detected names, add canonical corrections, and ingest them into pantry state."
      actions={
        <button className="button button--ghost" onClick={onAddRow} type="button">
          Add Ingredient
        </button>
      }
    >
      {rows.length === 0 ? (
        <div className="empty-state">
          No detections yet. Upload a photo, load sample detections, or add ingredients manually.
        </div>
      ) : (
        <div className="detection-grid">
          {rows.map((row, index) => (
            <div className="detection-card" key={row.id}>
              <div className="detection-card__header">
                <strong>Detection {index + 1}</strong>
                <button
                  className="link-button"
                  onClick={() => onRemoveRow(row.id)}
                  type="button"
                >
                  Remove
                </button>
              </div>

              <label>
                Detected name
                <input
                  onChange={(event) => onChangeRow(row.id, "detected_name", event.target.value)}
                  placeholder="e.g. spinach"
                  value={row.detected_name}
                />
              </label>

              <label>
                Canonical correction (optional)
                <input
                  list="ingredient-options"
                  onChange={(event) => onChangeRow(row.id, "corrected_name", event.target.value)}
                  placeholder="Leave blank to use detected name"
                  value={row.corrected_name}
                />
              </label>

              <div className="field-row">
                <label>
                  Quantity
                  <input
                    min="0"
                    onChange={(event) => onChangeRow(row.id, "quantity", event.target.value)}
                    placeholder="120"
                    step="0.1"
                    type="number"
                    value={row.quantity}
                  />
                </label>

                <label>
                  Unit
                  <input
                    onChange={(event) => onChangeRow(row.id, "unit", event.target.value)}
                    placeholder="g"
                    value={row.unit}
                  />
                </label>

                <label>
                  Confidence
                  <input
                    max="1"
                    min="0"
                    onChange={(event) =>
                      onChangeRow(row.id, "detected_confidence", event.target.value)
                    }
                    placeholder="0.91"
                    step="0.01"
                    type="number"
                    value={row.detected_confidence}
                  />
                </label>
              </div>
            </div>
          ))}
        </div>
      )}

      <datalist id="ingredient-options">
        {ingredients.map((ingredient) => (
          <option key={ingredient.id} value={ingredient.name} />
        ))}
      </datalist>

      <div className="button-row">
        <button
          className="button"
          disabled={rows.length === 0 || isSubmitting}
          onClick={onSubmit}
          type="button"
        >
          {isSubmitting ? "Saving Pantry..." : "Confirm Pantry State"}
        </button>
      </div>

      {error ? <InlineMessage tone="error">{error}</InlineMessage> : null}

      {ingestResult?.unmatched_detected_ingredients?.length ? (
        <InlineMessage tone="warning">
          Some detections could not be matched to canonical ingredients. They are shown in the
          debug panel below.
        </InlineMessage>
      ) : null}
    </SectionCard>
  );
}

DetectionReviewPanel.createBlankRow = createBlankRow;
