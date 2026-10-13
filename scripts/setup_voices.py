"""Create ready-made voices for the web UI from LibriSpeech (CC BY 4.0).

Each voice becomes a folder under ./references/<Name>/ holding a ~15-25 s
reference clip (ref.wav) and its transcript (ref.lab). fish-speech clones a
voice from that clip whenever a request passes reference_id=<Name>.

Usage (from the repo root):  python scripts/setup_voices.py
"""

import json
import tarfile
import urllib.request
from pathlib import Path

import numpy as np
import soundfile as sf

URL = "https://www.openslr.org/resources/12/dev-clean.tar.gz"
WORK = Path("/tmp/librispeech")
OUT = Path("references")

# Display names for the voices, assigned to male speakers in ID order
NAMES = ["Adrian", "Marcus", "Theo", "Daniel", "Victor"]
MIN_SECONDS, MAX_SECONDS = 15.0, 25.0


def download():
    archive = WORK / "dev-clean.tar.gz"
    root = WORK / "LibriSpeech"
    if (root / "dev-clean").exists():
        return root
    WORK.mkdir(parents=True, exist_ok=True)
    if not archive.exists():
        print("Downloading LibriSpeech dev-clean (~340 MB)...")
        urllib.request.urlretrieve(URL, archive)
    print("Extracting...")
    with tarfile.open(archive) as tar:
        tar.extractall(WORK, filter="data")
    return root


def male_speakers(root):
    speakers = []
    for line in (root / "SPEAKERS.TXT").read_text().splitlines():
        if line.startswith(";"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3 and parts[1] == "M" and parts[2] == "dev-clean":
            speakers.append(parts[0])
    return sorted(speakers, key=int)


def build_clip(speaker_dir):
    """Join consecutive utterances from one chapter into a single clip."""
    for chapter in sorted(speaker_dir.iterdir()):
        trans = next(chapter.glob("*.trans.txt"))
        lines = trans.read_text().splitlines()
        audio, texts, sr = [], [], None
        for line in lines:
            utt_id, text = line.split(" ", 1)
            data, sr = sf.read(chapter / f"{utt_id}.flac", dtype="float32")
            if sum(len(a) for a in audio) + len(data) > MAX_SECONDS * sr:
                break
            audio.append(data)
            texts.append(text.capitalize().strip() + ".")
            if sum(len(a) for a in audio) >= MIN_SECONDS * sr:
                gap = np.zeros(int(0.25 * sr), dtype="float32")
                joined = np.concatenate([x for a in audio for x in (a, gap)][:-1])
                return joined, sr, " ".join(texts)
    return None


def main():
    root = download()
    OUT.mkdir(exist_ok=True)
    voices = []
    for speaker in male_speakers(root):
        if len(voices) == len(NAMES):
            break
        clip = build_clip(root / "dev-clean" / speaker)
        if clip is None:
            continue
        audio, sr, text = clip
        name = NAMES[len(voices)]
        folder = OUT / name
        folder.mkdir(parents=True, exist_ok=True)
        sf.write(folder / "ref.wav", audio, sr)
        (folder / "ref.lab").write_text(text)
        voices.append(
            {
                "name": name,
                "gender": "male",
                "seconds": round(len(audio) / sr, 1),
                "source": f"LibriSpeech dev-clean speaker {speaker} (CC BY 4.0)",
            }
        )
        print(f"Created voice {name} from speaker {speaker} ({len(audio) / sr:.1f}s)")
    (OUT / "voices.json").write_text(json.dumps(voices, indent=2))
    print(f"Done: {len(voices)} voices in {OUT.resolve()}")


if __name__ == "__main__":
    main()
