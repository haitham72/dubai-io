"""Worker process for the two local scoring models. Runs under an interpreter that has torch + transformers
(the API venv is deliberately light), talking JSON lines over stdin / stdout. It must not import `app.*`.

  request : {"texts": ["...", ...]}
  response: {"results": [{"polarity": {...}, "sentiment": -1..1, "emotions": {label: score >= threshold}}, ...]}
            or {"error": "..."}
First line out is {"ready": true} once both models are loaded.

Models (env): LAB_SENTIMENT_MODEL  cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual   (polarity)
              LAB_EMOTION_MODEL    AnasAlokla/multilingual_go_emotions                          (multi-label, sigmoid)
              LAB_EMOTION_THRESHOLD 0.45
"""
import json
import os
import sys

LABEL_FALLBACK = {"label_0": "negative", "label_1": "neutral", "label_2": "positive"}


def main() -> None:
    out = sys.stdout
    sys.stdout = sys.stderr  # library chatter must never corrupt the JSON channel
    from transformers import pipeline

    sentiment = pipeline("text-classification", model=os.environ["LAB_SENTIMENT_MODEL"], top_k=None)
    emotion = pipeline("text-classification", model=os.environ["LAB_EMOTION_MODEL"], top_k=None,
                       function_to_apply="sigmoid")
    threshold = float(os.environ.get("LAB_EMOTION_THRESHOLD", "0.45"))
    out.write(json.dumps({"ready": True}) + "\n")
    out.flush()
    for raw in sys.stdin:
        try:
            texts = [(t or ".")[:1500] for t in json.loads(raw)["texts"]]
            sent = sentiment(texts, truncation=True, max_length=256, batch_size=16)
            emo = emotion(texts, truncation=True, max_length=256, batch_size=16)
            results = []
            for s, e in zip(sent, emo):
                pol = {}
                for d in s:
                    label = d["label"].lower()
                    pol[LABEL_FALLBACK.get(label, label)] = float(d["score"])
                results.append({
                    "polarity": {k: round(v, 3) for k, v in pol.items()},
                    "sentiment": round(pol.get("positive", 0.0) - pol.get("negative", 0.0), 3),
                    "emotions": {d["label"].lower(): round(float(d["score"]), 2) for d in e
                                 if float(d["score"]) >= threshold and d["label"].lower() != "neutral"},
                })
            out.write(json.dumps({"results": results}) + "\n")
        except Exception as exc:  # report, never die silently
            out.write(json.dumps({"error": f"{type(exc).__name__}: {exc}"}) + "\n")
        out.flush()


if __name__ == "__main__":
    main()
