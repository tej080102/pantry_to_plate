import { useEffect, useState } from "react";

import { detectIngredientsFromImage } from "./api/detection";
import { fetchIngredients } from "./api/ingredients";
import {
  archiveExpiredPantry,
  consumePantryItem,
  deletePantryItem,
  fetchPantryItems,
  ingestPantry,
  updatePantryItem,
} from "./api/pantry";
import { generateRecipes } from "./api/recipes";
import { ApiError, API_BASE_URL } from "./api/client";
import { InlineMessage } from "./components/common/InlineMessage";
import { SectionCard } from "./components/common/SectionCard";
import { DetectionReviewPanel } from "./components/detection/DetectionReviewPanel";
import { PantryDashboard } from "./components/pantry/PantryDashboard";
import { RecipeGeneratorPanel } from "./components/recipes/RecipeGeneratorPanel";
import { ImageUploadPanel } from "./components/upload/ImageUploadPanel";

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
  const [isDetecting, setIsDetecting] = useState(false);
  const [isSubmittingPantry, setIsSubmittingPantry] = useState(false);
  const [isLoadingPantry, setIsLoadingPantry] = useState(false);
  const [busyPantryItemId, setBusyPantryItemId] = useState(null);
  const [recipeItems, setRecipeItems] = useState([]);
  const [recipeGenerationMethod, setRecipeGenerationMethod] = useState("");
  const [priorityIngredients, setPriorityIngredients] = useState([]);
  const [isGeneratingRecipes, setIsGeneratingRecipes] = useState(false);
  const [editingById, setEditingById] = useState({});
  const [consumeById, setConsumeById] = useState({});

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
  }

  function handleDetectionRowChange(rowId, field, value) {
    setDetectionRows((current) =>
      current.map((row) => (row.id === rowId ? { ...row, [field]: value } : row)),
    );
  }

  function handleAddDetectionRow() {
    setDetectionRows((current) => [...current, createDetectionRow()]);
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

  async function handleArchiveExpired() {
    setPantryError("");
    try {
      const result = await archiveExpiredPantry(userId);
      await loadPantry();
      if (!result.archived_count) {
        setPantryError("No expired pantry items needed archiving.");
      }
    } catch (error) {
      setPantryError(error.message || "Failed to archive expired items.");
    }
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
    } catch (error) {
      setRecipeError(error.message || "Failed to generate recipes.");
    } finally {
      setIsGeneratingRecipes(false);
    }
  }

  const unmatchedItems = ingestResult?.unmatched_detected_ingredients || [];
  const inactiveItems = pantryItems.filter((item) => item.is_archived || item.is_false_positive);

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Pantry to Plate</p>
          <h1>AI-powered pantry state and recipe demo</h1>
          <p className="hero__copy">
            Upload a pantry photo when the backend supports detection, review ingredients, build
            pantry state, and explore spoilage-driven recipe suggestions from the live catalog.
          </p>
        </div>

        <div className="hero__sidecar">
          <label>
            Demo user
            <input onChange={(event) => setUserId(event.target.value)} value={userId} />
          </label>
          <div className="hero__meta">
            <span>Backend URL</span>
            <code>{API_BASE_URL}</code>
          </div>
        </div>
      </header>

      <main className="app-grid">
        <div className="main-column">
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

          <PantryDashboard
            busyItemId={busyPantryItemId}
            consumeById={consumeById}
            editingById={editingById}
            error={pantryError}
            includeInactive={includeInactive}
            items={pantryItems}
            loading={isLoadingPantry}
            onArchiveExpired={handleArchiveExpired}
            onConsume={handleConsumePantryItem}
            onConsumeChange={handleConsumeChange}
            onDelete={handleDeletePantryItem}
            onEditChange={handleEditChange}
            onRefresh={loadPantry}
            onSave={handleSavePantryItem}
            onToggleFalsePositive={handleToggleFalsePositive}
            onToggleIncludeInactive={setIncludeInactive}
          />

          <RecipeGeneratorPanel
            error={recipeError}
            generationMethod={recipeGenerationMethod}
            loading={isGeneratingRecipes}
            onGenerate={handleGenerateRecipes}
            priorityIngredients={priorityIngredients}
            recipes={recipeItems}
          />
        </div>

        <aside className="side-column">
          <SectionCard
            title="Demo Diagnostics"
            subtitle="Compact visibility into unmatched detections and inactive pantry items."
          >
            {unmatchedItems.length ? (
              <div className="debug-block">
                <h3>Unmatched detections</h3>
                <ul className="debug-list">
                  {unmatchedItems.map((item) => (
                    <li key={`${item.detected_name}-${item.reason}`}>
                      <strong>{item.detected_name}</strong>
                      <span>{item.reason}</span>
                      <span>
                        {item.quantity != null ? `${item.quantity} ${item.unit || ""}` : "No quantity"}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <div className="empty-mini">No unmatched detections from the latest pantry ingest.</div>
            )}

            {inactiveItems.length ? (
              <div className="debug-block">
                <h3>Inactive pantry items</h3>
                <ul className="debug-list">
                  {inactiveItems.map((item) => (
                    <li key={item.id}>
                      <strong>{item.ingredient.name}</strong>
                      <span>{item.is_false_positive ? "Dismissed" : "Archived"}</span>
                      <span>{item.source_detected_name || "No detected name"}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <div className="empty-mini">
                No archived or false-positive items are visible for this user.
              </div>
            )}
          </SectionCard>

          <SectionCard
            title="How This Branch Works"
            subtitle="Real backend integration, with safe fallbacks where APIs are not implemented yet."
          >
            <ul className="bullet-list">
              <li>`/ingredients` is used for canonical ingredient suggestions.</li>
              <li>`/pantry/*` powers ingest, retrieval, update, consume, dismiss, and archive flows.</li>
              <li>`/recipes/generate` turns the live pantry state into recipe suggestions.</li>
              <li>`/perception/detect` is attempted first; if Gemini detection fails, the UI falls back to manual/sample detections.</li>
            </ul>

            <InlineMessage tone="info">
              The frontend stays usable even when perception is temporarily unavailable.
            </InlineMessage>
          </SectionCard>
        </aside>
      </main>
    </div>
  );
}
