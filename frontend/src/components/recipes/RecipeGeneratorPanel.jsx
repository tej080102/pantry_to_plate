import { SectionCard } from "../common/SectionCard";
import { InlineMessage } from "../common/InlineMessage";
import { StatusBadge } from "../common/StatusBadge";

function RecipeCard({ item }) {
  const { recipe, matched, missing, urgentMatches, nutritionEstimate } = item;

  return (
    <article className="recipe-card">
      <div className="recipe-card__header">
        <div>
          <h3>{recipe.title}</h3>
          <p>
            {recipe.source_name || "Catalog recipe"}
            {recipe.estimated_cook_time_minutes
              ? ` • ${recipe.estimated_cook_time_minutes} min`
              : ""}
            {recipe.servings ? ` • ${recipe.servings} servings` : ""}
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
              matched.map(({ pantryItem, recipeIngredient }) => (
                <li key={recipeIngredient.id}>
                  {recipeIngredient.ingredient.name}
                  {pantryItem.priority_bucket ? ` (${pantryItem.priority_bucket})` : ""}
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
            {missing.length ? missing.map((name) => <li key={name}>{name}</li>) : <li>None</li>}
          </ul>
        </div>
      </div>

      {nutritionEstimate ? (
        <div className="nutrition-strip">
          <span>{nutritionEstimate.calories} kcal</span>
          <span>{nutritionEstimate.protein}g protein</span>
          <span>{nutritionEstimate.carbs}g carbs</span>
          <span>{nutritionEstimate.fat}g fat</span>
          <span>{nutritionEstimate.fiber}g fiber</span>
        </div>
      ) : null}

      <div className="recipe-details">
        <div>
          <strong>Ingredient list</strong>
          <ul>
            {recipe.recipe_ingredients.map((row) => (
              <li key={row.id}>
                {row.quantity != null ? `${row.quantity} ${row.unit || ""} ` : ""}
                {row.ingredient.name}
                {row.is_optional ? " (optional)" : ""}
              </li>
            ))}
          </ul>
        </div>

        <div>
          <strong>Instructions</strong>
          <p>{recipe.instructions || "No structured instructions available."}</p>
        </div>
      </div>

      {nutritionEstimate?.note ? (
        <p className="helper-text">{nutritionEstimate.note}</p>
      ) : null}
    </article>
  );
}

export function RecipeGeneratorPanel({
  recipes,
  loading,
  error,
  unavailable,
  onGenerate,
}) {
  return (
    <SectionCard
      title="4. Recipe Suggestions"
      subtitle="Generate demo-ready suggestions from the existing recipe catalog and current pantry overlap."
      actions={
        <button className="button" disabled={loading} onClick={onGenerate} type="button">
          {loading ? "Generating..." : "Generate Recipes"}
        </button>
      }
    >
      {unavailable ? (
        <InlineMessage tone="warning">
          `/recipes/generate` is not available on this branch. This UI uses the current recipe catalog
          and pantry overlap to simulate recipe generation for the demo.
        </InlineMessage>
      ) : null}

      {error ? <InlineMessage tone="error">{error}</InlineMessage> : null}

      {!loading && recipes.length === 0 ? (
        <div className="empty-state">
          No recipe suggestions yet. Load pantry items first, then generate suggestions.
        </div>
      ) : null}

      <div className="recipe-grid">
        {recipes.map((item) => (
          <RecipeCard item={item} key={item.recipe.id} />
        ))}
      </div>
    </SectionCard>
  );
}
