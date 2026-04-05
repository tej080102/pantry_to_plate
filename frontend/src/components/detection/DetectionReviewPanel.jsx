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

function resolvedMatchName(row, ingredientIndex) {
  const correctedName = row.corrected_name.trim();
  if (correctedName) {
    return correctedName;
  }
  const autoMatch = ingredientIndex.get(normalizeName(row.detected_name || ""));
  return autoMatch || "";
}

function ReviewRow({
  row,
  index,
  ingredients,
  ingredientIndex,
  onChangeRow,
  onRemoveRow,
}) {
  const quickAddIngredients = ingredients.slice(0, 10);

  function suggestionOptions() {
    const query = normalizeName(row.corrected_name || row.detected_name || "");
    if (!query) {
      return quickAddIngredients.slice(0, 6);
    }

    const exactish = ingredients.filter((ingredient) =>
      ingredient.name.toLowerCase().includes(query),
    );
    return (exactish.length ? exactish : quickAddIngredients).slice(0, 6);
  }

  const rowState = reviewStateForRow(row, ingredientIndex);
  const resolvedMatch = resolvedMatchName(row, ingredientIndex);

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
      </div>

      <div className="review-row__footer">
        <p className="helper-text">
          {resolvedMatch
            ? `Saving as ${resolvedMatch}.`
            : "Needs a catalog match before it is easy to trust."}
        </p>

        <div className="chip-group">
          {suggestionOptions().map((ingredient) => (
            <button
              className={
                resolvedMatch === ingredient.name
                  ? "chip-button chip-button--selected"
                  : "chip-button"
              }
              key={`${row.id}-${ingredient.id}`}
              onClick={() => onChangeRow(row.id, "corrected_name", ingredient.name)}
              type="button"
            >
              {ingredient.name}
            </button>
          ))}
        </div>
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
      subtitle="Clean up the latest scan, then save only the rows you trust."
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
                  <h3>Needs attention</h3>
                  <p>These rows do not yet have a confident pantry match.</p>
                </div>
                <StatusBadge label="MEDIUM" />
              </div>
              <div className="review-stack">
                {attentionRows.map((row) => (
                  <ReviewRow
                    key={row.id}
                    index={rows.findIndex((item) => item.id === row.id)}
                    ingredientIndex={ingredientIndex}
                    ingredients={ingredients}
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
                  <p>These rows already have enough information to go into the pantry.</p>
                </div>
                <StatusBadge label="LOW" />
              </div>
              <div className="review-stack">
                {readyRows.map((row) => (
                  <ReviewRow
                    key={row.id}
                    index={rows.findIndex((item) => item.id === row.id)}
                    ingredientIndex={ingredientIndex}
                    ingredients={ingredients}
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

      <div className="quick-add-bar">
        <span className="helper-text">Quick add common ingredients</span>
        <div className="chip-group">
          {ingredients.slice(0, 10).map((ingredient) => (
            <button
              className="chip-button"
              key={`quick-${ingredient.id}`}
              onClick={() =>
                onAddRow({
                  detected_name: ingredient.name.toLowerCase(),
                  corrected_name: ingredient.name,
                  unit: ingredient.standard_unit || "",
                })
              }
              type="button"
            >
              {ingredient.name}
            </button>
          ))}
        </div>
      </div>

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
