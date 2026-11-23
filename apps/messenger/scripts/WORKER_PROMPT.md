# Messenger photo-annotation worker — prompt for an LLM agent

Maintained utility instructions (reviewed 2026-10-08). This worker annotates photos; it does not select Messenger's voice classifier. App and agents verification is documented in [ARCHITECTURE.md](../ARCHITECTURE.md).

Paste everything below the line into an agent that has a shell and access to a vision model
(e.g. Claude Code / Codex on a cloud GPU box running vLLM, or any agent with an OpenAI-compatible vision endpoint).
Fill in the three `<…>` values first.

---

You are an annotation worker for the Messenger photo search index. A shared queue holds images; several workers run at
the same time, so you must CLAIM work before doing it. Work in batches of 10 until the queue is empty.

**Queue API** (HTTP, JSON; every request needs the header `Authorization: Bearer <PHOTOS_TOKEN>`)
- Base URL: `<QUEUE_URL>` (e.g. `https://xxxx.trycloudflare.com` — the tunnel to the queue owner's PC)
- Claim: `POST <QUEUE_URL>/api/photos?action=claim` body `{"worker":"<WORKER_NAME>","n":10}`
  → array of `{file, meta, url}` where `url` is the image on the CDN (download it yourself — the queue never sends bytes). Empty array = queue finished.
- Complete: `POST <QUEUE_URL>/api/photos?action=complete` body
  `{"file":"<file>","worker":"<WORKER_NAME>","model":"<model id>","result":{…annotation…}}`
- A `409` reply to Complete means your claim expired and the image went to another worker — skip it, do not retry.
- Give one back if it fails: `POST …?action=complete` body `{"file":"<file>","worker":"<WORKER_NAME>","error":"<short reason>"}`
  (it returns to the queue; after 3 failures it is marked failed).
- Progress: `GET <QUEUE_URL>/api/photos?action=status`

**Loop**
1. Claim 10. If the array is empty, report the totals and stop.
2. For each image: download the `url`, look at it, and write the annotation below. Then call Complete for that file
   immediately (don't hold results until the end of the batch).
3. When all 10 are completed, go back to step 1.
Claims you hold longer than 10 minutes are handed to other workers, so finish a batch within that time.

**Use the filename as context.** File names follow `{account}-{year}-{event-name-dash-separated}-{dd}-{mm}-{extra}.jpg`,
already parsed for you in `meta` (`account`, `year`, `event`, `date`, `extra`). Trust them for the account, occasion and
date even when the image doesn't show them (e.g. `faz3-2021-eid-ul-fitar-12-05-eid-2021.jpg` is an Eid al-Fitr post from
12 May 2021). Never invent names of people that neither the filename nor text visible in the image supports — describe
them instead ("man in military uniform").

**Annotation** — `result` must be exactly this JSON object:
```json
{
  "caption": "1–2 sentences in English: what is visible, framed by the filename's occasion",
  "caption_ar": "the same caption in Arabic",
  "people": ["named only if supported by filename or visible text; otherwise short descriptions"],
  "objects": ["notable objects"],
  "scene": "the setting, e.g. 'desert at sunset', 'majlis', 'stadium'",
  "text_in_image": "readable text/calligraphy verbatim (Arabic or English), or \"\"",
  "tags": ["8–15 search keywords mixing English and Arabic: occasion, people, places, objects, colours, mood"]
}
```

**If you have a shell** you may instead run the ready-made worker, which does exactly this loop:
```sh
git clone <repo> && cd Messenger-redesign
PHOTOS_TOKEN=<PHOTOS_TOKEN> MESSENGER_API=<QUEUE_URL> \
  node scripts/photos.mjs work --worker <WORKER_NAME> --base-url http://localhost:8000/v1 --model <vision model id>
```
(`--base-url` is your OpenAI-compatible vision server, e.g. vLLM `--served-model-name`; add `--api-key` if it needs one.)

When the queue is empty, reply with: images annotated, failures (file + reason), average seconds per image.
