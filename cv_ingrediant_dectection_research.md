# Ingredient Detection from Fridge Images: Approach Evaluation

## Overview

This document compares practical computer vision approaches for detecting ingredients from fridge images.

The goal is to choose a first implementation path that is accurate enough to be useful, affordable enough to test, and simple enough to ship without creating unnecessary infrastructure burden.

This is intentionally written like an engineering decision note, not a research paper.

---

## Problem statement

We want to detect ingredients visible in fridge photos.

Examples:

- milk carton
- eggs
- tomatoes
- spinach
- yogurt cup
- onion
- cheese block
- sauce bottle

The challenge is that fridge images are messy in the real world:

- items are partially hidden
- packaging varies a lot
- lighting is inconsistent
- objects overlap
- some ingredients are in transparent or reflective containers
- some items are not “standard” object detection classes

Because of that, the best solution is not always the one with the most ML sophistication. It is the one that gives strong enough results with manageable effort.

---

## Acceptance Criteria

- [ ] At least 2 approaches are evaluated
- [ ] Tradeoffs across accuracy, cost, and complexity are documented
- [ ] Sample test results or expected outputs are analyzed
- [ ] Final approach is recommended for implementation

---

## Approaches evaluated

This comparison focuses on two realistic first options:

1. **Pretrained object detection model** using YOLO-style detection
2. **API-based multimodal vision model** using Gemini Vision

I also include one practical extension at the end: an optional hybrid path.

---

## Approach 1: Pretrained object detection with YOLO

### What it is

YOLO is a fast object detection family that returns:

- bounding boxes
- class labels
- confidence scores

Ultralytics documents YOLOv8 as supporting detection, segmentation, classification, pose, and export to deployment formats such as ONNX and TensorRT. Their object detection docs also note that pretrained detect models are commonly trained on COCO-style datasets. citeturn916218view2turn104412view0

### Why it is attractive

- fast inference
- well known ecosystem
- can run locally or on your own backend
- good control over latency and deployment
- easy to integrate into a Python service

### Main limitation for this use case

A standard pretrained detector usually works best on its trained label set. That becomes a problem for fridge images because many ingredient categories are not represented in a useful way in generic detection datasets.

Examples:

- a model may detect `bottle` but not `soy sauce`
- it may detect `apple` but miss `spinach`
- it may detect a `container` instead of the ingredient inside it

So a plain off-the-shelf YOLO detector is usually a **good baseline**, but not always a complete product solution for ingredients.

### Feasibility summary

**Best case:** good at finding visually obvious packaged or familiar items.

**Weak case:** struggles with niche ingredients, clutter, heavy occlusion, and fine-grained food labels unless retrained.

---

## Approach 2: API-based multimodal vision model with Gemini Vision

### What it is

Gemini is a multimodal model family that can understand images and answer prompts about them. Google documents image understanding support for classification, visual question answering, object detection, and segmentation, and Vertex AI supports supplying images either inline or from GCS. Supported image MIME types include PNG and JPEG, with GCS-based file inputs supported up to larger sizes than inline uploads. citeturn916218view1turn916218view4

### Why it is attractive

- no model training required to get started
- flexible prompting
- can return structured JSON if prompted correctly
- handles open-ended categories better than fixed-label detectors
- easy fit for early prototyping, especially if the image is already in GCS

### Main limitation for this use case

- per-request cost matters at scale
- response consistency can vary if prompts are loose
- bounding box quality may not match specialized detectors in all cases
- vendor dependency is higher than with self-hosted detection

### Feasibility summary

**Best case:** great for quickly answering “what ingredients are visible in this fridge image?” without building a custom dataset first.

**Weak case:** less predictable for pixel-level precision and may require prompt engineering, output validation, and retries for production consistency.

---

## Head-to-head comparison

| Dimension | YOLO-style detector | Gemini Vision |
|---|---|---|
| Core strength | Fast object localization | Flexible multimodal understanding |
| Setup effort | Medium | Low |
| Need training? | Usually yes for good ingredient coverage | No for initial prototype |
| Bounding boxes | Native output | Possible, but less specialized |
| Fine-grained ingredient names | Weak unless retrained | Better zero-shot behavior |
| Latency control | Strong | Depends on API and network |
| Infra ownership | You manage model serving | Vendor-managed |
| Per-request cost | Low after deployment | Ongoing API cost |
| Best use case | Repeated, high-volume inference with fixed labels | Fast prototyping and open-ended recognition |

---

## Accuracy discussion

### YOLO baseline accuracy expectation

For a fridge image, a generic pretrained YOLO model will likely do reasonably well on:

- bottles
- cans
- eggs in some cases
- apples, oranges, bananas if clearly visible
- packaged boxes or cartons

It will likely be weaker on:

- leafy greens
- herbs
- chopped ingredients in containers
- uncommon vegetables
- items partially hidden behind other objects
- brand-specific packaging where the ingredient identity is implicit

### Gemini Vision accuracy expectation

Gemini is likely to do better when the task is phrased semantically, for example:

> Identify all visible ingredients in this fridge image. Return a JSON array with ingredient name, confidence, and whether the item is clearly visible or partially occluded.

That kind of prompt lets the model reason over packaging, context, and broader world knowledge. For example, it may infer `milk`, `spinach`, or `yogurt` even when the object is not a clean COCO-style detection class.

That said, semantic recognition does not guarantee perfect grounding. The model may guess wrong when labels are tiny, packaging is ambiguous, or two similar items are present.

---

## Cost discussion

### YOLO

Cost profile:

- engineering cost is front-loaded
- inference cost is mainly compute you host yourself
- marginal per-image cost becomes low once deployed

This is a better shape if the product will eventually process many images per day.

### Gemini Vision

Gemini Developer API offers free and paid tiers, and paid usage is token-based. Google also notes that Batch API can reduce cost for eligible workloads, and Vertex AI / Gemini pricing depends on model family and token usage. citeturn916218view0turn496131search6

Cost profile:

- very low upfront engineering effort
- recurring API cost per request
- cost can grow quickly if image volume is high or multiple calls are made per image

This is ideal for POCs and early product exploration, but it should be measured carefully before committing to scale.

---

## Ease of integration

### YOLO

Integration steps usually look like this:

1. receive image in backend
2. load model in inference service
3. run prediction
4. post-process detections
5. map class labels to app ingredient schema

This is straightforward in code, but operationally heavier because you own:

- model packaging
- runtime dependencies
- GPU or CPU sizing
- deployment and monitoring

### Gemini Vision

Integration steps are even simpler:

1. upload image to GCS
2. send image reference or bytes to Gemini
3. prompt for structured ingredient extraction
4. parse JSON response
5. store normalized ingredient list

This is especially clean because the ingestion POC already stores images in GCS, and Vertex AI supports using GCS-based image inputs directly. citeturn916218view4

---

## Deployment constraints

### YOLO deployment constraints

- needs an inference service
- may need GPU if throughput targets are high
- better long-term control, but more DevOps work
- likely needs custom training data to get strong ingredient coverage

### Gemini Vision deployment constraints

- depends on external API availability and latency
- easier to deploy because there is almost no model-serving infrastructure
- needs guardrails around prompt consistency and output schema
- data governance and vendor policy review may be needed

---

## Sample expected outputs

Below is a realistic example using a sample fridge image containing:

- milk carton
- eggs
- spinach bag
- tomatoes
- yogurt cups
- hot sauce bottle

### Expected YOLO-style output

```json
[
  {"label": "bottle", "confidence": 0.89, "bbox": [412, 122, 486, 401]},
  {"label": "egg", "confidence": 0.72, "bbox": [138, 322, 240, 390]},
  {"label": "tomato", "confidence": 0.68, "bbox": [262, 291, 341, 354]},
  {"label": "carton", "confidence": 0.64, "bbox": [58, 90, 149, 335]}
]
```

### Likely YOLO interpretation

What is good:

- gets positions and boxes
- useful for localization

What may be missing:

- may output `carton` instead of `milk`
- may miss `spinach`
- may not identify `yogurt cups` correctly
- ingredient names may stay generic

### Expected Gemini Vision output

```json
{
  "ingredients": [
    {"name": "milk", "confidence": "high", "visibility": "clear"},
    {"name": "eggs", "confidence": "medium", "visibility": "partial"},
    {"name": "spinach", "confidence": "medium", "visibility": "clear"},
    {"name": "tomatoes", "confidence": "high", "visibility": "clear"},
    {"name": "yogurt", "confidence": "medium", "visibility": "clear"},
    {"name": "hot sauce", "confidence": "medium", "visibility": "clear"}
  ]
}
```

### Likely Gemini interpretation

What is good:

- better ingredient-level naming
- better early-stage product usefulness
- easier to connect to recipe suggestion workflows

What may go wrong:

- confidence is not calibrated like detector probability
- can hallucinate a plausible item if packaging is ambiguous
- may not provide exact coordinates if you need localization later

---

## Tradeoff summary

### YOLO wins when

- you need low-latency local inference
- bounding boxes matter a lot
- image volume is high
- you are willing to collect or label a custom ingredient dataset
- you want lower long-term inference cost

### Gemini wins when

- you need to move fast
- you want decent semantic ingredient extraction without training
- you already use GCS and Google Cloud services
- image volume is still low to moderate
- product value depends more on “what is in the fridge?” than exact object coordinates

---

## Recommendation

### Recommended first implementation: **Gemini Vision for MVP**

I recommend starting with **Gemini Vision** as the first implementation path.

### Why

1. **Fastest time to value**  
   You can go from uploaded image to ingredient list without building a training dataset.

2. **Better fit for ingredient semantics**  
   The product needs ingredient understanding, not just generic object labels.

3. **Clean integration with the ingestion POC**  
   Images already land in GCS, and Gemini on Vertex AI supports image inputs from GCS. citeturn916218view4

4. **Lower initial engineering complexity**  
   No model serving stack is needed for the first version.

### Recommended guardrails

If Gemini is chosen first, add these from day one:

- force JSON output schema
- normalize ingredient names to canonical values
- keep confidence buckets simple: `high`, `medium`, `low`
- log prompt, raw response, and normalized output
- manually review a small evaluation set of fridge images

---

## Follow-up recommendation

### Best medium-term path: **Hybrid approach**

After MVP validation, the strongest architecture may be:

- **Gemini Vision** for semantic ingredient extraction
- **YOLO-based detector** later for localization-heavy use cases or cost optimization

That hybrid path makes sense if the product later needs:

- bounding boxes for UI overlays
- lower cost at scale
- offline or edge deployment
- tighter latency control

A practical roadmap would be:

### Phase 1
- build ingestion
- call Gemini on uploaded fridge images
- evaluate accuracy on real user samples

### Phase 2
- collect labeled fridge images
- measure recurring failure modes
- train or fine-tune a YOLO model on the most important ingredient classes

### Phase 3
- choose between hybrid inference or full migration depending on cost and accuracy

---

## Final decision

If the goal is to ship something useful quickly, start with **Gemini Vision**.

If the goal later becomes low-cost, high-volume, tightly controlled inference, invest in a **custom YOLO pipeline** after you have real image data and clear failure cases.

That is the lowest-risk engineering path.

---

## References

- Gemini supports multimodal image understanding tasks including classification, visual question answering, object detection, and segmentation. citeturn916218view1
- Vertex AI supports using image inputs from Google Cloud Storage and documents supported image formats and size limits. citeturn916218view4
- Gemini Developer API has free and paid tiers, and Batch API can reduce cost for some workloads. citeturn916218view0
- Ultralytics documents YOLOv8 as supporting multiple CV tasks and export paths such as ONNX and TensorRT. citeturn916218view2turn104412view0
- YOLO-World is an open-vocabulary extension built on YOLOv8 that can use custom prompts without full retraining, which may be interesting if the team wants a middle ground later.

