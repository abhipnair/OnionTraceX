import os
os.environ["TRANSFORMERS_DISABLE_CONVERSION"] = "1"

import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel

MODEL_ID = "s2w-ai/DarkBERT"

# Load DarkBERT encoder
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_ID,
    use_safetensors=False
)
model = AutoModel.from_pretrained(
    MODEL_ID,
    use_safetensors=False
)
model.eval()

def embed(text: str):
    tokens = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=512
    )
    with torch.no_grad():
        out = model(**tokens)
    return out.last_hidden_state[:, 0, :]  # CLS vector

# --- Build prototype embeddings ---
DOMAIN_PROTOTYPES = {
    "ransomware": [
        "we provide ransomware-as-a-service",
        "payload builder and affiliate panel"
    ],
    "drugs": [
        "we sell lsd mdma cocaine worldwide",
        "discreet drug shipping escrow accepted"
    ],
    "marketplace": [
        "darknet marketplace vendor listings",
        "escrow multisig trusted vendors"
    ],
    "hacking": [
        "ddos services exploit kits",
        "carding dumps cvv fullz"
    ]
}

prototype_embeddings = {}

for domain, texts in DOMAIN_PROTOTYPES.items():
    vecs = [embed(t) for t in texts]
    prototype_embeddings[domain] = torch.mean(
        torch.cat(vecs, dim=0),
        dim=0,
        keepdim=True
    )

# --- Test input (simulating page text) ---
TEST_TEXT = """
Affiliates required. Access to ransomware builder.
Encrypted payload delivery and TOR support.
"""

test_vec = embed(TEST_TEXT)

# --- Similarity scoring ---
scores = {}
for domain, proto_vec in prototype_embeddings.items():
    sim = F.cosine_similarity(test_vec, proto_vec).item()
    scores[domain] = sim

# Normalize to confidence
total = sum(max(v, 0) for v in scores.values())
confidences = {
    k: max(v, 0) / total if total > 0 else 0
    for k, v in scores.items()
}

# Results
print("=== Classification Result ===")
for k in sorted(confidences, key=confidences.get, reverse=True):
    print(f"{k:12s} -> {confidences[k]:.3f}")
