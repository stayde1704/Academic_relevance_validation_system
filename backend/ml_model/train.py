# D:\EDI\venv\Scripts\activate 

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


def build_pairs(claims, corpus):
    pairs = []
    skipped = 0

    for c in claims:
        doc_id = c["evidence_doc_id"]
        label_str = c["evidence_label"].upper()

        if not doc_id or doc_id == "nan":
            skipped += 1
            continue
        try:
            doc_id = str(int(float(doc_id)))
        except:
            skipped += 1
            continue

        if doc_id not in corpus:
            skipped += 1
            continue

        paper = corpus[doc_id]
        paper_text = f"{paper['title']} {paper['abstract']}".strip()

        if not paper_text:
            skipped += 1
            continue

        if label_str == "SUPPORT":
            label = 1.0
        elif label_str == "CONTRADICT":
            label = 0.5
        else:
            label = 0.0

        pairs.append({
            "claim": c["claim"],
            "paper_text": paper_text,
            "label": label
        })

    print(f"Built {len(pairs)} pairs ({skipped} skipped)")
    return pairs


def load_nfcorpus_pairs(sample_size=1000):
    print("Loading NFCorpus dataset...")
    try:
        from datasets import load_dataset

        corpus  = load_dataset("BeIR/nfcorpus", "corpus",  split="corpus")
        queries = load_dataset("BeIR/nfcorpus", "queries", split="queries")
        qrels   = load_dataset("BeIR/nfcorpus-qrels",      split="test")

        corpus_dict  = {
            str(x["_id"]): f"{x.get('title', '')} {x.get('text', '')}".strip()
            for x in corpus
        }
        queries_dict = {
            str(x["_id"]): x.get("text", "")
            for x in queries
        }

        pairs = []
        for item in qrels:
            qid   = str(item["query-id"])
            did   = str(item["corpus-id"])
            score = int(item.get("score", 0))

            if qid not in queries_dict or did not in corpus_dict:
                continue

            label = 1.0 if score == 2 else 0.5 if score == 1 else 0.0

            pairs.append({
                "claim": queries_dict[qid],
                "paper_text": corpus_dict[did],
                "label": label
            })

            if len(pairs) >= sample_size:
                break

        print(f"Loaded {len(pairs)} NFCorpus pairs")
        return pairs

    except Exception as e:
        print(f"⚠️ Could not load NFCorpus: {e}")
        return []


def load_scidocs_pairs(sample_size=500):
    print("Loading SciDocs from local files...")
    try:
        import json

        corpus_path  = "ml_model/data/scidocs/corpus.jsonl"
        queries_path = "ml_model/data/scidocs/queries.jsonl"
        qrels_path   = "ml_model/data/scidocs/qrels/test.tsv"

        if not os.path.exists(corpus_path):
            print("⚠️ SciDocs files not found at ml_model/data/scidocs/")
            return []

        # load corpus
        corpus_dict = {}
        with open(corpus_path, "r", encoding="utf-8") as f:
            for line in f:
                item = json.loads(line)
                corpus_dict[str(item["_id"])] = f"{item.get('title', '')} {item.get('text', '')}".strip()

        # load queries — note: no title field, just text
        queries_dict = {}
        with open(queries_path, "r", encoding="utf-8") as f:
            for line in f:
                item = json.loads(line)
                queries_dict[str(item["_id"])] = item.get("text", "")

        # load qrels — 3 columns: query-id, corpus-id, score
        pairs = []
        with open(qrels_path, "r", encoding="utf-8") as f:
            next(f)  # skip header
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) < 3:
                    continue

                qid   = str(parts[0])
                did   = str(parts[1])
                score = int(parts[2])

                if qid not in queries_dict or did not in corpus_dict:
                    continue

                # score 1 = relevant, 0 = not relevant (no score=2 in SciDocs)
                label = 1.0 if score == 1 else 0.0

                pairs.append({
                    "claim": queries_dict[qid],
                    "paper_text": corpus_dict[did],
                    "label": label
                })

                if len(pairs) >= sample_size:
                    break

        print(f"Loaded {len(pairs)} SciDocs pairs")
        return pairs

    except Exception as e:
        print(f"⚠️ Could not load SciDocs: {e}")
        return []
        

def mean_pool(output, attention_mask):
    token_embeddings = output.last_hidden_state
    mask = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * mask, 1) / torch.clamp(mask.sum(1), min=1e-9)


def train(
    corpus_path="ml_model/data/corpus_train.csv",
    claims_train_path="ml_model/data/claims_train.csv",
    claims_val_path="ml_model/data/claims_validation.csv",
    output_path="ml_model/saved_model",
    epochs=5,
    batch_size=8,
    lr=1e-5
):
    print("Loading data...")
    corpus       = load_corpus(corpus_path)
    train_claims = load_claims(claims_train_path)
    val_claims   = load_claims(claims_val_path)

    scifact_pairs  = build_pairs(train_claims, corpus)
    val_pairs      = build_pairs(val_claims, corpus)

    nfcorpus_pairs = load_nfcorpus_pairs(sample_size=1000)
    scidocs_pairs  = load_scidocs_pairs(sample_size=500)

    train_pairs = scifact_pairs + nfcorpus_pairs + scidocs_pairs
    random.shuffle(train_pairs)

    print(f"\nTotal training pairs: {len(train_pairs)}")
    print(f"  SciFact:   {len(scifact_pairs)}")
    print(f"  NFCorpus:  {len(nfcorpus_pairs)}")
    print(f"  SciDocs:   {len(scidocs_pairs)}")

    if not train_pairs:
        print("No training pairs found.")
        return

    print("\nLoading E5 model...")
    try:
        model = SentenceTransformer("intfloat/e5-base-v2", device=device)
        print(f"✅ Model loaded on {device}")
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return

    model[0].auto_model.gradient_checkpointing_enable()

    claim_texts  = [f"query: {p['claim']}"        for p in train_pairs]
    paper_texts  = [f"passage: {p['paper_text']}" for p in train_pairs]
    labels       = [p["label"]                    for p in train_pairs]
    label_tensor = torch.tensor(labels, dtype=torch.float32).to(device)

    optimizer   = optim.AdamW(model.parameters(), lr=lr)
    cos_sim     = nn.CosineSimilarity(dim=1)
    loss_fn     = nn.MSELoss()
    tokenizer   = model.tokenizer
    transformer = model[0].auto_model

    print(f"\nTraining for {epochs} epochs on {device}...")
    model.train()

    for epoch in range(epochs):
        total_loss  = 0
        num_batches = 0

        for i in range(0, len(claim_texts), batch_size):
            optimizer.zero_grad()

            c_batch = claim_texts[i:i + batch_size]
            p_batch = paper_texts[i:i + batch_size]
            l_batch = label_tensor[i:i + batch_size]

            c_enc = tokenizer(c_batch, padding=True, truncation=True,
                              max_length=256, return_tensors="pt").to(device)
            p_enc = tokenizer(p_batch, padding=True, truncation=True,
                              max_length=256, return_tensors="pt").to(device)

            c_emb = mean_pool(transformer(**c_enc), c_enc["attention_mask"])
            p_emb = mean_pool(transformer(**p_enc), p_enc["attention_mask"])

            scores = cos_sim(c_emb, p_emb)
            loss   = loss_fn(scores, l_batch)

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


def validate(model, val_pairs):
    model.eval()
    y_true     = []
    y_pred     = []
    all_scores = []

    print(f"Validating on {len(val_pairs)} pairs...")

    with torch.no_grad():
        for i, p in enumerate(val_pairs):
            if i % 50 == 0:
                print(f"  {i}/{len(val_pairs)}...")

            claim_vec = model.encode([f"query: {p['claim']}"],        convert_to_tensor=False)
            paper_vec = model.encode([f"passage: {p['paper_text']}"], convert_to_tensor=False)

            score = float(cosine_similarity(claim_vec, paper_vec)[0][0])
            all_scores.append(score)

            if score >= 0.82:
                pred = "ml_relevant"
            elif score >= 0.60:
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
    print(f"Score distribution — min: {min(all_scores):.3f} max: {max(all_scores):.3f} mean: {np.mean(all_scores):.3f} median: {np.median(all_scores):.3f}")
    print(classification_report(y_true, y_pred))

def validate_saved_model(
    corpus_path="ml_model/data/corpus_train.csv",
    claims_val_path="ml_model/data/claims_validation.csv",
    model_path="ml_model/saved_model"
):
    corpus     = load_corpus(corpus_path)
    val_claims = load_claims(claims_val_path)
    val_pairs  = build_pairs(val_claims, corpus)

    print("Loading saved model...")
    model = SentenceTransformer(model_path, device=device)
    validate(model, val_pairs)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "validate":
        validate_saved_model()
    else:
        train()