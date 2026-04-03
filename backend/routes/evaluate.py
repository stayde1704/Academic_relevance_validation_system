from flask import Blueprint, request, jsonify, Response, stream_with_context
from utils.openalex_client import fetch_papers
from utils.doi_handler import clean_doi
from utils.reference_validator import evaluate_reference
from ml_model import classify_paper, get_scorer
import requests
import json

evaluate_bp = Blueprint('evaluate', __name__)

@evaluate_bp.route("/evaluate", methods=["POST"])
def evaluate():
    data = request.get_json()
    if not data or "query" not in data:
        return jsonify({"error": "Query required"}), 400

    query = data["query"]
    page = data.get("page", 1)
    per_page = data.get("per_page", 15)
    papers, has_more = fetch_papers(query, page=page, per_page=per_page)

    return jsonify({
        "references": papers,
        "metrics": {
            "total_fetched": len(papers),
            "page": page,
            "per_page": per_page,
            "has_more": has_more
        }
    })


@evaluate_bp.route("/evaluate-stream", methods=["POST"])
def evaluate_stream():
    data = request.get_json()
    if not data or "query" not in data:
        return jsonify({"error": "Query required"}), 400

    query        = data["query"]
    instruction  = data.get("instruction", "").strip()
    use_ml       = bool(instruction)
    batch_number = data.get("batch", 1)

    if use_ml:
        get_scorer()

    PAGE_BATCH = 5   
    start_page = (batch_number - 1) * PAGE_BATCH + 1
    end_page   = batch_number * PAGE_BATCH

    def generate():
        total_sent = 0
        all_papers = []

        # ── Phase 1: stream all papers immediately ────────────────────────
        for page in range(start_page, end_page + 1):
            params = {
                "search": query.strip(),
                "per_page": 200,
                "page": page
            }
            try:
                response = requests.get(
                    "https://api.openalex.org/works",
                    params=params,
                    timeout=10
                )
                response.raise_for_status()
                results = response.json().get("results", [])

                if not results:
                    break

                print(f"📄 Page {page} — {len(results)} papers")

                for item in results:
                    primary_location = item.get("primary_location") or {}
                    source           = primary_location.get("source") or {}
                    paper_url        = primary_location.get("landing_page_url")
                    paper_doi        = clean_doi(item.get("doi"))
                    open_access_info = item.get("open_access") or {}

                    paper = {
                        "title":    item.get("display_name"),
                        "year":     item.get("publication_year"),
                        "doi":      paper_doi,
                        "citations": item.get("cited_by_count"),
                        "venue":    source.get("display_name"),
                        "url":      paper_url,
                        "authors":  [
                            a.get("author", {}).get("display_name")
                            for a in item.get("authorships", [])
                        ],
                        "status":       "pending",
                        "ml_relevance": "pending" if use_ml else "skipped",
                        "open_access": {
                            "is_oa":     open_access_info.get("is_oa", False),
                            "oa_status": open_access_info.get("oa_status"),
                            "oa_url":    open_access_info.get("oa_url")
                        },
                        "source": {
                            "name":      source.get("display_name"),
                            "publisher": source.get("publisher"),
                            "type":      source.get("type"),
                            "issn_l":    source.get("issn_l")
                        },
                        "index": total_sent,
                        "page":  page
                    }

                    yield f"data: {json.dumps({'type': 'paper', 'data': paper})}\n\n"
                    all_papers.append({
                        "index":     total_sent,
                        "paper":     paper,
                        "paper_url": paper_url,
                        "paper_doi": paper_doi
                    })
                    total_sent += 1

            except Exception as e:
                print(f"❌ Error page {page}: {e}")
                break

        print(f"✅ {total_sent} papers streamed. Starting validation...")

        # ── Phase 2: batch validate + ML score ───────────────────────────
        from sklearn.metrics.pairwise import cosine_similarity

        BATCH_SIZE = 32
        for i in range(0, len(all_papers), BATCH_SIZE):
            batch = all_papers[i:i + BATCH_SIZE]
            print(f"🔍 Validating batch {i//BATCH_SIZE + 1}/{(len(all_papers)-1)//BATCH_SIZE + 1}")

            if use_ml:
                scorer       = get_scorer()
                instr_texts  = [f"query: {instruction}" for _ in batch]
                paper_texts  = [
                    f"passage: {(b['paper'].get('title') or '')} {(b['paper'].get('abstract') or '')}".strip()
                    for b in batch
                ]
                instr_vecs  = scorer.model.encode(instr_texts,  batch_size=BATCH_SIZE, convert_to_numpy=True)
                paper_vecs  = scorer.model.encode(paper_texts,  batch_size=BATCH_SIZE, convert_to_numpy=True)
                scores      = [
                    float(cosine_similarity([instr_vecs[j]], [paper_vecs[j]])[0][0])
                    for j in range(len(batch))
                ]
                ml_statuses = [scorer.classify_from_score(s) for s in scores]
            else:
                ml_statuses = ["skipped"] * len(batch)

            for j, item in enumerate(batch):
                try:
                    if not item["paper_url"] and not item["paper_doi"]:
                        val_status = "invalid_metadata"
                    else:
                        val_status = evaluate_reference(item["paper_url"], item["paper_doi"])

                    yield f"data: {json.dumps({'type': 'status_update', 'index': item['index'], 'status': val_status, 'ml_relevance': ml_statuses[j]})}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'type': 'status_update', 'index': item['index'], 'status': 'broken', 'ml_relevance': 'skipped'})}\n\n"

        # ── Done ──────────────────────────────────────────────────────────
        yield f"data: {json.dumps({'type': 'complete', 'total': total_sent, 'batch': batch_number})}\n\n"
        print(f"🎉 Batch {batch_number} done: {total_sent} papers")

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )