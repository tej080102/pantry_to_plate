export function SectionCard({ title, subtitle, actions, children }) {
  return (
    <section className="section-card">
      <div className="section-card__header">
        <div>
          <h2>{title}</h2>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
        {actions ? <div className="section-card__actions">{actions}</div> : null}
      </div>
      <div className="section-card__content">{children}</div>
    </section>
  );
}
