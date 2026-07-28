import gradio as gr
import requests
import subprocess
import os
import threading
import time

# Start Ollama server in background
def start_ollama():
    subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)

threading.Thread(target=start_ollama, daemon=True).start()

# Pre-pull a small model
time.sleep(5)
subprocess.Popen(["ollama", "pull", "llama3.2:3b"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

OLLAMA_URL = "http://localhost:11434"

def list_models():
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if r.ok:
            models = r.json().get("models", [])
            return [m["name"] for m in models] or ["No models pulled yet"]
        return ["Ollama not ready yet..."]
    except:
        return ["Ollama not ready yet..."]

def chat(message, history, model):
    if not message.strip():
        return "", history
    try:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": message}],
            "stream": True
        }
        r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, stream=True, timeout=120)
        full_response = ""
        for line in r.iter_lines():
            if line:
                chunk = line.decode("utf-8")
                try:
                    import json
                    data = json.loads(chunk)
                    if data.get("message", {}).get("content"):
                        full_response += data["message"]["content"]
                        yield "", history + [[message, full_response]]
                    if data.get("done"):
                        break
                except:
                    pass
        return "", history + [[message, full_response]]
    except Exception as e:
        return "", history + [[message, f"Error: {e}"]]

def refresh_models():
    models = list_models()
    return gr.Dropdown(choices=models, value=models[0] if models else None)

with gr.Blocks(title="Ollama Cloud", theme=gr.themes.Soft()) as app:
    gr.Markdown("# 🦙 Ollama — Always-On Cloud\nChat with Ollama models hosted on HuggingFace Spaces. No laptop required.")
    
    with gr.Row():
        model_dd = gr.Dropdown(choices=list_models(), value=list_models()[0] if list_models() else None, label="Model")
        refresh_btn = gr.Button("↻", size="sm")
    
    chatbot = gr.Chatbot(height=500)
    msg_input = gr.Textbox(placeholder="Type a message...", label="Message")
    
    msg_input.submit(chat, [msg_input, chatbot, model_dd], [msg_input, chatbot])
    refresh_btn.click(refresh_models, outputs=model_dd)

app.launch(server_name="0.0.0.0", server_port=7860)
