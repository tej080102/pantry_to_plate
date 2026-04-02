const toneClassByValue = {
  HIGH: "badge badge--high",
  MEDIUM: "badge badge--medium",
  LOW: "badge badge--low",
  UNKNOWN: "badge badge--unknown",
  ACTIVE: "badge badge--active",
  ARCHIVED: "badge badge--archived",
  DISMISSED: "badge badge--dismissed",
};

export function StatusBadge({ label }) {
  return <span className={toneClassByValue[label] || "badge"}>{label}</span>;
}
