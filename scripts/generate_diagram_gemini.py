#!/usr/bin/env python3
"""Generate CivicLens diagram parts using Gemini 3.1 Flash image generation via OpenRouter."""
import os, sys, json, base64, requests

API_KEY = os.environ.get("OPENROUTER_API_KEY")
if not API_KEY:
    # Try loading from .env
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_path):
        for line in open(env_path):
            if line.startswith('OPENROUTER_API_KEY='):
                API_KEY = line.strip().split('=', 1)[1].strip('"').strip("'")
                break
if not API_KEY:
    print("Error: OPENROUTER_API_KEY not set"); sys.exit(1)

MODEL = os.environ.get("DIAGRAM_MODEL", "google/gemini-3.1-flash-image-preview")
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'findings', 'entropy-collapse-scaling', 'diagrams')
os.makedirs(OUT_DIR, exist_ok=True)

def generate_image(prompt, filename):
    """Call OpenRouter with Gemini image model, save result."""
    print(f"\n{'='*60}")
    print(f"Generating: {filename}")
    print(f"{'='*60}")

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
    }
    # For image-generation models (non-Gemini), pass explicit 16:9 dimensions
    if "gemini" not in MODEL.lower():
        payload["width"] = 1920
        payload["height"] = 1080

    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120,
    )

    if resp.status_code != 200:
        print(f"Error {resp.status_code}: {resp.text[:500]}")
        return False

    data = resp.json()

    # Extract image: msg.images[i].image_url.url = "data:image/png;base64,..."
    msg = data.get("choices", [{}])[0].get("message", {})
    images = msg.get("images", [])
    if not images:
        print(f"No images. Content: {str(msg.get('content',''))[:200]}")
        return False

    img_entry = images[0]
    if isinstance(img_entry, dict):
        img_data = img_entry.get("image_url", {}).get("url", "")
    else:
        img_data = img_entry

    if ";base64," in img_data:
        img_data = img_data.split(";base64,")[1]

    img_bytes = base64.b64decode(img_data)
    out_path = os.path.join(OUT_DIR, filename)
    with open(out_path, 'wb') as f:
        f.write(img_bytes)

    print(f"Saved: {out_path} ({len(img_bytes)} bytes)")
    return True

# ═══════════════════════════════════════════════════════════════
# PART 1: Moltbook Social Network UI Mockup
# ═══════════════════════════════════════════════════════════════
MOLTBOOK_PROMPT = """Create a clean, simplified mockup of a social network interface called "Moltbook" for an academic diagram. This is a Reddit-like platform for AI agents. Style: flat design, clean lines, white background, suitable for an academic conference slide.

The mockup should show:
- A dark header bar at top with "moltbook" text in red/coral color, a search bar, and navigation
- Below the header: sort tabs showing "Hot", "New", "Top", "Discussed"
- 3 post cards stacked vertically, each showing:
  - Red upvote arrow and score number on the left (scores: 89, 42, 5)
  - Small colored circle avatar
  - Green submolt link like "m/general"
  - Post title in bold
  - Gray comment count
- A sidebar on the right showing:
  - "Live Activity" section with dark background and green activity dots
  - "Submolts" list showing m/general, m/agents, m/philosophy with green circle icons
- Clean, minimal, professional look — suitable for an academic presentation
- White background, no shadows, flat design
- The overall shape should be like a browser window or app frame"""

# ═══════════════════════════════════════════════════════════════
# PART 2: Docker Agent Grid
# ═══════════════════════════════════════════════════════════════
AGENTS_PROMPT = """Create a grid of 8 Docker container blocks for AI agents, arranged in a 4x2 grid layout, for an academic diagram. Clean flat design, white background.

Each agent container is a colored rounded rectangle block with:
- A small robot icon at the top
- A large Greek letter in the center (α, β, γ, δ, ε, ζ, η, θ)
- The agent name below (Alpha, Beta, Gamma, Delta, Epsilon, Zeta, Eta, Theta)
- Each container has a bidirectional arrow (↕) coming from it, showing it reads and posts

Color coding by personality type:
- α Alpha and θ Theta: GRAY color (baseline personality)
- β Beta: BLUE color (introspective personality)
- γ Gamma: DARK GRAY (nihilist personality)
- δ Delta: GREEN color (leader personality)
- ε Epsilon: CYAN color (follower personality)
- ζ Zeta: RED color (contrarian personality)
- η Eta: AMBER/ORANGE color (curious personality)

Below the grid: a dashed outline box with "... +N Variable Agents" text

Header text above: "DOCKER AGENTS (AI Agents)"

Style: flat design, clean lines, white background, professional academic diagram style. Each block should be clearly distinct with its personality color."""

# ═══════════════════════════════════════════════════════════════
# PART 3: Full Combined Diagram
# ═══════════════════════════════════════════════════════════════
FULL_PROMPT = """Create a complete academic experimental setup diagram for "CivicLens" - a multi-agent social network research platform. This is for an academic conference slide. Clean, professional, flat design with white background. HIGH QUALITY, HIGHEST RESOLUTION.

The diagram has THREE COLUMNS connected by arrows:

LEFT COLUMN - "EXPERIMENTAL VARIABLES":
Four variable boxes stacked vertically, each with an icon and label. NO parentheses text, NO "(Control Panel)" subtitle. Clean and minimal:
1. AGENTS: Shows people/group silhouette icons, "×N" text with a slider bar visual
2. PERSONALITY: Shows different personality archetype icons — Leader, Contrarian, Curious, Follower, Skeptic, Baseline shown as small colored badges or icons. Show the variety of personality types visually with colored dots or mini cards
3. SEED POSTS: Shows document/page stack icons, "Quantity" label, arrow pointing right toward the platform
4. DURATION: Shows clock/hourglass icon, "t=" with time range indicator

CENTER COLUMN - "Moltbook":
NO subtitle like "(Social Network Interface)". Just "Moltbook" as the header.
A simplified social network UI mockup showing:
- A frame that looks like a social media app or website
- 3-4 post cards with colored circle avatars, upvote arrows, gray text lines representing content
- One post highlighted as a seed post with a distinct indicator
- Comment thread indicators with indentation
- A small sidebar area showing community/submolt list

RIGHT COLUMN - "DOCKER AGENTS":
NO subtitle like "(AI Agents)". Just "DOCKER AGENTS" as header.
A grid of 8-10 agent containers arranged in rows:
- Each container is a LARGE colored block with a robot icon, a prominent Greek letter (α, β, γ, δ, ε, ζ, η, θ), and the agent name below
- Color coding by personality: green/teal for curious, orange for leader, red for contrarian, blue for introspective, gray for baseline, purple for devotee, cyan for follower
- Each individual agent has its own bidirectional arrow showing it reads and posts to the platform
- Below the grid: "... +N Variable Agents" in a dashed outline box

CONNECTIONS:
- Dashed gray arrows from each variable to the platform center
- One bold colored arrow from "Seed Posts" labeled "Injection" going into the platform
- Individual bidirectional arrows from EACH agent block toward the Moltbook platform

BOTTOM LEGEND:
- Colored circles/squares with personality type labels: Baseline, Introspective, Nihilist, Leader, Follower, Contrarian, Curious, Devotee
- Small icon legend showing: AI Agent icon, Seed Post icon, Read/Post Interaction arrow, Variable Control dashed line

TITLE at top: "CivicLens: Academic Multi-Agent Social Network Research Platform — Experimental Setup"

Style: Publication quality, clean flat design, white background, professional typography, suitable for Nature/Science/NeurIPS style conference presentation. HIGHEST QUALITY possible. Make it look polished and professional like a figure from a top-tier research paper."""

if __name__ == "__main__":
    parts = [
        (MOLTBOOK_PROMPT, "moltbook_mockup.png"),
        (AGENTS_PROMPT, "agent_grid.png"),
        (FULL_PROMPT, "civiclens_full.png"),
    ]

    # Usage:
    #   python3 script.py          → generate all 3 parts (1 each)
    #   python3 script.py 3        → generate only part 3
    #   python3 script.py 3 20     → generate part 3 twenty times (civiclens_full_01.png ... _20.png)
    if len(sys.argv) > 1:
        idx = int(sys.argv[1]) - 1
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        prompt, base_name = parts[idx]
        # Use model short name as suffix for filenames
        model_tag = MODEL.split("/")[-1].split("-")[0] if "/" in MODEL else "gen"
        if count == 1:
            name, ext = os.path.splitext(base_name)
            parts = [(prompt, f"{name}_{model_tag}{ext}")]
        else:
            name, ext = os.path.splitext(base_name)
            parts = [(prompt, f"{name}_{model_tag}_{i:02d}{ext}") for i in range(1, count + 1)]

    for prompt, filename in parts:
        ok = generate_image(prompt, filename)
        if not ok:
            print(f"Failed: {filename}, retrying...")
            generate_image(prompt, filename)

    print(f"\nDone! {len(parts)} images saved to {OUT_DIR}/")
