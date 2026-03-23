# LLM Evaluation for Recipe Generation in Sprout

## Task
Research and evaluate different large language model approaches for generating recipes based on available ingredients, with a focus on grounded generation using structured inputs and strict JSON outputs.

---

## Objective

The goal of this evaluation is to identify an LLM approach that can generate useful, consistent, and grounded recipes from detected pantry ingredients while minimizing hallucinations. Since Sprout is designed as a recipe assistant that prioritizes expiring ingredients, the selected LLM must work well with structured inputs and reliably return machine-readable outputs that can be rendered directly in the application.

---

## Evaluation Criteria

The following criteria were used to compare candidate models:

1. **Grounded generation support**  
   Ability to generate recipes from structured ingredient and recipe-match inputs instead of relying on free-form prompting.

2. **JSON output reliability**  
   Ability to follow a strict output schema without extra prose or formatting errors.

3. **Hallucination risk**  
   Likelihood of inventing ingredients, quantities, or steps that are not supported by the provided context.

4. **Ease of integration**  
   Compatibility with FastAPI backend workflows, API-based deployment, and future Cloud Run hosting.

5. **Cost and deployment flexibility**  
   Support for low-cost experimentation and whether the model can be API-hosted or self-hosted.

---

## Evaluated LLM Options

### Option 1: Gemini Pro / Gemini API

**Approach**  
Use Gemini through an API-based workflow. The backend sends a structured recipe skeleton, prioritized ingredient list, and generation rules. The model returns a recipe in strict JSON format.

**Strengths**
- Easy API integration with Python backend
- Strong instruction following for structured prompts
- Good fit for fast prototyping and cloud-based workflows
- Can be combined with Gemini Vision in later stages for a more unified pipeline

**Weaknesses**
- Less control than a self-hosted model
- Output may still drift from schema if prompts are weak
- Cost can grow with repeated generation requests

**Use case fit**
- Very good for MVP and early demo stages
- Best when speed of implementation matters more than deep model customization

---

### Option 2: Llama 3 (self-hosted or managed container)

**Approach**  
Use Llama 3 in a self-hosted containerized setup. The backend sends structured recipe candidates plus pantry metadata and expects strict JSON output.

**Strengths**
- Greater control over deployment and tuning
- Can be hosted in a private environment
- Better long-term flexibility if the team wants to customize prompts, latency, or infrastructure

**Weaknesses**
- More operational overhead than an API-based model
- Requires more setup for serving, monitoring, and scaling
- JSON consistency may require stronger output constraints and validation layers

**Use case fit**
- Good for advanced stages of the project
- Better if the team wants tighter control over infrastructure and model behavior

---

## Comparison Summary

| Criterion                   | Gemini Pro                   | Llama 3                                                |
|-----------------------------|------------------------------|--------------------------------------------------------|
| Ease of setup               | High                         | Medium                                                 |
| JSON reliability            | High with prompt constraints | Medium, needs stronger validation                      |
| Grounded generation support | Strong                       | Strong                                                 |
| Hallucination control       | Good with structured input   | Good with structured input, but more validation needed |
| Deployment flexibility      | Medium                       | High                                                   |
| Best fit for current sprint | Yes                          | Possible, but heavier to operationalize                |

---

## Recommended Approach

For the current project stage, **Gemini Pro is the recommended primary option** for recipe generation, with **Llama 3 as a future extensible alternative**.

This recommendation is based on:
- faster integration into the current FastAPI backend
- lower implementation overhead
- better near-term support for structured prompting and JSON-style generation
- strong alignment with the project’s need for rapid prototype validation

---

## Prompt Strategy for Grounded Generation

To reduce hallucinations, the model should never be asked to invent a recipe from scratch. Instead, it should be guided using structured, constrained inputs.

### Input design

The prompt should include:
- detected ingredient list
- prioritized ingredients nearing expiry
- matched recipe skeleton from the database
- missing ingredient list
- explicit instruction to use only supported ingredients unless clearly marked as optional

### Prompt structure

1. **System instruction**
   - The model is a recipe generation assistant.
   - It must generate recipes only from provided ingredients and matched recipe context.
   - It must return valid JSON only.

2. **Context block**
   - Pantry ingredients with quantities if available
   - Priority ingredients flagged by spoilage rank
   - Candidate recipe title or skeleton from the database
   - Constraints such as dietary preference, missing ingredients, or serving size

3. **Output rules**
   - No markdown
   - No explanatory text outside JSON
   - Use provided ingredients first
   - Clearly separate required and optional ingredients
   - Do not invent unavailable core ingredients

### Example prompt idea

**System prompt**  
You are a recipe generation assistant. Generate a recipe only from the structured input provided. Prioritize ingredients marked as expiring soon. Return valid JSON only and do not include commentary.

**User prompt payload**
- Available ingredients: tomato, spinach, egg, cheese
- Priority ingredients: spinach, tomato
- Candidate recipe style: omelet or skillet dish
- Missing ingredients allowed: salt, pepper, oil
- Servings: 2

This strategy keeps the LLM grounded in factual application data rather than open-ended generation.

---

## JSON Output Format Design

The recipe output should follow a strict schema so that the frontend and backend can parse and display results reliably.

```json
{
  "title": "Spinach Tomato Omelet",
  "servings": 2,
  "estimated_cook_time_minutes": 15,
  "ingredients": [
    {
      "name": "spinach",
      "quantity": 2,
      "unit": "cups",
      "status": "available"
    },
    {
      "name": "tomato",
      "quantity": 1,
      "unit": "medium",
      "status": "available"
    },
    {
      "name": "egg",
      "quantity": 3,
      "unit": "count",
      "status": "available"
    },
    {
      "name": "salt",
      "quantity": 1,
      "unit": "tsp",
      "status": "optional_missing"
    }
  ],
  "steps": [
    "Whisk the eggs in a bowl.",
    "Cook spinach and tomato in a pan until softened.",
    "Add eggs and cook until set.",
    "Top with cheese and fold before serving."
  ],
  "priority_ingredients_used": ["spinach", "tomato"],
  "nutrition_notes": "High in protein and moderate in fiber."
}
```

### Why this format works
- It is easy to validate in the backend
- It prevents inconsistent free-form outputs
- It supports frontend rendering without extra parsing
- It preserves traceability of which ingredients were actually used

---

## Risks and Mitigation Strategies

### 1. Hallucinated ingredients
**Risk:** The model may introduce ingredients that are not in the pantry or recipe skeleton.  
**Mitigation:**  
- Use database-first recipe matching before the LLM step
- Pass only structured ingredient context
- Validate generated ingredients against allowed lists before returning results

### 2. Invalid JSON output
**Risk:** The model may return plain text, markdown, or malformed JSON.  
**Mitigation:**  
- Use strict prompt instructions that require JSON only
- Add backend schema validation with automatic rejection or retry
- Optionally wrap generation in a repair step if parsing fails

### 3. Loss of grounding
**Risk:** The model may drift into generic cooking advice instead of using the provided pantry state.  
**Mitigation:**  
- Include priority ingredient usage as an explicit requirement
- Penalize outputs that omit expiring ingredients
- Use a recipe skeleton from the database as the factual base

### 4. Overly generic or repetitive recipes
**Risk:** Outputs may be bland or repetitive across similar ingredient sets.  
**Mitigation:**  
- Provide recipe style hints from matched database recipes
- Vary candidate skeletons before generation
- Add lightweight ranking after generation

### 5. Cost or latency issues
**Risk:** API-based generation may become expensive or slow under repeated requests.  
**Mitigation:**  
- Cache common ingredient combinations
- Keep prompts compact and structured
- Consider Llama 3 as a future self-hosted alternative

---

## Final Recommendation

The preferred design is a **grounded hybrid pipeline**:

1. Detect pantry ingredients from the uploaded image  
2. Rank ingredients by spoilage priority  
3. Retrieve recipe candidates from the database  
4. Send structured context to the LLM  
5. Require strict JSON output  
6. Validate the result before returning it to the frontend

For implementation, **Gemini Pro is the best immediate choice**, while **Llama 3 remains a strong future option** if the project later prioritizes infrastructure control and self-hosted deployment.

---

## Acceptance Criteria Mapping

- **At least 2 LLM options are evaluated**  
  Yes — Gemini Pro and Llama 3 were evaluated.

- **Prompt strategy for grounded generation is defined**  
  Yes — structured input, database-first grounding, and JSON-only output rules were defined.

- **JSON output format is designed**  
  Yes — a full JSON schema example is included.

- **Risks such as hallucination are identified and mitigation strategies are proposed**  
  Yes — key risks and mitigations are documented in detail.

---
