export function InlineMessage({ tone = "info", children }) {
  return <div className={`inline-message inline-message--${tone}`}>{children}</div>;
}
