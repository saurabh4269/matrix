# Common workflow commands for matrix
#
# Override CANDIDATES on the command line:
#   make submission CANDIDATES="C:/path/to/candidates.jsonl"

CANDIDATES ?= ./candidates.jsonl
SUBMISSION ?= submissions/team_v2.csv
TEAM_ID    ?= team_v2

.PHONY: help install test sample precompute submission audit score validate compare clean

help:
	@echo "matrix, common commands:"
	@echo ""
	@echo "  make install              install Python + npm dependencies"
	@echo "  make test                 run the 29 unit tests"
	@echo "  make sample               stratify 300 candidates for hand-labelling"
	@echo "  make precompute           pre-compute embeddings + BM25 (one-time, outside ranking budget)"
	@echo "  make submission           rank.py end-to-end → submissions/$(TEAM_ID).csv"
	@echo "  make audit                hallucination check on the current submission"
	@echo "  make validate             official Stage-1 format validator"
	@echo "  make score                NDCG/MAP/P@k against labelled eval set"
	@echo "  make compare A=x.csv B=y.csv  diff two submissions"
	@echo ""
	@echo "Override:"
	@echo "  CANDIDATES=<path to candidates.jsonl>"
	@echo "  TEAM_ID=<your team id>  (controls output filename)"

install:
	pip install -r requirements.txt
	pip install -r sandbox/backend/requirements.txt
	cd sandbox/frontend && npm install

test:
	python -m pytest tests/ -v

sample:
	python -m eval.sample --candidates "$(CANDIDATES)" --out-dir ./eval --per-bucket 50 --seed 42

precompute:
	python -m src.precompute --candidates "$(CANDIDATES)" --out-dir ./data

submission:
	python rank.py --candidates "$(CANDIDATES)" --out submissions/$(TEAM_ID).csv

audit:
	python -m audit.reasoning_audit --candidates "$(CANDIDATES)" --submission $(SUBMISSION)

validate:
	@echo "Running official Stage-1 validator on $(SUBMISSION)…"
	python "$(VALIDATOR_PATH)/validate_submission.py" $(SUBMISSION) || true

score:
	python -m eval.score --labels eval/labelled.jsonl --submission $(SUBMISSION)

compare:
	python -m eval.compare --a $(A) --b $(B)

clean:
	rm -rf __pycache__ */__pycache__ */*/__pycache__ .pytest_cache
	rm -rf sandbox/frontend/dist sandbox/frontend/.vite
