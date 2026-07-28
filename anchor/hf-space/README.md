---
title: Ollama
emoji: 🦙
colorFrom: indigo
colorTo: purple
sdk: gradio
app_port: 7860
pinned: false
license: mit
---
# Always-On Ollama on HuggingFace Spaces (Free Tier)

Runs Ollama inside a Gradio Space with a chat UI. Also exposes the Ollama API on port 7860.

## After deployment
- Chat UI: `https://josephrw-ollama.hf.space`
- API: `https://josephrw-ollama.hf.space` (Gradio backend, Ollama runs locally inside)

## Add more models
Edit `app.py` and add `subprocess.Popen(["ollama", "pull", "model_name"])` lines.
