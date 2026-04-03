# ml_model/test.py

from relevance_scorer import RelevanceScorer, classify_paper, score_paper

INSTRUCTION = "Represent the scientific claim for retrieving supporting research papers"

def test_basic_scoring():
    print("=== Basic Scoring Test ===\n")
    scorer = RelevanceScorer()

    cases = [
        {
            "instruction": "research papers on AI hallucination in citations",
            "query": "AI hallucination citation validation",
            "paper": {
                "title": "Detecting Hallucinations in Large Language Model Citations",
                "abstract": "We propose methods to detect fabricated citations in LLM outputs..."
            },
            "expected": "ml_relevant"
        },
        {
            "instruction": "research papers on AI hallucination in citations",
            "query": "AI hallucination citation validation",
            "paper": {
                "title": "Deep Learning for Image Recognition",
                "abstract": "A convolutional neural network for image classification tasks..."
            },
            "expected": "ml_irrelevant"
        },
        {
            "instruction": "do affirmations and symbolic cues make a difference in human behavior",
            "query": "manifestation self hypnosis",
            "paper": {
                "title": "Enclothed Cognition and Symbolic Priming Effects",
                "abstract": "Wearing symbolic clothing affects cognitive performance and self perception..."
            },
            "expected": "ml_relevant"
        }
    ]

    for i, case in enumerate(cases):
        print(f"Test {i+1}:")
        print(f"  Instruction : {case['instruction']}")
        print(f"  Query       : {case['query']}")
        print(f"  Paper       : {case['paper']['title']}")

        score = scorer.score(case["instruction"], case["query"], case["paper"])
        result = scorer.classify(case["instruction"], case["query"], case["paper"])

        print(f"  Score       : {score:.3f}")
        print(f"  Result      : {result}")
        print(f"  Expected    : {case['expected']}")
        print(f"  {'✓ PASS' if result == case['expected'] else '✗ FAIL'}")
        print()


def test_no_instruction():
    """When no instruction given, ml scoring should be skipped"""
    print("=== No Instruction Test ===\n")
    scorer = RelevanceScorer()

    paper = {"title": "Some Paper", "abstract": "Some abstract text"}
    score = scorer.score("", "", paper)
    print(f"Empty instruction score: {score} (expected 0.0)")


def test_edge_cases():
    print("=== Edge Cases ===\n")
    scorer = RelevanceScorer()

    instruction = "research papers on machine learning"

    cases = [
        {"title": "", "abstract": ""},           # empty paper
        {"title": "ML Paper", "abstract": ""},   # no abstract
        {"title": "", "abstract": "Some text"},  # no title
    ]

    for i, paper in enumerate(cases):
        score = scorer.score(instruction, "machine learning", paper)
        print(f"Edge case {i+1}: score={score:.3f}")


def test_with_scifact():
    """Test against real SciFact validation data"""
    print("=== SciFact Validation Test ===\n")
    import pandas as pd
    import ast
    import os

    corpus_path = "ml_model/data/corpus_train.csv"
    claims_path = "ml_model/data/claims_validation.csv"

    if not os.path.exists(corpus_path) or not os.path.exists(claims_path):
        print("SciFact data not found, skipping.")
        return

    corpus_df = pd.read_csv(corpus_path)
    corpus = {}
    for _, row in corpus_df.iterrows():
        raw = row["abstract"]
        try:
            abstract = " ".join(ast.literal_eval(raw)) if pd.notna(raw) else ""
        except:
            abstract = str(raw)
        corpus[str(row["doc_id"])] = {
            "title": str(row["title"]),
            "abstract": abstract
        }

    claims_df = pd.read_csv(claims_path)
    scorer = RelevanceScorer()

    correct = 0
    total = 0

    for _, row in claims_df.iterrows():
        if pd.isna(row["evidence_doc_id"]) or str(row["evidence_label"]).upper() == "":
            continue

        doc_id = str(int(float(row["evidence_doc_id"])))
        if doc_id not in corpus:
            continue

        paper = corpus[doc_id]
        instruction = str(row["claim"])
        true_label = "ml_relevant" if str(row["evidence_label"]).upper() == "SUPPORT" else "ml_irrelevant"

        result = scorer.classify(instruction, instruction, paper)
        # using claim as both instruction and query for pure validation

        if result == true_label or (result == "ml_less_relevant" and true_label == "ml_relevant"):
            correct += 1
        total += 1

    print(f"Accuracy on validation set: {correct}/{total} = {correct/total:.2%}")


if __name__ == "__main__":
    test_basic_scoring()
    test_no_instruction()
    test_edge_cases()
    test_with_scifact()
    print("\n=== All tests done ===")

