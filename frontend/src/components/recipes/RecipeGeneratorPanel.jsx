import { useState } from "react";

import { InlineMessage } from "../common/InlineMessage";
import { SectionCard } from "../common/SectionCard";
import { StatusBadge } from "../common/StatusBadge";

function RecipeCard({ item, onChooseRecipe, choosingRecipeTitle }) {
  const [isOpen, setIsOpen] = useState(false);
  const matched = item.ingredients.filter((ingredient) => ingredient.available_in_pantry);
  const missing = item.ingredients.filter((ingredient) => !ingredient.available_in_pantry);
  const urgentMatches = matched.filter((ingredient) => ingredient.is_priority);
  const priorityLabel = urgentMatches.length ? "HIGH" : missing.length ? "MEDIUM" : "LOW";
  const isChoosing = choosingRecipeTitle === item.title;

  return (
    <article className="recipe-accordion">
      <button
        className="recipe-accordion__summary"
        onClick={() => setIsOpen((current) => !current)}
        type="button"
      >
        <div className="recipe-accordion__titleblock">
          <h3>{item.title}</h3>
          <p>
            {item.pantry_coverage_percent}% pantry coverage
            {item.estimated_cook_time_minutes
              ? ` • ${item.estimated_cook_time_minutes} min`
              : ""}
            {item.servings ? ` • ${item.servings} servings` : ""}
          </p>
        </div>
        <div className="recipe-accordion__meta">
          <StatusBadge label={priorityLabel} />
          <span className="recipe-accordion__toggle">
            {isOpen ? "Hide details" : "View details"}
          </span>
        </div>
      </button>

      {isOpen ? (
        <div className="recipe-accordion__content">
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

          <div className="button-row">
            <button
              className="button"
              disabled={isChoosing}
              onClick={() => onChooseRecipe(item)}
              type="button"
            >
              {isChoosing ? "Applying..." : "Choose This Recipe"}
            </button>
          </div>
        </div>
      ) : null}
    </article>
  );
}

export function RecipeGeneratorPanel({
  recipes,
  loading,
  error,
  actionMessage,
  choosingRecipeTitle,
  onGenerate,
  onChooseRecipe,
}) {
  return (
    <SectionCard
      title="3. Recipe Suggestions"
      subtitle="Generate live suggestions from the current pantry state."
      actions={
        <button className="button" disabled={loading} onClick={onGenerate} type="button">
          {loading ? "Generating..." : "Generate Recipes"}
        </button>
      }
    >
      {error ? <InlineMessage tone="error">{error}</InlineMessage> : null}
      {actionMessage ? <InlineMessage tone="info">{actionMessage}</InlineMessage> : null}

      {!loading && recipes.length > 0 ? (
        <InlineMessage tone="info">
          Showing {recipes.length} recipe{recipes.length === 1 ? "" : "s"}.
        </InlineMessage>
      ) : null}

      {!loading && recipes.length === 0 ? (
        <div className="empty-state">
          No recipe suggestions yet. Load pantry items first, then generate suggestions.
        </div>
      ) : null}

      <div className="recipe-grid">
        {recipes.map((item) => (
          <RecipeCard
            choosingRecipeTitle={choosingRecipeTitle}
            item={item}
            key={`${item.title}-${item.estimated_cook_time_minutes}`}
            onChooseRecipe={onChooseRecipe}
          />
        ))}
      </div>
    </SectionCard>
  );
}
