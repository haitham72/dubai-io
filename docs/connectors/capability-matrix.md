# Capability matrix

Declared in `app/connectors/catalog.py`. `available` in the API is false for `unavailable` rows and for WhatsApp until `WHATSAPP_EVOLUTION_ENABLED`, `EVOLUTION_API_BASE_URL`, and `EVOLUTION_API_KEY` are all set. `outbound: true` still does nothing until the owner approves the exact payload.

`read_history` means the source can be paged. It does not mean one sync downloads a full archive. Attachment `metadata` is a name or mimetype, not the bytes.

| id | category | integration | mode | auth | read | history | attachments | realtime | outbound | content | summary |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `browser_bookmarks` | browser | export_import | export | file_import | true | false | none | none | false | full | No live bookmark API. Import an export you downloaded. |
| `browser_history` | browser | export_import | export | file_import | true | false | none | none | false | full | No live browser-history API. Import an export you downloaded. |
| `browser_saved_pages` | browser | export_import | export | file_import | true | false | none | none | false | full | No live saved-pages API. Import an export you downloaded. |
| `google_calendar` | calendar | official_api | live | oauth_bearer | true | true | none | polling | false | full | Official Google Calendar read of the primary calendar. |
| `outlook_calendar` | calendar | official_api | live | oauth_bearer | true | true | none | polling | false | full | Official Outlook calendar read through Microsoft Graph. |
| `github` | development | official_api | live | api_token | true | true | none | polling | false | full | Official GitHub notification read with a personal access token. |
| `gitlab` | development | official_api | live | api_token | true | true | none | polling | false | full | Official GitLab activity read. |
| `jira` | development | official_api | live | api_token | true | true | none | polling | false | full | Official Jira Cloud read of issues assigned to you. |
| `gmail` | email | official_api | live | oauth_bearer | true | true | metadata | polling | false | full | Official Gmail read API for headers, snippets, and attachment names. |
| `imap` | email | official_api | live | imap_password | true | true | none | polling | false | full | Official IMAP for a mailbox you can log into with an app password. |
| `outlook` | email | official_api | live | oauth_bearer | true | true | none | polling | false | full | Official Microsoft Graph inbox read with delta sync. |
| `dropbox` | files | official_api | live | oauth_bearer | true | true | metadata | polling | false | metadata | Official Dropbox folder listing with cursor continuation. |
| `filesystem` | files | official_api | live | filesystem_path | true | true | content | polling | false | full | Reads a folder you choose on this server. Does not scan the whole disk. |
| `google_drive` | files | official_api | live | oauth_bearer | true | true | metadata | polling | false | metadata | Official Google Drive metadata list. |
| `onedrive` | files | official_api | live | oauth_bearer | true | true | metadata | polling | false | metadata | Official OneDrive metadata list through Microsoft Graph. |
| `finance_provider` | finance | unavailable | unavailable | none | false | false | none | none | false | none | No financial-data provider is configured. Use an imported statement file. |
| `finance_statements` | finance | export_import | export | file_import | true | false | none | none | false | full | Import bank or card statements you exported. No bank is contacted. |
| `saved_media` | media | export_import | export | file_import | true | false | none | none | false | full | Import a media list you supply. Does not scrape a streaming site. |
| `spotify` | media | official_api | live | oauth_bearer | true | true | none | polling | false | metadata | Official Spotify read of your saved tracks. |
| `youtube` | media | official_api | live | oauth_bearer | true | true | none | polling | false | metadata | Official YouTube read of your uploads playlist. Not watch history. |
| `discord` | messaging | official_api | live | bot_token | true | true | none | polling | false | full | Official Discord bot read of one channel you name. Not personal DMs. |
| `signal` | messaging | unavailable | unavailable | none | false | false | none | none | false | none | Signal has no authorized personal API. No unofficial client is included. |
| `slack` | messaging | official_api | live | oauth_bearer | true | true | none | polling | false | full | Official Slack read of conversations the token can access. |
| `telegram` | messaging | official_api | live | bot_token | true | false | none | webhook_or_polling | true | full | Official Telegram bot for messages sent to that bot, not your private history. |
| `whatsapp` | messaging | unofficial | live | qr_linked_device | true | true | metadata | webhook_or_polling | true | full | Optional unofficial WhatsApp link through a self-hosted Evolution API (Baileys). Off by default. |
| `android_notifications` | mobile | unavailable | unavailable | none | false | false | none | none | false | none | Android notification access needs a device app this server does not include. |
| `contacts` | mobile | unavailable | unavailable | none | false | false | none | none | false | none | Contacts stay on the device. This server does not import them. |
| `ios_permitted` | mobile | unavailable | unavailable | none | false | false | none | none | false | none | iOS does not permit this server to read other apps' data. No connector is offered. |
| `linear` | productivity | official_api | live | api_token | true | true | none | polling | false | full | Official Linear read of issues assigned to you. |
| `notion` | productivity | official_api | live | oauth_bearer | true | true | none | polling | false | metadata | Official Notion page list for pages shared with the integration. |
| `todoist` | productivity | official_api | live | api_token | true | true | none | polling | false | full | Official Todoist task read. |
| `trello` | productivity | official_api | live | api_token | true | true | none | polling | false | full | Official Trello card read. |
| `amazon` | shopping | export_import | export | file_import | true | false | none | none | false | full | No consumer Amazon order API. Import a file you exported. |
| `ebay` | shopping | export_import | export | file_import | true | false | none | none | false | full | No buyer purchase-history API is used. Import a file you exported. |
| `noon` | shopping | export_import | export | file_import | true | false | none | none | false | full | No Noon order API. Import a file you exported. |
| `purchase_receipts` | shopping | export_import | export | file_import | true | false | none | none | false | full | Import purchase receipts you already have. No shop is contacted. |
| `instagram` | social | export_import | export | file_import | true | false | none | none | false | full | Personal Instagram DMs are unavailable. A file you exported can be imported. |
| `linkedin` | social | export_import | export | file_import | true | false | none | none | false | full | No personal LinkedIn API. Import a data download you exported. |
| `reddit` | social | official_api | live | oauth_bearer | true | true | none | polling | false | full | Official Reddit read of your saved posts. |
| `x` | social | official_api | live | oauth_bearer | true | false | none | polling | false | full | Official X API for your own recent posts. Direct messages are not available. |

Limitations that are easy to miss:

- Gmail stores the snippet and attachment **names**. It does not download attachment bytes and it does not send.
- Microsoft mail and calendar use Graph delta links, and those links are refused unless the host is `graph.microsoft.com`.
- Jira and self-managed GitLab URLs must be public `https` hosts. Loopback and private addresses are rejected.
- IMAP reads headers and the first 2KB of text over TLS. Revoke deletes the stored password; the app password itself is removed at the mailbox host.
- The local folder refuses the disk root, skips secret-shaped names (`.env`, private keys), and does not follow a symlink out of the folder.
- Dropbox, Drive, and OneDrive list metadata. They do not download file bytes.
- Slack reads conversations the token can see. It does not post.
- Telegram outbound is `sendMessage` to a chat that has talked to the bot, and only after approval. Personal history is not available.
- Reddit is saved posts. X is the user's own posts, not DMs. YouTube is uploads, not watch history. Spotify is saved tracks.
