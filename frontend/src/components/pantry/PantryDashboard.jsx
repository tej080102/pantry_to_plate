import { SectionCard } from "../common/SectionCard";
import { StatusBadge } from "../common/StatusBadge";
import { InlineMessage } from "../common/InlineMessage";

function PantryItemCard({
  item,
  editingState,
  consumeAmount,
  onEditChange,
  onConsumeChange,
  onSave,
  onConsume,
  onDelete,
  onToggleFalsePositive,
  busyItemId,
}) {
  const isBusy = busyItemId === item.id;
  const lifecycleLabel = item.is_false_positive
    ? "DISMISSED"
    : item.is_archived
      ? "ARCHIVED"
      : "ACTIVE";

  return (
    <article className="pantry-card">
      <div className="pantry-card__header">
        <div>
          <h3>{item.ingredient.name}</h3>
          {item.source_detected_name ? (
            <p>Detected as: {item.source_detected_name}</p>
          ) : null}
        </div>
        <div className="badge-row">
          <StatusBadge label={item.priority_bucket} />
          <StatusBadge label={lifecycleLabel} />
        </div>
      </div>

      <dl className="pantry-card__meta">
        <div>
          <dt>Quantity</dt>
          <dd>{item.quantity != null ? `${item.quantity} ${item.unit || ""}`.trim() : "Unknown"}</dd>
        </div>
        <div>
          <dt>Expiry</dt>
          <dd>{item.estimated_expiry_date || "Unknown"}</dd>
        </div>
        <div>
          <dt>Priority rank</dt>
          <dd>{item.priority_rank}</dd>
        </div>
        <div>
          <dt>Confidence</dt>
          <dd>{item.detected_confidence != null ? item.detected_confidence : "N/A"}</dd>
        </div>
      </dl>

      <div className="pantry-card__controls">
        <div className="field-row">
          <label>
            Quantity
            <input
              min="0"
              onChange={(event) => onEditChange(item.id, "quantity", event.target.value)}
              step="0.1"
              type="number"
              value={editingState.quantity}
            />
          </label>
          <label>
            Unit
            <input
              onChange={(event) => onEditChange(item.id, "unit", event.target.value)}
              value={editingState.unit}
            />
          </label>
          <button
            className="button button--secondary"
            disabled={isBusy}
            onClick={() => onSave(item.id)}
            type="button"
          >
            Save
          </button>
        </div>

        <div className="field-row">
          <label>
            Consume amount
            <input
              min="0"
              onChange={(event) => onConsumeChange(item.id, event.target.value)}
              step="0.1"
              type="number"
              value={consumeAmount}
            />
          </label>
          <div className="quick-action-group">
            {[1, 2, 5].map((amount) => (
              <button
                className="chip-button"
                disabled={isBusy}
                key={`${item.id}-${amount}`}
                onClick={() => onConsumeChange(item.id, String(amount))}
                type="button"
              >
                {amount}
              </button>
            ))}
          </div>
          <button
            className="button button--secondary"
            disabled={isBusy || !consumeAmount}
            onClick={() => onConsume(item.id)}
            type="button"
          >
            Consume
          </button>
          <button
            className="button button--ghost"
            disabled={isBusy}
            onClick={() => onToggleFalsePositive(item)}
            type="button"
          >
            {item.is_false_positive ? "Undo Dismiss" : "Dismiss as False Positive"}
          </button>
          <button
            className="button button--danger"
            disabled={isBusy}
            onClick={() => onDelete(item.id)}
            type="button"
          >
            Delete
          </button>
        </div>
      </div>
    </article>
  );
}

export function PantryDashboard({
  items,
  includeInactive,
  onToggleIncludeInactive,
  onRefresh,
  onEditChange,
  onConsumeChange,
  onSave,
  onConsume,
  onDelete,
  onToggleFalsePositive,
  editingById,
  consumeById,
  busyItemId,
  loading,
  error,
}) {
  return (
    <SectionCard
      title="4. Pantry Dashboard"
      subtitle="Expired items are removed from the active pantry automatically."
      actions={
        <div className="button-row button-row--compact">
          <label className="checkbox">
            <input
              checked={includeInactive}
              onChange={(event) => onToggleIncludeInactive(event.target.checked)}
              type="checkbox"
            />
            Include inactive
          </label>
          <button className="button button--secondary" onClick={onRefresh} type="button">
            Refresh
          </button>
        </div>
      }
    >
      {loading ? <div className="loading-block">Loading pantry...</div> : null}
      {error ? <InlineMessage tone="error">{error}</InlineMessage> : null}

      {!loading && items.length === 0 ? (
        <div className="empty-state">
          No pantry items yet.
        </div>
      ) : null}

      <div className="pantry-grid">
        {items.map((item) => (
          <PantryItemCard
            busyItemId={busyItemId}
            consumeAmount={consumeById[item.id] || ""}
            editingState={editingById[item.id] || { quantity: item.quantity ?? "", unit: item.unit ?? "" }}
            item={item}
            key={item.id}
            onConsume={onConsume}
            onConsumeChange={onConsumeChange}
            onDelete={onDelete}
            onEditChange={onEditChange}
            onSave={onSave}
            onToggleFalsePositive={onToggleFalsePositive}
          />
        ))}
      </div>
    </SectionCard>
  );
}
