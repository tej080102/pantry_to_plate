import { useState } from "react";

import { SectionCard } from "../common/SectionCard";
import { StatusBadge } from "../common/StatusBadge";
import { InlineMessage } from "../common/InlineMessage";

function lifecycleLabelForItem(item) {
  if (item.is_false_positive) {
    return "DISMISSED";
  }
  if (item.is_archived) {
    return "ARCHIVED";
  }
  return "ACTIVE";
}

function pantryGroupForItem(item) {
  if (item.is_archived || item.is_false_positive) {
    return "inactive";
  }
  if (item.priority_bucket === "HIGH" || item.priority_bucket === "MEDIUM") {
    return "urgent";
  }
  return "stable";
}

function formatExpiry(item) {
  return item.estimated_expiry_date || "Unknown expiry";
}

function formatQuantity(item) {
  return item.quantity != null ? `${item.quantity} ${item.unit || ""}`.trim() : "Unknown quantity";
}

function PantrySection({
  title,
  description,
  items,
  expandedId,
  editingById,
  busyItemId,
  onExpand,
  onEditChange,
  onSave,
  onDelete,
}) {
  if (!items.length) {
    return null;
  }

  return (
    <section className="list-section">
      <div className="list-section__header">
        <div>
          <h3>{title}</h3>
          <p>{description}</p>
        </div>
        <span className="section-count">{items.length}</span>
      </div>

      <div className="pantry-stack">
        {items.map((item) => {
          const lifecycleLabel = lifecycleLabelForItem(item);
          const isExpanded = expandedId === item.id;
          const isBusy = busyItemId === item.id;
          const editingState = editingById[item.id] || {
            quantity: item.quantity ?? "",
            unit: item.unit ?? "",
          };

          return (
            <article className="pantry-row" key={item.id}>
              <button
                className="pantry-row__summary"
                onClick={() => onExpand(isExpanded ? null : item.id)}
                type="button"
              >
                <div className="pantry-row__main">
                  <div className="pantry-row__titleblock">
                    <h4>{item.ingredient.name}</h4>
                    <p>
                      {formatQuantity(item)} • {formatExpiry(item)}
                    </p>
                    {item.source_detected_name ? (
                      <span className="pantry-row__source">
                        Detected as {item.source_detected_name}
                      </span>
                    ) : null}
                  </div>
                </div>

                <div className="pantry-row__aside">
                  <div className="badge-row">
                    <StatusBadge label={item.priority_bucket} />
                    <StatusBadge label={lifecycleLabel} />
                  </div>
                  <span className="pantry-row__toggle">
                    {isExpanded ? "Hide actions" : "Edit item"}
                  </span>
                </div>
              </button>

              {isExpanded ? (
                <div className="pantry-row__editor">
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
                  </div>

                  <div className="button-row">
                    <button
                      className="button button--secondary"
                      disabled={isBusy}
                      onClick={() => onSave(item.id)}
                      type="button"
                    >
                      Save changes
                    </button>
                    <button
                      className="button button--danger"
                      disabled={isBusy}
                      onClick={() => onDelete(item.id)}
                      type="button"
                    >
                      Delete item
                    </button>
                  </div>
                </div>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
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
  const [expandedId, setExpandedId] = useState(null);
  const [activeFilter, setActiveFilter] = useState("all");

  const urgentItems = items.filter((item) => pantryGroupForItem(item) === "urgent");
  const stableItems = items.filter((item) => pantryGroupForItem(item) === "stable");
  const inactiveItems = items.filter((item) => pantryGroupForItem(item) === "inactive");

  const filteredItems = items.filter((item) => {
    if (activeFilter === "urgent") {
      return pantryGroupForItem(item) === "urgent";
    }
    if (activeFilter === "stable") {
      return pantryGroupForItem(item) === "stable";
    }
    if (activeFilter === "inactive") {
      return pantryGroupForItem(item) === "inactive";
    }
    return true;
  });

  const visibleUrgent = filteredItems.filter((item) => pantryGroupForItem(item) === "urgent");
  const visibleStable = filteredItems.filter((item) => pantryGroupForItem(item) === "stable");
  const visibleInactive = filteredItems.filter((item) => pantryGroupForItem(item) === "inactive");

  return (
    <SectionCard
      title="4. Pantry Dashboard"
      subtitle="See what to use first, then expand a row only when you need to edit it."
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
      <div className="insight-strip">
        <div className="insight-tile">
          <span>Total items</span>
          <strong>{items.length}</strong>
        </div>
        <div className="insight-tile insight-tile--urgent">
          <span>Use soon</span>
          <strong>{urgentItems.length}</strong>
        </div>
        <div className="insight-tile">
          <span>Stable</span>
          <strong>{stableItems.length}</strong>
        </div>
        <div className="insight-tile">
          <span>Inactive</span>
          <strong>{inactiveItems.length}</strong>
        </div>
      </div>

      <div className="filter-bar">
        {[
          { id: "all", label: "All items" },
          { id: "urgent", label: "Use soon" },
          { id: "stable", label: "Stable" },
          { id: "inactive", label: "Inactive" },
        ].map((filter) => (
          <button
            className={
              activeFilter === filter.id
                ? "chip-button chip-button--selected"
                : "chip-button"
            }
            key={filter.id}
            onClick={() => setActiveFilter(filter.id)}
            type="button"
          >
            {filter.label}
          </button>
        ))}
      </div>

      {loading ? <div className="loading-block">Loading pantry...</div> : null}
      {error ? <InlineMessage tone="error">{error}</InlineMessage> : null}

      {!loading && items.length === 0 ? (
        <div className="empty-state">
          No pantry items yet. Save reviewed detections first to build your pantry.
        </div>
      ) : null}

      {!loading && filteredItems.length > 0 ? (
        <div className="stack-group">
          <PantrySection
            busyItemId={busyItemId}
            description="High and medium priority items that should guide recipe choices."
            editingById={editingById}
            expandedId={expandedId}
            items={visibleUrgent}
            onDelete={onDelete}
            onEditChange={onEditChange}
            onExpand={setExpandedId}
            onSave={onSave}
            title="Use soon"
          />

          <PantrySection
            busyItemId={busyItemId}
            description="Active pantry items with lower urgency."
            editingById={editingById}
            expandedId={expandedId}
            items={visibleStable}
            onDelete={onDelete}
            onEditChange={onEditChange}
            onExpand={setExpandedId}
            onSave={onSave}
            title="Stable"
          />

          <PantrySection
            busyItemId={busyItemId}
            description="Archived or dismissed rows shown only when inactive items are included."
            editingById={editingById}
            expandedId={expandedId}
            items={visibleInactive}
            onDelete={onDelete}
            onEditChange={onEditChange}
            onExpand={setExpandedId}
            onSave={onSave}
            title="Inactive"
          />
        </div>
      ) : null}
    </SectionCard>
  );
}
