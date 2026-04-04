import { useEffect, useState } from "react";

import { detectIngredientsFromImage } from "./api/detection";
import { fetchIngredients } from "./api/ingredients";
import {
  applyRecipeToPantry,
  consumePantryItem,
  deletePantryItem,
  fetchPantryItems,
  ingestPantry,
  updatePantryItem,
} from "./api/pantry";
import { generateRecipes } from "./api/recipes";
import { ApiError } from "./api/client";
import { SectionCard } from "./components/common/SectionCard";
import { DetectionReviewPanel } from "./components/detection/DetectionReviewPanel";
import { PantryDashboard } from "./components/pantry/PantryDashboard";
import { RecipeGeneratorPanel } from "./components/recipes/RecipeGeneratorPanel";
import { ImageUploadPanel } from "./components/upload/ImageUploadPanel";

const WIZARD_STEPS = [
  { id: "upload", label: "Upload", title: "Add a pantry photo or sample detections." },
  { id: "review", label: "Review", title: "Confirm the ingredients you want to save." },
  { id: "pantry", label: "Pantry", title: "Review active pantry state and make quick fixes." },
  { id: "recipes", label: "Recipes", title: "Generate recipes from the confirmed pantry." },
];

function createDetectionRow(overrides = {}) {
  return {
    id: crypto.randomUUID(),
    detected_name: "",
    corrected_name: "",
    quantity: "",
    unit: "",
    detected_confidence: "",
    ...overrides,
  };
}

function toOptionalNumber(value) {
  if (value === "" || value == null) {
    return null;
  }
  const parsed = Number(value);
  return Number.isNaN(parsed) ? null : parsed;
}

export default function App() {
  const [userId, setUserId] = useState("demo-user");
  const [ingredients, setIngredients] = useState([]);
  const [pantryItems, setPantryItems] = useState([]);
  const [includeInactive, setIncludeInactive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [detectionRows, setDetectionRows] = useState([]);
  const [ingestResult, setIngestResult] = useState(null);
  const [detectionFallbackMode, setDetectionFallbackMode] = useState(false);
  const [detectionError, setDetectionError] = useState("");
  const [pantryError, setPantryError] = useState("");
  const [recipeError, setRecipeError] = useState("");
  const [recipeActionMessage, setRecipeActionMessage] = useState("");
  const [isDetecting, setIsDetecting] = useState(false);
  const [isSubmittingPantry, setIsSubmittingPantry] = useState(false);
  const [isLoadingPantry, setIsLoadingPantry] = useState(false);
  const [busyPantryItemId, setBusyPantryItemId] = useState(null);
  const [busyRecipeTitle, setBusyRecipeTitle] = useState("");
  const [recipeItems, setRecipeItems] = useState([]);
  const [recipeGenerationMethod, setRecipeGenerationMethod] = useState("");
  const [priorityIngredients, setPriorityIngredients] = useState([]);
  const [isGeneratingRecipes, setIsGeneratingRecipes] = useState(false);
  const [editingById, setEditingById] = useState({});
  const [consumeById, setConsumeById] = useState({});
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    loadIngredients();
  }, []);

  useEffect(() => {
    if (userId) {
      loadPantry();
    }
  }, [userId, includeInactive]);

  useEffect(() => {
    if (!selectedFile) {
      setPreviewUrl("");
      return undefined;
    }

    const objectUrl = URL.createObjectURL(selectedFile);
    setPreviewUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [selectedFile]);

  async function loadIngredients() {
    try {
      const data = await fetchIngredients();
      setIngredients(data);
    } catch (error) {
      console.error(error);
    }
  }

  async function loadPantry() {
    setIsLoadingPantry(true);
    setPantryError("");
    try {
      const data = await fetchPantryItems(userId, includeInactive);
      setPantryItems(data);
      setEditingById(
        Object.fromEntries(
          data.map((item) => [
            item.id,
            {
              quantity: item.quantity ?? "",
              unit: item.unit ?? "",
            },
          ]),
        ),
      );
    } catch (error) {
      setPantryError(error.message || "Failed to load pantry items.");
    } finally {
      setIsLoadingPantry(false);
    }
  }

  async function handleDetect() {
    if (!selectedFile) {
      return;
    }

    setIsDetecting(true);
    setDetectionError("");
    try {
      const response = await detectIngredientsFromImage(selectedFile);
      const ingredientsFromResponse = response.ingredients || response.detected_ingredients || [];
      setDetectionRows(
        ingredientsFromResponse.map((item) =>
          createDetectionRow({
            detected_name: item.normalized_name || item.raw_label || item.detected_name || "",
            quantity: item.quantity_hint ?? "",
            unit: item.unit_hint ?? "",
            detected_confidence: item.confidence ?? "",
          }),
        ),
      );
      setDetectionFallbackMode(false);
      setCurrentStep(1);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        setDetectionFallbackMode(true);
        setDetectionError("");
        return;
      }

      setDetectionFallbackMode(true);
      setDetectionError(error.message || "Image detection failed.");
    } finally {
      setIsDetecting(false);
    }
  }

  function loadSampleDetections() {
    setDetectionRows([
      createDetectionRow({
        detected_name: "spinach",
        corrected_name: "Spinach",
        quantity: "120",
        unit: "g",
        detected_confidence: "0.96",
      }),
      createDetectionRow({
        detected_name: "egg",
        corrected_name: "Egg",
        quantity: "6",
        unit: "count",
        detected_confidence: "0.91",
      }),
      createDetectionRow({
        detected_name: "shredded cheese",
        corrected_name: "Cheese",
        quantity: "80",
        unit: "g",
        detected_confidence: "0.74",
      }),
    ]);
    setDetectionFallbackMode(true);
    setDetectionError("");
    setCurrentStep(1);
  }

  function handleDetectionRowChange(rowId, field, value) {
    setDetectionRows((current) =>
      current.map((row) => (row.id === rowId ? { ...row, [field]: value } : row)),
    );
  }

  function handleAddDetectionRow(overrides = {}) {
    setDetectionRows((current) => [...current, createDetectionRow(overrides)]);
  }

  function handleRemoveDetectionRow(rowId) {
    setDetectionRows((current) => current.filter((row) => row.id !== rowId));
  }

  async function handleIngestPantry() {
    setIsSubmittingPantry(true);
    setDetectionError("");
    try {
      const filteredRows = detectionRows.filter((row) => row.detected_name.trim());
      const payload = {
        user_id: userId,
        detected_ingredients: filteredRows.map((row) => ({
          detected_name: row.detected_name.trim(),
          quantity: toOptionalNumber(row.quantity),
          unit: row.unit || null,
          detected_confidence: toOptionalNumber(row.detected_confidence),
        })),
        manual_corrections: filteredRows
          .filter(
            (row) =>
              row.corrected_name &&
              row.corrected_name.trim() &&
              row.corrected_name.trim() !== row.detected_name.trim(),
          )
          .map((row) => ({
            detected_name: row.detected_name.trim(),
            corrected_name: row.corrected_name.trim(),
          })),
      };

      const response = await ingestPantry(payload);
      setIngestResult(response);
      setPantryItems(response.items);
      setEditingById(
        Object.fromEntries(
          response.items.map((item) => [
            item.id,
            {
              quantity: item.quantity ?? "",
              unit: item.unit ?? "",
            },
          ]),
        ),
      );
      setRecipeItems([]);
      setRecipeGenerationMethod("");
      setPriorityIngredients([]);
      setCurrentStep(2);
    } catch (error) {
      setDetectionError(error.message || "Failed to persist pantry items.");
    } finally {
      setIsSubmittingPantry(false);
    }
  }

  function handleFileChange(event) {
    const file = event.target.files?.[0];
    setSelectedFile(file || null);
  }

  function handleEditChange(itemId, field, value) {
    setEditingById((current) => ({
      ...current,
      [itemId]: {
        ...(current[itemId] || {}),
        [field]: value,
      },
    }));
  }

  function handleConsumeChange(itemId, value) {
    setConsumeById((current) => ({
      ...current,
      [itemId]: value,
    }));
  }

  async function withPantryRefresh(itemId, action) {
    setBusyPantryItemId(itemId);
    setPantryError("");
    try {
      await action();
      await loadPantry();
    } catch (error) {
      setPantryError(error.message || "Pantry action failed.");
    } finally {
      setBusyPantryItemId(null);
    }
  }

  async function handleSavePantryItem(itemId) {
    const edit = editingById[itemId] || {};
    await withPantryRefresh(itemId, () =>
      updatePantryItem(itemId, {
        quantity: toOptionalNumber(edit.quantity),
        unit: edit.unit || null,
      }),
    );
  }

  async function handleConsumePantryItem(itemId) {
    const amount = toOptionalNumber(consumeById[itemId]);
    if (!amount) {
      return;
    }

    await withPantryRefresh(itemId, async () => {
      await consumePantryItem(itemId, amount);
      setConsumeById((current) => ({ ...current, [itemId]: "" }));
    });
  }

  async function handleDeletePantryItem(itemId) {
    await withPantryRefresh(itemId, () => deletePantryItem(itemId));
  }

  async function handleToggleFalsePositive(item) {
    await withPantryRefresh(item.id, () =>
      updatePantryItem(item.id, {
        is_false_positive: !item.is_false_positive,
      }),
    );
  }

  async function handleGenerateRecipes() {
    const activePantryItems = pantryItems.filter(
      (item) => !item.is_archived && !item.is_false_positive,
    );
    if (activePantryItems.length === 0) {
      setRecipeItems([]);
      setPriorityIngredients([]);
      setRecipeGenerationMethod("");
      setRecipeError("Load pantry items first, then generate recipe suggestions.");
      return;
    }

    setIsGeneratingRecipes(true);
    setRecipeError("");
    setRecipeActionMessage("");
    try {
      const today = new Date();
      const payload = {
        ingredients: activePantryItems.map((item) => ({
          name: item.ingredient.name,
          quantity: item.quantity,
          unit: item.unit || item.ingredient.standard_unit || null,
          priority: item.priority_bucket,
          days_until_expiry: item.estimated_expiry_date
            ? Math.max(
                0,
                Math.ceil(
                  (new Date(`${item.estimated_expiry_date}T00:00:00`) - today) /
                    (1000 * 60 * 60 * 24),
                ),
              )
            : null,
        })),
        max_recipes: 4,
        servings: 2,
      };
      const response = await generateRecipes(payload);
      setRecipeItems(response.recipes || []);
      setRecipeGenerationMethod(response.generation_method || "");
      setPriorityIngredients(response.priority_ingredients || []);
      setCurrentStep(3);
    } catch (error) {
      setRecipeError(error.message || "Failed to generate recipes.");
    } finally {
      setIsGeneratingRecipes(false);
    }
  }

  async function handleChooseRecipe(recipe) {
    setBusyRecipeTitle(recipe.title);
    setRecipeError("");
    setRecipeActionMessage("");
    try {
      const response = await applyRecipeToPantry({
        user_id: userId,
        recipe_title: recipe.title,
        ingredients: recipe.ingredients.map((ingredient) => ({
          name: ingredient.name,
          quantity: ingredient.quantity || null,
          available_in_pantry: ingredient.available_in_pantry,
        })),
      });

      if (includeInactive) {
        await loadPantry();
      } else {
        setPantryItems(response.items);
        setEditingById(
          Object.fromEntries(
            response.items.map((item) => [
              item.id,
              {
                quantity: item.quantity ?? "",
                unit: item.unit ?? "",
              },
            ]),
          ),
        );
      }

      const appliedCount = response.applied_deductions.length;
      const skippedCount = response.skipped_ingredients.length;
      const messageParts = [`Applied "${response.recipe_title}" to the pantry.`];
      messageParts.push(
        appliedCount === 1
          ? "1 ingredient was deducted."
          : `${appliedCount} ingredients were deducted.`,
      );
      if (skippedCount) {
        messageParts.push(
          skippedCount === 1
            ? "1 ingredient was skipped because its quantity could not be matched safely."
            : `${skippedCount} ingredients were skipped because their quantities could not be matched safely.`,
        );
        messageParts.push(
          `Skipped: ${response.skipped_ingredients.map((ingredient) => ingredient.ingredient_name).join(", ")}.`,
        );
      }
      setRecipeActionMessage(messageParts.join(" "));
    } catch (error) {
      setRecipeError(error.message || "Failed to apply the selected recipe.");
    } finally {
      setBusyRecipeTitle("");
    }
  }

  const activePantryItems = pantryItems.filter(
    (item) => !item.is_archived && !item.is_false_positive,
  );
  const stepId = WIZARD_STEPS[currentStep].id;

  function goToStep(index) {
    setCurrentStep(index);
  }

  function nextFromPantry() {
    if (activePantryItems.length === 0) {
      setPantryError("Add or keep at least one active pantry item before moving on.");
      return;
    }
    setCurrentStep(3);
  }

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Pantry to Plate</p>
          <h1>AI-powered recipe generator</h1>
          <p className="hero__copy">
            Scan, confirm, and cook from what is already in your pantry.
          </p>
        </div>
      </header>

      <main className="wizard-layout">
        <section className="wizard-rail">
          <div className="wizard-steps">
            {WIZARD_STEPS.map((step, index) => {
              const state =
                index === currentStep ? "current" : index < currentStep ? "done" : "upcoming";
              return (
                <button
                  className={`wizard-step wizard-step--${state}`}
                  key={step.id}
                  onClick={() => goToStep(index)}
                  type="button"
                >
                  <span className="wizard-step__index">{index + 1}</span>
                  <span>
                    <strong>{step.label}</strong>
                    <small>{step.title}</small>
                  </span>
                </button>
              );
            })}
          </div>

          <SectionCard title="Progress" subtitle="One screen at a time.">
            <div className="wizard-summary">
              <div>
                <strong>{detectionRows.length}</strong>
                <span>detections ready</span>
              </div>
              <div>
                <strong>{activePantryItems.length}</strong>
                <span>active pantry items</span>
              </div>
              <div>
                <strong>{recipeItems.length}</strong>
                <span>recipe results</span>
              </div>
            </div>
          </SectionCard>
        </section>

        <section className="wizard-screen">
          {stepId === "upload" ? (
            <>
              <ImageUploadPanel
                error={detectionError}
                fallbackMode={detectionFallbackMode}
                file={selectedFile}
                isDetecting={isDetecting}
                onDetect={handleDetect}
                onFileChange={handleFileChange}
                onLoadSample={loadSampleDetections}
                previewUrl={previewUrl}
              />
            </>
          ) : null}

          {stepId === "review" ? (
            <>
              <DetectionReviewPanel
                error={detectionError}
                ingredients={ingredients}
                ingestResult={ingestResult}
                isSubmitting={isSubmittingPantry}
                onAddRow={handleAddDetectionRow}
                onChangeRow={handleDetectionRowChange}
                onRemoveRow={handleRemoveDetectionRow}
                onSubmit={handleIngestPantry}
                rows={detectionRows}
              />
              <div className="wizard-nav">
                <button className="button--secondary" onClick={() => goToStep(0)} type="button">
                  Back
                </button>
                <button
                  className="button"
                  disabled={detectionRows.length === 0 || isSubmittingPantry}
                  onClick={handleIngestPantry}
                  type="button"
                >
                  {isSubmittingPantry ? "Saving..." : "Confirm and Continue"}
                </button>
              </div>
            </>
          ) : null}

          {stepId === "pantry" ? (
            <>
              <PantryDashboard
                busyItemId={busyPantryItemId}
                consumeById={consumeById}
                editingById={editingById}
                error={pantryError}
                includeInactive={includeInactive}
                items={pantryItems}
                loading={isLoadingPantry}
                onConsume={handleConsumePantryItem}
                onConsumeChange={handleConsumeChange}
                onDelete={handleDeletePantryItem}
                onEditChange={handleEditChange}
                onRefresh={loadPantry}
                onSave={handleSavePantryItem}
                onToggleFalsePositive={handleToggleFalsePositive}
                onToggleIncludeInactive={setIncludeInactive}
              />
              <div className="wizard-nav">
                <button className="button--secondary" onClick={() => goToStep(1)} type="button">
                  Back
                </button>
                <button className="button" onClick={nextFromPantry} type="button">
                  Continue to Recipes
                </button>
              </div>
            </>
          ) : null}

          {stepId === "recipes" ? (
            <>
              <RecipeGeneratorPanel
                actionMessage={recipeActionMessage}
                choosingRecipeTitle={busyRecipeTitle}
                error={recipeError}
                generationMethod={recipeGenerationMethod}
                loading={isGeneratingRecipes}
                onChooseRecipe={handleChooseRecipe}
                onGenerate={handleGenerateRecipes}
                priorityIngredients={priorityIngredients}
                recipes={recipeItems}
              />
              <div className="wizard-nav">
                <button className="button--secondary" onClick={() => goToStep(2)} type="button">
                  Back
                </button>
              </div>
            </>
          ) : null}
        </section>
      </main>
    </div>
  );
}
