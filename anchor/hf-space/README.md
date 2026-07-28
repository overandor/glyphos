---
title: Ollama
emoji: 🦙
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 11434
pinned: false
license: mit
---
# Always-On Ollama on HuggingFace Spaces

This Space runs Ollama with pre-pulled models. It gives you a permanent API endpoint that works without your laptop.

## Endpoint
After deployment: `https://<your-username>-ollama.hf.space`

## Usage
```bash
# List models
curl https://<your-username>-ollama.hf.space/api/tags

# Chat
curl https://<your-username>-ollama.hf.space/api/chat -d '{
  "model": "llama3.2:3b",
  "messages": [{"role": "user", "content": "Hello!"}]
}'
```

## Add models
Edit the Dockerfile and add `ollama pull <model>` lines, then rebuild.

## Connect to static UI
Update `ollama-config.json`:
```json
{
  "cloud_endpoint": "https://<your-username>-ollama.hf.space"
}
```
