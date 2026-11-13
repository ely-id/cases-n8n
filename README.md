# cases-n8n

Automation cases built with n8n and LLMs. Each case keeps its workflow, its test data and the raw output of every run in the same folder, so the numbers can be checked.

## Marketplace review triage

Folder: [`marketplace/`](marketplace/)

An n8n workflow that reads a customer review or support ticket from a fictional delivery marketplace and returns:

- a category: order quality, delay, price or other
- a priority (High, Medium or Low) with a short justification
- the team that should handle it: Quality, Logistics, Payments or Support
- a one-line summary
- a suggested first reply to the customer

The prompt, the cases and the outputs are in Brazilian Portuguese. All data is fictional.

### How it works

```
Form or webhook -> normalize fields -> LLM with structured output -> build row -> Google Sheets
```

- Two entry points: an n8n form for a single case and a webhook for batch runs.
- Model: Gemini 3.5 Flash-Lite at temperature 0.2, with a JSON schema that restricts category, priority and team to fixed values.
- Every row records the prompt version and the model, so each result can be traced to the exact prompt that produced it.

### How it was measured

1. I wrote 8 tie-break rules for the answer key before running anything.
2. I used 40 tuning cases to adjust the prompt: one baseline round (v1), then one round with the rules added (v2). No example from the tuning set went into the prompt.
3. I froze the prompt and recorded its SHA-256 (see [`CONGELAMENTO.md`](marketplace/fluxo-n8n/CONGELAMENTO.md)).
4. I ran 40 unseen test cases exactly once with the frozen prompt.

The cases were generated with AI. I reviewed and signed both answer keys, and the test key was signed before any tuning result existed.

### Results

Agreement with my answer key, 40 cases per run:

| Run | Prompt | Category | Priority | Team | All three |
|---|---|---|---|---|---|
| Tuning, round 1 | v1 baseline | 38/40 (95.0%) | 34/40 (85.0%) | 40/40 (100.0%) | 32/40 (80.0%) |
| Tuning, round 2 | v2 | 40/40 (100.0%) | 39/40 (97.5%) | 40/40 (100.0%) | 39/40 (97.5%) |
| **Test, single run** | **v2, frozen** | **40/40 (100.0%)** | **38/40 (95.0%)** | **39/40 (97.5%)** | **38/40 (95.0%)** |

Only the test row is the result. The tuning rounds are shown because they explain how the prompt changed.

Also measured on the test run:

- **Time per case:** about 1 min 55 s by hand (average of 5 timed cases) against 4.3 s for the workflow (mean of the full request, including the write to the sheet). This compares first drafts and does not count human review.
- **Suggested replies:** 9 of 10 sampled replies met the criteria (polite, uses the first name, 2 to 3 sentences, no promised timeframe, consistent with the classification).

The two test errors:

- **Case 13:** the model read a total delivery time of 1h10 as the delay, which was 40 minutes, and set High instead of Medium.
- **Case 35:** the model treated a complaint about a service fee as a question, and set Low and Support instead of Medium and Payments.

### Limitations

- These numbers measure agreement with an answer key that I signed myself, on fictional cases (n=40). They are not accuracy in production.
- The test set uses new wording, but the same kinds of situations as the tuning set.
- I timed the manual work myself, already knowing the cases, and my replies were shorter than the model's.
- When a customer asks a question, the reply only routes it to support. The workflow has no knowledge base, so answering directly would mean making things up. That is the next step.
- Across the 40 test replies, 2 promised a timeframe that the prompt forbids and 2 had garbled wording.

### Repository layout

```
marketplace/
  casos/        tuning set, test set and the tie-break rules
  fluxo-n8n/    workflow export, prompts and the freeze record
  scripts/      batch runner
  resultados/   raw output of every run
```

File and column names are in Portuguese. A short glossary:

| Portuguese | English |
|---|---|
| ajuste | tuning set |
| prova | test set |
| gabarito | answer key |
| regras de desempate | tie-break rules |
| triagens | triage rows (the sheet tab) |
| teste de fumaça | smoke test |

### Running it

You need n8n (tested on 2.45.6), a Gemini API credential, a Google Sheets credential and Python 3. The script uses only the standard library.

1. Import [`triador-v2-publico.json`](marketplace/fluxo-n8n/triador-v2-publico.json) into n8n.
2. Set your own credentials on the Gemini node and on the Google Sheets node.
3. In the Google Sheets node, replace `SUBSTITUA_PELO_ID_DA_SUA_PLANILHA` with your spreadsheet ID. The spreadsheet needs a tab named `triagens`.
4. Publish the workflow.
5. From `marketplace/`, run the test set:

```sh
python3 scripts/enviar_lote.py casos/prova-40-v2.csv --pausa 5 --timeout 180
```

The script sends one case at a time to `POST /webhook/review-atendimento-lote`, refuses to run if any row of the answer key is unsigned, never retries on its own and writes `resultados/resultado-<lote>-<date>.csv`. The form is served at `/form/review-atendimento`.

### How this was built

I designed the measurement, signed the answer keys and made the decisions. An AI coding agent (Claude Code) did the n8n and scripting work. A separate AI agent checked each step against the raw data and recomputed every number before it was accepted.
