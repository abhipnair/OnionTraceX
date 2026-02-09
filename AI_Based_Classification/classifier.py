import os
os.environ["TRANSFORMERS_DISABLE_CONVERSION"] = "1"

import yaml
from bs4 import BeautifulSoup
from transformers import AutoTokenizer, AutoModel

# Load config
with open("AI_Based_Classification/config.yaml") as f:
    CFG = yaml.safe_load(f)

MODEL_ID = CFG["model"]["id"]

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_ID,
    use_safetensors=False
)

model = AutoModel.from_pretrained(
    MODEL_ID,
    use_safetensors=False
)
model.eval()


def clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return " ".join(soup.stripped_strings).lower()


def classify_pages(pages: list[str]):
    text = " ".join(clean_html(p) for p in pages)

    if not text.strip():
        return "unknown", 0.0

    scores = {
        label: sum(k in text for k in keywords)
        for label, keywords in CFG["labels"].items()
    }

    total = sum(scores.values()) + 1e-6
    confidences = {k: v / total for k, v in scores.items()}

    label = max(confidences, key=confidences.get)
    confidence = confidences[label]

    if confidence < CFG["thresholds"]["accept"]:
        return "unknown", confidence

    return label, confidence
