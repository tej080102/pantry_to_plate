import { SectionCard } from "../common/SectionCard";
import { InlineMessage } from "../common/InlineMessage";
import { StatusBadge } from "../common/StatusBadge";

function RecipeCard({ item }) {
  const matched = item.ingredients.filter((ingredient) => ingredient.available_in_pantry);
  const missing = item.ingredients.filter((ingredient) => !ingredient.available_in_pantry);
  const urgentMatches = matched.filter((ingredient) => ingredient.is_priority);

  return (
    <article className="recipe-card">
      <div className="recipe-card__header">
        <div>
          <h3>{item.title}</h3>
          <p>
            {item.pantry_coverage_percent}% pantry coverage
            {item.estimated_cook_time_minutes
              ? ` • ${item.estimated_cook_time_minutes} min`
              : ""}
            {item.servings ? ` • ${item.servings} servings` : ""}
          </p>
        </div>
        <div className="badge-row">
          <StatusBadge label={urgentMatches.length ? "HIGH" : missing.length ? "MEDIUM" : "LOW"} />
        </div>
      </div>

      <div className="recipe-summary-grid">
        <div>
          <strong>Matched pantry items</strong>
          <ul>
            {matched.length ? (
              matched.map((ingredient) => (
                <li key={ingredient.name}>
                  {ingredient.name}
                  {ingredient.is_priority ? " (priority)" : ""}
                </li>
              ))
            ) : (
              <li>No pantry overlap found</li>
            )}
          </ul>
        </div>

        <div>
          <strong>Missing ingredients</strong>
          <ul>
            {missing.length ? missing.map((ingredient) => <li key={ingredient.name}>{ingredient.name}</li>) : <li>None</li>}
          </ul>
        </div>
      </div>

      <p className="helper-text">{item.description}</p>

      <div className="recipe-details">
        <div>
          <strong>Ingredient list</strong>
          <ul>
            {item.ingredients.map((ingredient) => (
              <li key={ingredient.name}>
                {ingredient.quantity ? `${ingredient.quantity} ` : ""}
                {ingredient.name}
                {ingredient.available_in_pantry ? " (in pantry)" : ""}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <strong>Instructions</strong>
          <ol className="recipe-steps">
            {item.steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </div>
      </div>

      {item.priority_ingredients_used?.length ? (
        <p className="helper-text">
          Priority ingredients used: {item.priority_ingredients_used.join(", ")}
        </p>
      ) : null}
    </article>
  );
}

export function RecipeGeneratorPanel({
  recipes,
  loading,
  error,
  generationMethod,
  priorityIngredients,
  onGenerate,
}) {
  return (
    <SectionCard
      title="4. Recipe Suggestions"
      subtitle="Generate live suggestions from the current pantry state."
      actions={
        <button className="button" disabled={loading} onClick={onGenerate} type="button">
          {loading ? "Generating..." : "Generate Recipes"}
        </button>
      }
    >
      {error ? <InlineMessage tone="error">{error}</InlineMessage> : null}

      {generationMethod ? (
        <InlineMessage tone="info">
          Generated with `{generationMethod}`
          {priorityIngredients?.length ? ` using priority items: ${priorityIngredients.join(", ")}` : "."}
        </InlineMessage>
      ) : null}

      {!loading && recipes.length === 0 ? (
        <div className="empty-state">
          No recipe suggestions yet. Load pantry items first, then generate suggestions.
        </div>
      ) : null}

      <div className="recipe-grid">
        {recipes.map((item) => (
          <RecipeCard item={item} key={`${item.title}-${item.estimated_cook_time_minutes}`} />
        ))}
      </div>
    </SectionCard>
  );
}
