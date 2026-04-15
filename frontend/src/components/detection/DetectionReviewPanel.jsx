import { SectionCard } from "../common/SectionCard";
import { InlineMessage } from "../common/InlineMessage";
import { StatusBadge } from "../common/StatusBadge";

function createBlankRow() {
  return {
    id: crypto.randomUUID(),
    detected_name: "",
    corrected_name: "",
    quantity: "",
    unit: "",
    estimated_expiry_date: "",
  };
}

function normalizeName(value) {
  return value.trim().toLowerCase();
}

function createIngredientIndex(ingredients) {
  return new Map(ingredients.map((ingredient) => [normalizeName(ingredient.name), ingredient.name]));
}

function reviewStateForRow(row, ingredientIndex) {
  const detectedName = normalizeName(row.detected_name || "");
  const correctedName = normalizeName(row.corrected_name || "");

  if (!detectedName) {
    return "UNKNOWN";
  }

  if (correctedName || ingredientIndex.has(detectedName)) {
    return "LOW";
  }

  return "MEDIUM";
}

function ReviewRow({
  row,
  index,
  ingredientIndex,
  onChangeRow,
  onRemoveRow,
}) {
  const rowState = reviewStateForRow(row, ingredientIndex);

  return (
    <article className="review-row">
      <div className="review-row__topline">
        <div className="review-row__identity">
          <strong>Detection {index + 1}</strong>
          <StatusBadge label={rowState} />
        </div>
        <button className="link-button" onClick={() => onRemoveRow(row.id)} type="button">
          Remove
        </button>
      </div>

      <div className="review-row__fields">
        <label>
          Detected name
          <input
            onChange={(event) => onChangeRow(row.id, "detected_name", event.target.value)}
            placeholder="e.g. spinach"
            value={row.detected_name}
          />
        </label>

        <label>
          Catalog match
          <input
            list="ingredient-options"
            onChange={(event) => onChangeRow(row.id, "corrected_name", event.target.value)}
            placeholder="Choose a catalog match"
            value={row.corrected_name}
          />
        </label>

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
          Expiry date
          <input
            onChange={(event) => onChangeRow(row.id, "estimated_expiry_date", event.target.value)}
            type="date"
            value={row.estimated_expiry_date || ""}
          />
        </label>
      </div>

      <div className="review-row__footer">
        <p className="helper-text">Edit the row only if you want to rename or refine this ingredient.</p>
      </div>
    </article>
  );
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
  const ingredientIndex = createIngredientIndex(ingredients);
  const totalRows = rows.length;
  const readyRows = rows.filter((row) => reviewStateForRow(row, ingredientIndex) === "LOW");
  const attentionRows = rows.filter((row) => reviewStateForRow(row, ingredientIndex) !== "LOW");
  const quantityRows = rows.filter((row) => row.quantity !== "" && row.quantity != null);

  return (
    <SectionCard
      title="2. Review Detections"
      subtitle="Clean up the latest scan, set quantity and expiry, then save what you want."
      actions={
        <div className="button-row button-row--compact">
          <button className="button button--secondary" onClick={onAddRow} type="button">
            Add Ingredient
          </button>
          <button
            className="button"
            disabled={rows.length === 0 || isSubmitting}
            onClick={onSubmit}
            type="button"
          >
            {isSubmitting ? "Saving..." : "Save to Pantry"}
          </button>
        </div>
      }
    >
      <div className="insight-strip">
        <div className="insight-tile">
          <span>Total rows</span>
          <strong>{totalRows}</strong>
        </div>
        <div className="insight-tile">
          <span>Ready to save</span>
          <strong>{readyRows.length}</strong>
        </div>
        <div className="insight-tile">
          <span>Need attention</span>
          <strong>{attentionRows.length}</strong>
        </div>
        <div className="insight-tile">
          <span>With quantity</span>
          <strong>{quantityRows.length}</strong>
        </div>
      </div>

      {rows.length === 0 ? (
        <div className="empty-state">
          Start with a photo, sample detections, or quick-add an ingredient to begin review.
        </div>
      ) : (
        <div className="stack-group">
          {attentionRows.length ? (
            <section className="list-section">
              <div className="list-section__header">
                <div>
                  <h3>Needs review</h3>
                  <p>These rows may need a quick edit before you save them.</p>
                </div>
                <StatusBadge label="MEDIUM" />
              </div>
              <div className="review-stack">
                {attentionRows.map((row) => (
                  <ReviewRow
                    key={row.id}
                    index={rows.findIndex((item) => item.id === row.id)}
                    ingredientIndex={ingredientIndex}
                    onChangeRow={onChangeRow}
                    onRemoveRow={onRemoveRow}
                    row={row}
                  />
                ))}
              </div>
            </section>
          ) : null}

          {readyRows.length ? (
            <section className="list-section">
              <div className="list-section__header">
                <div>
                  <h3>Ready to save</h3>
                  <p>These rows are ready to go into the pantry as they are.</p>
                </div>
                <StatusBadge label="LOW" />
              </div>
              <div className="review-stack">
                {readyRows.map((row) => (
                  <ReviewRow
                    key={row.id}
                    index={rows.findIndex((item) => item.id === row.id)}
                    ingredientIndex={ingredientIndex}
                    onChangeRow={onChangeRow}
                    onRemoveRow={onRemoveRow}
                    row={row}
                  />
                ))}
              </div>
            </section>
          ) : null}
        </div>
      )}

      <datalist id="ingredient-options">
        {ingredients.map((ingredient) => (
          <option key={ingredient.id} value={ingredient.name} />
        ))}
      </datalist>

      {error ? <InlineMessage tone="error">{error}</InlineMessage> : null}

      {ingestResult?.unmatched_detected_ingredients?.length ? (
        <InlineMessage tone="warning">
          Some detections are still unmatched. Review the rows marked as needing attention.
        </InlineMessage>
      ) : null}
    </SectionCard>
  );
}

DetectionReviewPanel.createBlankRow = createBlankRow;
