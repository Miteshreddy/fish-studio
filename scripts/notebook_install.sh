#!/usr/bin/env bash
# Robust installer for Kaggle/Colab. Skips pyaudio (only used by tools/api_client.py)
# and installs packages one by one if the batch install fails, so one bad package
# can't silently break the whole setup.
cd "$(dirname "$0")/.."
apt-get -qq update >/dev/null 2>&1; apt-get -qq install -y portaudio19-dev libsox-dev ffmpeg >/dev/null 2>&1

DEPS=$(python - <<'PY'
import tomllib
deps = tomllib.load(open("pyproject.toml", "rb"))["project"]["dependencies"]
print("\n".join(d for d in deps if not d.startswith("pyaudio")))
PY
)
echo "$DEPS" > /tmp/fish_reqs.txt

if ! pip install -q -r /tmp/fish_reqs.txt; then
  echo ">>> Batch install failed, retrying one package at a time"
  while read -r dep; do
    pip install -q "$dep" || echo ">>> FAILED: $dep"
  done < /tmp/fish_reqs.txt
fi
pip install -q --no-deps -e .

# Pin packages that clash with the notebook's pre-installed ones:
# torchvision must match torch 2.8, transformers needs huggingface_hub<1.0,
# fish-speech's protobuf code needs >=3.20, and the web UI targets Gradio 5.
pip install -q "torchvision==0.23.0" "huggingface_hub>=0.34,<1.0" "protobuf>=3.20,<6" "gradio==5.45.0"

python -c "import pyrootutils, gradio, torch, torchvision, pytorch_lightning, transformers, fish_speech.inference_engine; print('INSTALL OK, torch', torch.__version__, 'cuda', torch.cuda.is_available())"
