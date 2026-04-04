import { SectionCard } from "../common/SectionCard";
import { StatusBadge } from "../common/StatusBadge";
import { InlineMessage } from "../common/InlineMessage";

function PantryItemCard({
  item,
  editingState,
  onEditChange,
  onSave,
  onDelete,
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
      </dl>

      <div className="pantry-card__controls">
        <div className="pantry-card__editor">
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
          <label>
            Expiry
            <input
              onChange={(event) => onEditChange(item.id, "estimated_expiry_date", event.target.value)}
              type="date"
              value={editingState.estimated_expiry_date}
            />
          </label>
        </div>

        <div className="pantry-card__actions">
          <button
            className="button button--secondary"
            disabled={isBusy}
            onClick={() => onSave(item.id)}
            type="button"
          >
            Save
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
  onSave,
  onDelete,
  editingById,
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
            editingState={
              editingById[item.id] || {
                quantity: item.quantity ?? "",
                unit: item.unit ?? "",
                estimated_expiry_date: item.estimated_expiry_date ?? "",
              }
            }
            item={item}
            key={item.id}
            onDelete={onDelete}
            onEditChange={onEditChange}
            onSave={onSave}
          />
        ))}
      </div>
    </SectionCard>
  );
}
