import os

path = os.path.join("api", "routes", "community", "community.py")
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

target = 'model_name = os.getenv("VOO_NVIDIA_MODEL", "meta/llama-3.1-70b-instruct")'
replacement = 'model_name = os.getenv("VOO_NVIDIA_MODEL", "meta/llama-3.3-70b-instruct")'

if target in text:
    new_text = text.replace(target, replacement)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(new_text)
    print("SUCCESS: Updated NVIDIA model default to llama-3.3-70b-instruct!")
else:
    print("Target not found")
