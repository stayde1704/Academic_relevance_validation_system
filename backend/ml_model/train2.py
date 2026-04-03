# D:\EDI\venv\Scripts\activate
# Run: python ml_model/train2.py
# Validate: python ml_model/train2.py validate

import pandas as pd
import ast
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics import classification_report
from sklearn.metrics.pairwise import cosine_similarity
import torch
from torch import nn
import torch.optim as optim
import os
import random
import sys

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")
if torch.cuda.is_available():
    print(torch.cuda.get_device_name(0))


def parse_abstract(raw):
    if not raw or pd.isna(raw):
        return ""
    try:
        sentences = ast.literal_eval(raw)
        if isinstance(sentences, list):
            return " ".join(str(s) for s in sentences)
    except:
        pass
    return str(raw).strip()


def load_corpus(corpus_path):
    df = pd.read_csv(corpus_path)
    corpus = {}
    for _, row in df.iterrows():
        corpus[str(int(row["doc_id"]))] = {
            "title": str(row["title"]) if pd.notna(row["title"]) else "",
            "abstract": parse_abstract(row["abstract"])
        }
    return corpus


def load_claims(claims_path):
    df = pd.read_csv(claims_path)
    claims = []
    for _, row in df.iterrows():
        claims.append({
            "claim": str(row["claim"]),
            "evidence_doc_id": str(row["evidence_doc_id"]) if pd.notna(row["evidence_doc_id"]) else "",
            "evidence_label": str(row["evidence_label"]) if pd.notna(row["evidence_label"]) else ""
        })
    return claims


def build_triplets(claims, corpus):
    """
    Build (anchor, positive, negative) triplets from SciFact.
    anchor   = claim
    positive = SUPPORT paper
    negative = CONTRADICT paper if available, else random unrelated paper
    """
    # first pass — collect all support and contradict pairs
    support_map   = {}  # claim → paper_text
    contradict_map = {} # claim → paper_text

    for c in claims:
        doc_id    = c["evidence_doc_id"]
        label_str = c["evidence_label"].upper()

        if not doc_id or doc_id == "nan":
            continue
        try:
            doc_id = str(int(float(doc_id)))
        except:
            continue
        if doc_id not in corpus:
            continue

        paper = corpus[doc_id]
        paper_text = f"{paper['title']} {paper['abstract']}".strip()
        if not paper_text:
            continue

        if label_str == "SUPPORT":
            support_map[c["claim"]] = paper_text
        elif label_str == "CONTRADICT":
            contradict_map[c["claim"]] = paper_text

    # all paper texts for random negatives
    all_paper_texts = [
        f"{p['title']} {p['abstract']}".strip()
        for p in corpus.values()
        if f"{p['title']} {p['abstract']}".strip()
    ]

    # second pass — build triplets
    triplets = []
    skipped  = 0

    for claim, pos_text in support_map.items():
        # prefer a real contradict paper as negative
        if claim in contradict_map:
            neg_text = contradict_map[claim]
        else:
            # fall back to random unrelated paper
            neg_text = random.choice(all_paper_texts)
            # make sure it's not the positive
            while neg_text == pos_text:
                neg_text = random.choice(all_paper_texts)

        triplets.append({
            "anchor":   claim,
            "positive": pos_text,
            "negative": neg_text
        })

    print(f"Built {len(triplets)} triplets ({skipped} skipped)")
    return triplets


def mean_pool(output, attention_mask):
    token_embeddings = output.last_hidden_state
    mask = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * mask, 1) / torch.clamp(mask.sum(1), min=1e-9)


def train(
    corpus_path="ml_model/data/corpus_train.csv",
    claims_train_path="ml_model/data/claims_train.csv",
    claims_val_path="ml_model/data/claims_validation.csv",
    output_path="ml_model/saved_model2",
    epochs=3,
    batch_size=8,
    lr=2e-5,
    margin=0.5   # triplet loss margin
):
    print("Loading data...")
    corpus       = load_corpus(corpus_path)
    train_claims = load_claims(claims_train_path)
    val_claims   = load_claims(claims_val_path)

    train_triplets = build_triplets(train_claims, corpus)
    val_pairs      = build_val_pairs(val_claims, corpus)

    random.shuffle(train_triplets)
    print(f"Training triplets: {len(train_triplets)}")
    print(f"Validation pairs:  {len(val_pairs)}")

    if not train_triplets:
        print("No triplets found.")
        return

    print("\nLoading E5 model...")
    try:
        model = SentenceTransformer("intfloat/e5-base-v2", device=device)
        print(f"✅ Model loaded on {device}")
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    model[0].auto_model.gradient_checkpointing_enable()

    tokenizer   = model.tokenizer
    transformer = model[0].auto_model

    optimizer  = optim.AdamW(model.parameters(), lr=lr)
    cos_sim    = nn.CosineSimilarity(dim=1)
    # triplet margin loss — positive should score higher than negative by at least `margin`
    triplet_loss = nn.TripletMarginWithDistanceLoss(
        distance_function=lambda a, b: 1 - cos_sim(a, b),
        margin=margin
    )

    print(f"\nTraining for {epochs} epochs on {device}...")
    model.train()

    for epoch in range(epochs):
        total_loss  = 0
        num_batches = 0

        for i in range(0, len(train_triplets), batch_size):
            optimizer.zero_grad()

            batch = train_triplets[i:i + batch_size]

            anchors   = [f"query: {t['anchor']}"          for t in batch]
            positives = [f"passage: {t['positive']}"      for t in batch]
            negatives = [f"passage: {t['negative']}"      for t in batch]

            a_enc = tokenizer(anchors,   padding=True, truncation=True,
                              max_length=256, return_tensors="pt").to(device)
            p_enc = tokenizer(positives, padding=True, truncation=True,
                              max_length=256, return_tensors="pt").to(device)
            n_enc = tokenizer(negatives, padding=True, truncation=True,
                              max_length=256, return_tensors="pt").to(device)

            a_emb = mean_pool(transformer(**a_enc), a_enc["attention_mask"])
            p_emb = mean_pool(transformer(**p_enc), p_enc["attention_mask"])
            n_emb = mean_pool(transformer(**n_enc), n_enc["attention_mask"])

            loss = triplet_loss(a_emb, p_emb, n_emb)

            loss.backward()
            optimizer.step()

            total_loss  += loss.item()
            num_batches += 1

            torch.cuda.empty_cache()

        print(f"Epoch {epoch+1}/{epochs} — Avg Loss: {total_loss/num_batches:.4f}")

    os.makedirs(output_path, exist_ok=True)
    model.save(output_path)
    print(f"\n✅ Model saved to {output_path}")

    print("\nValidating...")
    validate(model, val_pairs)


def build_val_pairs(claims, corpus):
    """
    For validation — build scored pairs with synthetic negatives.
    SUPPORT → 1.0, CONTRADICT → 0.5, random unrelated → 0.0
    """
    all_paper_texts = [
        f"{p['title']} {p['abstract']}".strip()
        for p in corpus.values()
        if f"{p['title']} {p['abstract']}".strip()
    ]

    pairs = []
    for c in claims:
        doc_id    = c["evidence_doc_id"]
        label_str = c["evidence_label"].upper()

        if not doc_id or doc_id == "nan":
            continue
        try:
            doc_id = str(int(float(doc_id)))
        except:
            continue
        if doc_id not in corpus:
            continue

        paper = corpus[doc_id]
        paper_text = f"{paper['title']} {paper['abstract']}".strip()
        if not paper_text:
            continue

        if label_str == "SUPPORT":
            label = 1.0
        elif label_str == "CONTRADICT":
            label = 0.5
        else:
            continue

        pairs.append({"claim": c["claim"], "paper_text": paper_text, "label": label})

        # add a synthetic irrelevant pair for every claim
        neg_text = random.choice(all_paper_texts)
        while neg_text == paper_text:
            neg_text = random.choice(all_paper_texts)
        pairs.append({"claim": c["claim"], "paper_text": neg_text, "label": 0.0})

    print(f"Built {len(pairs)} validation pairs")
    return pairs


def validate(model, val_pairs):
    model.eval()
    y_true     = []
    y_pred     = []
    all_scores = []

    print(f"Validating on {len(val_pairs)} pairs...")

    with torch.no_grad():
        for i, p in enumerate(val_pairs):
            if i % 100 == 0:
                print(f"  {i}/{len(val_pairs)}...")

            claim_vec = model.encode([f"query: {p['claim']}"],        convert_to_tensor=False)
            paper_vec = model.encode([f"passage: {p['paper_text']}"], convert_to_tensor=False)

            score = float(cosine_similarity(claim_vec, paper_vec)[0][0])
            all_scores.append(score)

            if score >= 0.55:
                pred = "ml_relevant"
            elif score >= 0.25:
                pred = "ml_less_relevant"
            else:
                pred = "ml_irrelevant"

            if p["label"] == 1.0:
                true_label = "ml_relevant"
            elif p["label"] == 0.5:
                true_label = "ml_less_relevant"
            else:
                true_label = "ml_irrelevant"

            y_true.append(true_label)
            y_pred.append(pred)

    print("\n" + "="*60)
    print("VALIDATION RESULTS:")
    print("="*60)
    print(f"Score distribution — min: {min(all_scores):.3f} max: {max(all_scores):.3f} "
          f"mean: {np.mean(all_scores):.3f} median: {np.median(all_scores):.3f}")
    print(classification_report(y_true, y_pred))


def validate_saved_model(
    corpus_path="ml_model/data/corpus_train.csv",
    claims_val_path="ml_model/data/claims_validation.csv",
    model_path="ml_model/saved_model2"
):
    corpus     = load_corpus(corpus_path)
    val_claims = load_claims(claims_val_path)
    val_pairs  = build_val_pairs(val_claims, corpus)

    print("Loading saved model...")
    model = SentenceTransformer(model_path, device=device)
    validate(model, val_pairs)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "validate":
        validate_saved_model()
    else:
        train()