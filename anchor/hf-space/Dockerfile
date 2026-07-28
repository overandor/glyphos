# HuggingFace Spaces — Always-On Ollama
# Deploy this as a HuggingFace Space (Docker type, CPU basic is free)
# This gives you a permanent Ollama endpoint that doesn't need your laptop.
#
# After deployment, your Ollama endpoint will be:
#   https://<your-username>-ollama.hf.space
#
# Then update anchor/ollama-config.json:
#   "cloud_endpoint": "https://<your-username>-ollama.hf.space"
#
# Models are pre-pulled during build. To add more, edit the RUN ollama pull line.

FROM ollama/ollama:latest

# Pre-pull models during build (keeps them in the image)
# CPU-basic tier: use small models (1-4GB)
RUN ollama serve & \
    sleep 5 && \
    ollama pull llama3.2:3b && \
    ollama pull qwen2.5:3b && \
    ollama pull phi3:mini && \
    kill %1

# Expose Ollama port
EXPOSE 11434

# Start Ollama with 0.0.0.0 binding (required for HF Spaces)
ENV OLLAMA_HOST=0.0.0.0:11434
CMD ["ollama", "serve"]
