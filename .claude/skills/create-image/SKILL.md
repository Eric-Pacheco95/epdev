---
name: create-image
description: Generate or edit images via Gemini MCP -- logos, slides, art, diagrams
---

# IDENTITY and PURPOSE

Image creation assistant. Select optimal Gemini model, craft high-quality prompts, deliver images via nanobanana MCP server.

# DISCOVERY

## Stage
BUILD

## Syntax
/create-image [--flash] [--ratio RATIO] <description or edit instruction>

## Parameters
- description: what to create or edit (required)
- --flash: use fast/cheap model for drafts (default: pro)
- --ratio: aspect ratio -- 1:1, 16:9, 9:16, 4:3, 3:4 (default: 16:9)

## Examples
- /create-image a minimalist logo for a crypto trading bot, dark theme
- /create-image --ratio 1:1 profile avatar with circuit board aesthetic
- /create-image --flash quick draft of a dashboard wireframe

## Chains
- Before: /create-keynote (generates slide images)
- After: (leaf -- delivers image)
- Full: /create-keynote > /create-image (per slide)

## Output Contract
- Input: image description or edit instruction
- Output: generated image file saved to output/images/ or specified path
- Side effects: writes image file to disk, may create conversation session

## autonomous_safe
false

# AVAILABLE TOOLS

| Tool | When to use |
|------|-------------|
| `gemini_generate_image` | Create a new image from scratch |
| `gemini_edit_image` | Modify an existing image (requires source image path) |
| `gemini_chat` | Iterative refinement, ask questions about images, multi-turn image work |
| `set_model` | Switch between `flash` (fast iteration) and `pro` (high quality) |
| `set_aspect_ratio` | Set default ratio for a session |
| `get_image_history` | Review previous generations in a session |
| `clear_conversation` | Reset session state |

# DECISION ROUTING

## Step 0: INPUT VALIDATION

- No input: print DISCOVERY as usage block, STOP
- Edit request without image path or prior session: ask which image to edit, STOP
- Prompt contains text-rendering demands (specific words in image): warn about text limitations, proceed
- Invalid --ratio value (not 1:1, 16:9, 9:16, 4:3, 3:4): print valid ratios and STOP
- Prompt < 5 words and no image context: ask Eric to describe the image more specifically before proceeding

## Step 1: Classify the request

| Category | Signal words / context | Route to |
|----------|----------------------|----------|
| **New image** | "create", "generate", "make", "design", "draw" | `gemini_generate_image` |
| **Edit existing** | "edit", "modify", "change", "update", "fix" + file path | `gemini_edit_image` |
| **Refine previous** | "try again", "more like", "less", "adjust", references a prior generation | `gemini_edit_image` with `last` or `history:N` |
| **Multi-image set** | "series", "set", "batch", "matching", "consistent style" | `gemini_generate_image` with `conversation_id` + `use_image_history: true` |
| **Describe/analyze** | "what is", "describe", "analyze" + image path | `gemini_chat` with image reference |

## Step 2: Select model quality

| Model | When to use | Cost tradeoff |
|-------|-------------|---------------|
| **pro** | Final deliverables, logos, keynote images, anything shared externally, photorealistic, complex scenes | Higher quality, slower, more expensive |
| **flash** | Quick iterations, drafts, testing prompts, exploration, simple graphics | Faster, cheaper, good enough for drafts |

**Default: `pro`** — Eric wants high quality. Only drop to `flash` if:
- Eric explicitly asks for a quick draft
- Iterating rapidly (3+ versions of the same concept)
- The image is a placeholder or internal-only

## Step 3: Select aspect ratio

| Ratio | Best for |
|-------|----------|
| `1:1` | Logos, icons, profile images, social media squares |
| `16:9` | Presentations, keynote slides, desktop wallpapers, YouTube thumbnails |
| `9:16` | Mobile wallpapers, Instagram stories, vertical posters |
| `4:3` | Classic presentation slides, photos |
| `3:4` | Portraits, book covers |
| `3:2` | Landscape photography |
| `2:3` | Portrait photography |
| `21:9` | Cinematic, ultrawide banners |

**Default: `16:9`** for general use. Infer from context when possible.

# PROMPT ENGINEERING

Before sending to Gemini, enhance the user's description into a high-quality image prompt:

1. **Be specific** — replace vague terms with concrete details (e.g., "nice background" -> "gradient from deep navy #0a1628 to midnight black")
2. **Specify style** — if not stated, infer from context (photorealistic, flat design, watercolor, 3D render, etc.)
3. **Include composition** — lighting, camera angle, depth of field, foreground/background
4. **Add quality markers** — "high detail", "professional quality", "clean lines", "sharp focus"
5. **Negative guidance** — mention what to avoid if relevant ("no text", "no watermarks", "no cluttered backgrounds")

Show Eric the enhanced prompt before generating so he can adjust if needed.

# SESSION MANAGEMENT

For multi-image work (keynote decks, brand assets, series):

1. Create a `conversation_id` based on the project (e.g., `keynote-jarvis-brain`, `brand-assets-v1`)
2. Enable `use_image_history: true` for style consistency across the set
3. Use `reference_images` to maintain character/style continuity
4. Track the session so edits and refinements carry forward

# OUTPUT

1. **Show the enhanced prompt** — let Eric approve or adjust before generating
2. **Generate the image** — save to a meaningful path:
   - Default: `C:/Users/ericp/Github/epdev/output/images/{descriptive-name}.png`
   - Keynote images: alongside the deck file
   - If Eric specifies a path, use that
3. **Display the result** — show the generated image inline
4. **Offer next steps**:
   - "Want me to refine this?" (edit mode)
   - "Want a different style?" (regenerate with new prompt)
   - "Want this in a different aspect ratio?" (regenerate)
   - "Want to create a matching set?" (session mode)

# INTEGRATION WITH OTHER SKILLS

- **`/create-keynote`**: When a keynote has `**Image**:` descriptions, this skill generates actual images for each slide
- **`/create-prd`**: Generate architecture diagrams or mockup visuals
- **`/visualize`**: For technical diagrams, prefer Mermaid via `/visualize`; for artistic/photorealistic visuals, use this skill

# EXAMPLES

**Simple request**: "make me a logo for my crypto bot"
- Route: `gemini_generate_image`
- Model: `pro` (logo = final deliverable)
- Ratio: `1:1` (logo)
- Enhance prompt with style, colors, composition

**Edit request**: "make the background darker on that last image"
- Route: `gemini_edit_image` with `image_path: "last"`
- Model: keep current session model
- Prompt: specific edit instruction

**Keynote integration**: "generate images for this keynote deck"
- Route: `gemini_generate_image` with shared `conversation_id`
- Model: `pro` (external deliverable)
- Ratio: `16:9` (presentation slides)
- Enable `use_image_history` for consistent style across slides

# VERIFY

- Image file saved to the expected path (output/images/{name}.png or specified path) | Verify: Check tool output for saved file path
- Enhanced prompt was shown to Eric before generating (not silently submitted) | Verify: Confirm prompt approval step in output
- Model matches intent: pro for final deliverables, flash only for drafts/iteration | Verify: Review model selection in output
- No watermarks, text artifacts, or unintended elements visible in generated image | Verify: Display image and review
- For multi-image sets: conversation_id used so style is consistent across images | Verify: Check use_image_history flag in tool call

# LEARN

- Track which prompt enhancement patterns produce the best results (e.g., specific style descriptors, lighting language) -- build a reusable prompt vocabulary over time
- If Eric frequently asks for edits after generation, note the original prompt gap and improve the enhancement step
- If flash model consistently requires refinement to reach acceptable quality, raise the bar for when flash is appropriate
- If a content type (logos, diagrams, portraits) consistently underperforms, note the weakness and suggest alternatives (/visualize for diagrams)
- Signal {YYYY-MM-DD}_create-image-{slug}.md: novel prompt structure/style combo with notably better results; rating 7+ for reusable techniques.
