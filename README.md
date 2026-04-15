# RFx Proposal Coverage Analyzer

A local tool for checking how well a proposal draft covers the requirements in an RFP or RFQ.

## Project summary

This project focuses on a common RFx review workflow for bid and proposal teams.

The app:
- ingests an RFP, RFQ, or RFI plus a draft proposal
- extracts requirement-like statements from the buyer document
- chunks the proposal into reviewable sections
- compares requirements against proposal content
- labels each requirement as `Covered`, `Partial`, or `Missing`
- highlights high-risk gaps and exports the review as CSV

## Current status

The app currently supports:
- upload an RFx document and a proposal draft
- support for `PDF`, `DOCX`, and `TXT`
- document summaries and cleaner preview text
- rule-based requirement extraction from the buyer document
- proposal chunking into reviewable sections
- local coverage matching with `Covered`, `Partial`, and `Missing`
- evidence snippets for each requirement decision
- CSV export of the coverage review
- a small benchmark dataset for local evaluation

## Why this project matters

Bid and proposal teams often need to read long tender documents, understand buyer requirements, and check whether their draft response covers what is being asked. This project is built around that review workflow.

## Run locally on macOS

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the app:

```bash
streamlit run app.py
```

## Demo flow

The fastest way to demo the app:

1. Start the app locally.
2. Click `Load sample files`.
3. Review the following sections:
   - `Loaded Documents`
   - `Review results`
   - `Coverage` tab for status and matched evidence
   - `Requirements` tab for extracted buyer requirements
   - `Proposal Chunks` tab for proposal sections
4. Export the CSV review file.

## Sample files

The repository includes sample documents in:
- `data/sample_rfp/`
- `data/sample_proposal/`

These include:
- a built-in synthetic smart campus RFP/proposal pair for fast testing
- downloaded public RFP PDFs for broader document testing

You can test the interface immediately with the `Load sample files` button.

## Evaluate locally

Run the benchmark:

```bash
python scripts/evaluate_benchmark.py
```

This uses a small hand-labeled dataset in `data/benchmark/coverage_benchmark.json` to report a baseline accuracy score for the coverage matcher.

Current baseline:
- overall accuracy: `0.917`
- benchmark cases: `2`
- labeled requirement items: `12`

## Technical design

Main components:
- `src/loaders.py`: document ingestion and PDF/DOCX/TXT parsing
- `src/analysis.py`: requirement extraction and proposal chunking
- `src/matching.py`: local matching, scoring, and coverage labeling
- `src/benchmark.py`: benchmark runner for local evaluation
- `app.py`: Streamlit review interface

## Limitations

This is a local prototype, not a production RFx system.

Current limitations:
- matching is heuristic and lightweight, not embedding-based
- OCR for scanned PDFs is not yet implemented
- the benchmark dataset is intentionally small
- requirement extraction is rule-based and may miss unusual formatting
