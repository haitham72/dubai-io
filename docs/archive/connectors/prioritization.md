# Connector priority

Scores are 1–5. Higher is better on every column, including maintainability (a 5 is cheap to keep working). They are judgements for a personal assistant in Dubai, stored in `app/connectors/catalog.py` so the API and this table stay on the same numbers.

| Criterion | What a 5 means |
|---|---|
| user_value | Used in ordinary life or work in Dubai |
| api_access | An authorized API or protocol exists and this server can call it |
| completeness | The call returns the records a person would expect, not a thin slice |
| reliability | The integration survives provider changes |
| privacy_legal | Consent is explicit, terms allow it, and other people's data is limited |
| maintainability | One person can keep it working without reverse engineering |

`live` calls a real API. `export` only stores a file the user uploads. `unavailable` has no builder and cannot sync. WhatsApp is `live` in code and **off** unless its feature flag is set; the score already prices that in.

Build order follows the total, then the id. Official mail, calendar, tasks, and a local folder come before anything unofficial.

| id | mode | user_value | api_access | completeness | reliability | privacy_legal | maintainability | total |
|---|---|---|---|---|---|---|---|---|
| google_calendar | live | 5 | 5 | 5 | 5 | 5 | 5 | 30 |
| gmail | live | 5 | 5 | 4 | 5 | 5 | 5 | 29 |
| filesystem | live | 4 | 5 | 5 | 5 | 4 | 5 | 28 |
| github | live | 4 | 5 | 4 | 5 | 5 | 5 | 28 |
| outlook | live | 5 | 5 | 4 | 5 | 5 | 4 | 28 |
| outlook_calendar | live | 4 | 5 | 5 | 5 | 5 | 4 | 28 |
| todoist | live | 4 | 5 | 4 | 5 | 5 | 5 | 28 |
| google_drive | live | 4 | 5 | 4 | 5 | 5 | 4 | 27 |
| dropbox | live | 3 | 5 | 4 | 5 | 5 | 4 | 26 |
| gitlab | live | 3 | 5 | 4 | 5 | 5 | 4 | 26 |
| linear | live | 3 | 5 | 4 | 5 | 5 | 4 | 26 |
| notion | live | 4 | 5 | 4 | 4 | 5 | 4 | 26 |
| onedrive | live | 3 | 5 | 4 | 5 | 5 | 4 | 26 |
| imap | live | 4 | 5 | 4 | 4 | 4 | 4 | 25 |
| trello | live | 3 | 5 | 4 | 4 | 5 | 4 | 25 |
| jira | live | 3 | 5 | 4 | 4 | 5 | 3 | 24 |
| slack | live | 4 | 5 | 3 | 4 | 4 | 4 | 24 |
| spotify | live | 3 | 5 | 3 | 4 | 5 | 4 | 24 |
| youtube | live | 3 | 5 | 3 | 4 | 5 | 4 | 24 |
| finance_statements | export | 4 | 1 | 3 | 5 | 5 | 5 | 23 |
| purchase_receipts | export | 4 | 1 | 3 | 5 | 5 | 5 | 23 |
| telegram | live | 4 | 3 | 2 | 4 | 4 | 4 | 21 |
| reddit | live | 3 | 4 | 3 | 3 | 4 | 3 | 20 |
| saved_media | export | 2 | 1 | 2 | 5 | 5 | 5 | 20 |
| browser_bookmarks | export | 2 | 1 | 2 | 4 | 4 | 5 | 18 |
| browser_history | export | 3 | 1 | 2 | 4 | 4 | 4 | 18 |
| discord | live | 3 | 3 | 2 | 4 | 3 | 3 | 18 |
| noon | export | 4 | 1 | 2 | 3 | 4 | 4 | 18 |
| amazon | export | 3 | 1 | 2 | 3 | 4 | 4 | 17 |
| browser_saved_pages | export | 2 | 1 | 2 | 4 | 4 | 4 | 17 |
| linkedin | export | 4 | 1 | 2 | 3 | 3 | 4 | 17 |
| ebay | export | 2 | 1 | 2 | 3 | 4 | 4 | 16 |
| x | live | 3 | 3 | 2 | 3 | 3 | 2 | 16 |
| android_notifications | unavailable | 4 | 1 | 2 | 2 | 3 | 2 | 14 |
| whatsapp | live | 5 | 1 | 3 | 2 | 1 | 1 | 13 |
| finance_provider | unavailable | 4 | 1 | 1 | 1 | 3 | 2 | 12 |
| instagram | export | 3 | 1 | 1 | 2 | 2 | 3 | 12 |
| contacts | unavailable | 3 | 1 | 1 | 1 | 2 | 2 | 10 |
| ios_permitted | unavailable | 4 | 1 | 1 | 1 | 2 | 1 | 10 |
| signal | unavailable | 4 | 1 | 1 | 1 | 2 | 1 | 10 |

Notes that move a source down even when user value is high:

- **Telegram** is the official Bot API. It does not see personal chat history.
- **Discord** is an official bot in one channel you name. A user token (self-bot) is not implemented.
- **X** can list the authenticated user's own recent posts. Direct messages are not requested. Access is restricted and often paid.
- **YouTube** reads the uploads playlist, not watch history. Watch history is not in the Data API.
- **Noon, Amazon, eBay, LinkedIn, Instagram** have no authorized personal-inbox or order API for this app. Import is a file the user already downloaded.
- **Signal, iOS, Android notifications, contacts, open banking** have no authorized server integration here. They stay unavailable rather than unofficial.
