# Dubai IO WhatsApp recall pilot

**Status:** Proposed local experiment  
**Timebox:** One working day once an approved export and a matched graph snapshot are available.

## Decision

Test whether searching the original WhatsApp wording gets Dubai IO to a correct, source-backed answer faster than its existing temporal_note graph recall. Start with exact phrases, IDs, and details the graph may omit. Include paraphrases, corrections, and cross-thread questions to show where each path helps. Use the result to decide whether to add a raw-text fallback to the shared memory retrieval path.

## Research basis

Yang, Shi, and Zhao submitted GrepMem on 18 November 2026. It uses summaries to compact the agent's working context and keeps a separate append-only plain-text history for regex recall. The history preserves details that may only become relevant after compaction. The authors report 95–97% accuracy on ContextBench after RL training Qwen3.5-9B, versus at most 21% for the compared lossy approaches. Those figures describe the paper's benchmark. This pilot applies the retrieval idea to a fixed WhatsApp export with Dubai IO's current answer model. A public project repository exists, and the local prototype can use ripgrep without depending on it. [Paper and implementation details](https://arxiv.org/html/2611.25123v1) · [Project repository](https://github.com/limenlp/GrepMem)

## Main agent handoff

**Consider adding scoped raw-source recall to the shared memory path if the pilot qualifies.** Dubai IO can use temporal_note to identify people, relationships, and changes over time, then recover the original message when a question requires evidence that did not survive extraction. Start with manually exported WhatsApp text.

| Dubai IO query | Benefit of searching the original messages |
| --- | --- |
| “What was the booking reference Omar sent?” | Find the exact reference even when the graph captured only the booking and its date. |
| “What exactly did she say about moving the meeting?” | Retrieve the original wording and nearby messages so the answer can cite the relevant lines. |
| “Was Thursday confirmed or just suggested?” | Bring the original suggestion and later reply into view so the agent can verify the sequence against the graph's current state. |

Use graph recall first. If it yields insufficient evidence and the question or graph result provides a searchable clue, such as a name, date, ID, or phrase, call bounded raw search within the same authorized owner and source scope. Return the original message with stable provenance, such as chat ID and source line range, and let the answer cite it. Abstain if the evidence still falls short. Paraphrases with no searchable clue and multi-hop relationship questions may benefit more from graph recall. A regex hit can supply evidence for an answer, but should never update temporal_note automatically.

Before proposing integration, have the main agent review the pilot's incremental recall, added latency, and scope controls. Reuse the existing authorized source store where available, and verify that source deletion and access revocation also remove search access. If the pilot clears the thresholds below, validate the graph-first fallback on held-out prompts before adding it to the shared retrieval path.

## Setup

1. Pick one small, approved set of manually exported WhatsApp text chats. Keep the original UTF-8 text, including multiline messages, in a local directory outside version control. Record export checksums and the snapshot cutoff. Use a local answer model for private exports or a synthetic fixture if the model runs remotely.
2. Use a scoped temporal_note graph snapshot built from the same chats and cutoff. Reuse the existing recall path and the project's owner and source scoping. If a matched snapshot is unavailable, use an isolated fixture and label the results as fixture-only. Record which source messages the baseline actually processed so ingestion gaps remain visible. [Memory specification §18](../../../plan/Memory/memory.md)
3. Add a small local regex retrieval harness over the approved files. Return chat ID, source line range, timestamp when available, and the full matched message with bounded surrounding context. Preserve Arabic, English, punctuation, and original spelling. Restrict search to the selected chats before matching. Invoke the regex engine directly with a fixed file allowlist, a timeout, and bounded output. Keep queries and raw snippets out of committed reports.

## Run the comparison

1. Freeze 24 prompts and their expected answers before running either path. Use six exact-detail questions, six paraphrase or Arabic/English variant questions, six correction or cross-message questions, and six unanswerable or out-of-scope controls. For answerable prompts, record the supporting message ranges and write questions as a user would ask them. Keep source references and expected answers out of the model prompt.
2. Run each prompt in two fresh sessions, one with raw regex retrieval and one with existing graph recall. Use the same model, answer prompt, evidence budget, and wall-clock deadline. Randomize execution order and give both paths the same maximum number of retrieval calls. Log the elapsed time to first sufficient evidence and to final answer, tool calls, tokens, and evidence references. A path that times out, abstains on an answerable prompt, or answers incorrectly has no winning time.
3. Score responses with the path labels hidden. Require the answer and its cited evidence to agree with the expected result. For corrections, require the answer to distinguish the earlier statement from the later update. Controls pass when the path abstains and reveals no out-of-scope information. Report paired wins, ties, and misses by question type. Tag misses as ingestion gaps, retrieval failures, unsupported answers, or scope failures. Report median matched-pair answer latency when both paths succeed.

## Decision after the pilot

Prototype a scoped fallback if regex recovers at least three verified answers graph recall misses, or if it reduces median answer latency by at least 25% across at least six jointly correct exact-detail queries. Any scope failure disqualifies the pilot from advancing. If neither threshold is met, leave the search harness as a local diagnostic. These are proposed thresholds for this small pilot.

Record the snapshot identifiers, model and budgets, aggregate results, and the decision in a short Markdown report. If the fallback qualifies, use a fresh set of prompts to test the proposed graph-first flow with regex available when graph recall returns insufficient evidence. Keep this evaluation local and read-only with respect to production memory.
