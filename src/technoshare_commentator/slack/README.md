# Slack Integration Module

This module handles all Slack-related operations for the TechnoShare Commentator bot using **Socket Mode**. It listens for events via WebSocket, posts replies, and provides utility functions for interacting with the Slack API.

---

## Architecture Overview

The Slack integration supports **two modes of operation**:

### Mode 1: Socket Mode Event Listener (Automated)
Real-time event processing via WebSocket connection:

1. **Socket Listener** (`main_socket.py`) - Maintains WebSocket connection to Slack, receives events in real-time
2. **Database Queue** - Stores jobs for processing
3. **Worker Process** (`main_worker.py`) - Polls database and executes pipeline
4. **Slack Client** - Posts replies back to Slack

```
Slack WebSocket → [Socket Listener] → [Database Queue] → [Worker] → [Pipeline] → Slack API (post)
```

**Benefits:**
- No public URL needed (no ngrok/tunneling)
- No signature verification complexity
- Works behind firewalls/NAT
- Instant event delivery

### Mode 2: Manual Script Execution
Run pipeline on-demand:

```bash
python scripts/run_pipeline_on_latest.py
```

```
[Script] → Slack API (fetch) → [Pipeline] → Slack API (post)
```

---

## How It Works: Socket Mode (Automated)

### 1. **Socket Connection** (`main_socket.py`)

The Socket Mode listener establishes a persistent WebSocket connection to Slack:

1. **Initialize Slack Bolt App**:
   ```python
   app = App(token=SLACK_BOT_TOKEN)  # No signing secret needed
   ```

2. **Connect via Socket Mode Handler**:
   ```python
   handler = SocketModeHandler(app, SLACK_APP_TOKEN)
   handler.start()  # Maintains persistent connection
   ```

3. **Receive Events in Real-Time**:
   - Slack pushes events through the WebSocket
   - No polling, no HTTP server needed
   - Authenticated via app-level token

### 2. **Event Handling** (`main_socket.py` - `@app.event("message")`)

When a message is posted in the monitored channel:

**Filters Applied:**
- ✓ **Channel Filter**: Only processes `TECHNOSHARE_CHANNEL_ID`
- ✓ **Bot Filter**: Ignores `bot_message` subtype or messages with `bot_id`
- ✓ **Subtype Filter**: Ignores `message_changed` and `message_deleted` events
- ✓ **URL Filter**: Only processes messages containing URLs

**Event Structure:**
```python
{
    "channel": "C123ABC",
    "ts": "1234567890.123456",
    "thread_ts": "1234567890.123456",  # if in a thread
    "user": "U123ABC",
    "text": "Check out this article: https://..."
}
```

### 3. **Job Queueing**

After filtering:

1. **Extract URLs** from message text using `extract_urls()`
2. **Save to database** via `Repo.save_message()`:
   - Creates job record with status `pending`
   - **Idempotency**: Uses message `ts` as unique key
   - Duplicate messages are detected and skipped
3. **Log result**: "✓ Queued job for message {ts}"

Job record contains:
- `id`: UUID for tracking
- `channel_id`: Where to post the reply
- `message_ts`: Original message timestamp (for threading)
- `text`: Full message text
- `status`: `pending` → `processing` → `done`/`failed`

### 4. **Job Processing** (`main_worker.py`)

The worker runs as a **separate process**:

1. **Polls database** every 5 seconds via `Repo.claim_next_job()`
2. **Claims job** by atomically updating status to `processing`
3. **Invokes pipeline**:
   ```python
   pipeline.process_job(job_id, channel_id, message_ts, text)
   ```
4. **Continues polling** for next job

### 5. **Pipeline Execution** (Both Modes)

Whether triggered by Socket Mode or manual script, `pipeline/run.py` handles processing:

1. **URL Extraction**: Identifies target URL from message text
2. **Evidence Retrieval**: Fetches content via adapter (ArXiv, GitHub, generic web)
3. **Stage A (Fact Extraction)**: Uses LLM to extract key facts
4. **Stage B (Reply Composition)**: Uses LLM to compose helpful comment
5. **Quality Gates**: Validates reply meets quality standards
6. **Slack Posting**: Sends formatted reply back to channel

### 6. **Reply Posting** (Both Modes)

The final step posts the bot's reply to Slack:

1. **Render to Slack format** (`rendering/slack_format.py`):
   - Converts structured data to Slack mrkdwn syntax
   - Formats links, bold/italic text, lists, code blocks

2. **Build payload** (`post_blocks.py`):
   ```python
   {
       "channel": "C123ABC",
       "thread_ts": "1234567890.123456",  # reply in thread
       "text": "**Key Points**\n- Point 1\n- Point 2...",
       "mrkdwn": True,
       "unfurl_links": False,
       "unfurl_media": False
   }
   ```

3. **Post via Slack API** (`client.py`):
   - Uses `slack_sdk.WebClient.chat_postMessage()`
   - Includes **retry logic** with exponential backoff (3 attempts)
   - Handles rate limiting automatically
   - Posts as threaded reply (preserves context)

---

## Module Components

### `main_socket.py` - Socket Mode Listener

**Main entry point for automated event processing**

- **`@app.event("message")`**: Handler for message events
- **`main()`**: Initializes database and starts Socket Mode handler
- **Filtering logic**: Channel, bot, subtype, and URL filters
- **Job queueing**: Saves valid messages to database

### `client.py` - Slack API Client

**SlackClientWrapper**: Wraps `slack_sdk.WebClient` with additional features

- **`post_reply(channel_id, thread_ts, text)`**: Posts a simple threaded reply
- **`get_latest_messages(channel_id, limit)`**: Fetches recent messages (for manual script)
- **`post_payload(payload)`**: Posts a pre-built payload (for Block Kit messages)
- **Retry logic**: 3 attempts with exponential backoff on rate limits

### `parse.py` - Event Normalization (Legacy)

**Note**: With Socket Mode, most filtering is done in `main_socket.py`. This module is kept for compatibility with manual scripts.

### `post_blocks.py` - Payload Builders

**`build_post_payload(channel, text, thread_ts)`**: Creates chat.postMessage payload

- Enables mrkdwn formatting
- Disables link/media unfurling
- Supports threaded replies

---

## Configuration

Required environment variables (in `.env` or environment):

```bash
# Slack Authentication (Socket Mode)
SLACK_BOT_TOKEN=xoxb-...           # Bot User OAuth Token
SLACK_APP_TOKEN=xapp-...           # App-Level Token (starts with xapp-)
TECHNOSHARE_CHANNEL_ID=C123ABC     # Channel ID to monitor

# OpenAI
OPENAI_API_KEY=sk-...              # For pipeline LLM calls

# Required Bot Token Scopes (OAuth & Permissions)
# - channels:history (read messages)
# - chat:write (post messages)

# Required App-Level Token (Socket Mode)
# - connections:write (establish WebSocket connection)
```

### Setting Up Socket Mode

1. **Go to [api.slack.com/apps](https://api.slack.com/apps)** → Your App

2. **Enable Socket Mode**:
   - Settings → Socket Mode → Enable Socket Mode
   - Generate an app-level token with `connections:write` scope
   - Copy the token (starts with `xapp-`)
   - Add to `.env` as `SLACK_APP_TOKEN=xapp-...`

3. **Configure Bot Scopes**:
   - OAuth & Permissions → Bot Token Scopes
   - Add: `channels:history`, `chat:write`

4. **Subscribe to Events**:
   - Event Subscriptions → Enable Events (no URL needed!)
   - Subscribe to bot events: `message.channels`

5. **Install App to Workspace**:
   - OAuth & Permissions → Install to Workspace
   - Copy Bot User OAuth Token (starts with `xoxb-`)
   - Add to `.env` as `SLACK_BOT_TOKEN=xoxb-...`

6. **Invite Bot to Channel**:
   ```
   /invite @yourbot
   ```

---

## Running the System

### Socket Mode (Automated Event Processing)

Run both the Socket Mode listener and worker:

```bash
# Terminal 1: Start Socket Mode listener
python -m src.technoshare_commentator.main_socket

# Terminal 2: Start worker (processes jobs from queue)
python -m src.technoshare_commentator.main_worker
```

**What happens:**
1. Socket listener maintains WebSocket connection to Slack
2. When someone posts a message with URL → saved to database
3. Worker picks up job and runs pipeline
4. Bot posts reply in thread

**No public URL needed!** Works from your laptop, behind firewall, etc.

---

### Manual Script (On-Demand Processing)

Run pipeline directly on latest message:

```bash
# Disable MLflow tracking (optional)
export MLFLOW_ENABLE_TRACKING=false

# Run on latest message
python scripts/run_pipeline_on_latest.py
```

**What this does:**
- Fetches most recent message from channel via API
- Runs pipeline synchronously
- Posts reply back to Slack
- Bypasses Socket Mode and database queue

---

## Data Flow Diagrams

### Socket Mode Flow (Automated)

```
┌─────────────────────────────────────────────────────────┐
│  Slack Platform (User posts message with URL)          │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ WebSocket push (Socket Mode)
                     ▼
          ┌──────────────────────┐
          │  main_socket.py      │  • Persistent WebSocket
          │  (@app.event)        │  • Filter events
          └──────────┬───────────┘  • Extract URLs
                     │
                     │ save_message()
                     ▼
          ┌──────────────────────┐
          │  SQLite Database     │  Job queue (pending)
          └──────────┬───────────┘
                     │
                     │ Poll every 5s (claim_next_job)
                     ▼
          ┌──────────────────────┐
          │  main_worker.py      │  Claim job atomically
          │  (Background)        │  Set status=processing
          └──────────┬───────────┘
                     │
                     │ process_job()
                     ▼
          ┌──────────────────────┐
          │  pipeline/run.py     │  5-stage pipeline:
          │  (Orchestrator)      │  • Extract URL
          └──────────┬───────────┘  • Fetch evidence
                     │              • Analysis (LLM)
                     │              • Quality gates
                     │              • Slack posting
                     ▼
          ┌──────────────────────┐
          │  post_analysis.py    │  Render to mrkdwn
          │  (Formatter)         │  Build payload
          └──────────┬───────────┘
                     │
                     │ post_payload()
                     ▼
          ┌──────────────────────┐
          │  client.py           │  POST to Slack API
          │  (slack_sdk)         │  Threaded reply
          └──────────┬───────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  Slack Thread        │  Bot comment visible
          └──────────────────────┘
```

### Manual Script Flow

```
┌────────────────────────────────────────────────┐
│  run_pipeline_on_latest.py (Manual)            │
└─────────────┬──────────────────────────────────┘
              │
              │ get_latest_messages()
              ▼
   ┌──────────────────────┐
   │  Slack API           │  Fetch recent messages
   │  (conversations.     │  from channel
   │   history)           │
   └──────────┬───────────┘
              │
              │ process_job()
              ▼
   ┌──────────────────────┐
   │  pipeline/run.py     │  7-stage pipeline
   └──────────┬───────────┘
              │
              ▼
   ┌──────────────────────┐
   │  client.py           │  POST to Slack API
   └──────────┬───────────┘
              │
              ▼
   ┌──────────────────────┐
   │  Slack Thread        │  Bot comment visible
   └──────────────────────┘
```

---

## Error Handling

- **Socket disconnection**: Automatically reconnects via `SocketModeHandler`
- **Duplicate message**: Logs "Duplicate message" and skips (idempotency via `ts`)
- **No URLs found**: Logs and ignores without queueing
- **Pipeline failure**: Job marked as `failed` in database with error message
- **Slack API errors**: Retried up to 3 times with exponential backoff
- **Rate limiting**: Automatically retried by tenacity decorator

---

## Key Design Decisions

1. **Socket Mode over HTTP webhooks**: Simpler local development, no public URL needed
2. **Separate listener and worker**: Socket listener queues jobs; worker processes them
3. **Database queue**: Decouples event reception from processing (resilience)
4. **Idempotency**: Message `ts` as unique key prevents duplicate processing
5. **Threaded replies**: All bot responses are in threads to avoid channel noise
6. **URL filtering**: Early filtering reduces unnecessary processing
7. **Plain text with mrkdwn**: Avoids Block Kit 3000-char limit

---

## Testing

### Test Socket Mode Connection

```bash
# Start the listener
python -m src.technoshare_commentator.main_socket
```

You should see:
```
INFO:socket_listener:Starting Socket Mode listener...
INFO:socket_listener:Monitoring channel: C123ABC
⚡️ Bolt app is running!
```

Post a message with URL in your channel and check logs for:
```
INFO:socket_listener:✓ Queued job for message 1234567890.123456 (URL: https://...)
```

### Test Full Pipeline

```bash
# Terminal 1: Socket listener
python -m src.technoshare_commentator.main_socket

# Terminal 2: Worker
python -m src.technoshare_commentator.main_worker

# Terminal 3: Check database
sqlite3 db.sqlite "SELECT * FROM jobs WHERE status='pending';"
```

### Run Integration Tests

```bash
pytest tests/integration/test_slack_integration.py
```

### Run Unit Tests

```bash
# Test Slack client
pytest tests/unit/test_slack_client.py

# Test formatting
pytest tests/test_slack_format.py
```

---

## Troubleshooting

**Problem**: "Invalid app token" or connection fails
- Verify `SLACK_APP_TOKEN` starts with `xapp-`
- Check Socket Mode is enabled in app settings
- Confirm app-level token has `connections:write` scope

**Problem**: Not receiving events
- Verify bot is invited to channel (`/invite @bot`)
- Check `TECHNOSHARE_CHANNEL_ID` matches actual channel ID
- Confirm Event Subscriptions has `message.channels` enabled
- Check bot token has `channels:history` scope

**Problem**: Socket Mode listener crashes
- Check logs for authentication errors
- Verify both `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN` are set
- Ensure tokens haven't expired or been revoked

**Problem**: Worker not processing jobs
- Check worker process is running
- Look for `pending` jobs: `sqlite3 db.sqlite "SELECT * FROM jobs;"`
- Check worker logs for exceptions
- Verify database file exists and is writable

**Problem**: Messages posted but not in thread
- Verify `thread_ts` parameter is passed correctly
- For top-level messages, `thread_ts` should be message's own `ts`

**Problem**: Bot creates duplicate replies
- Database idempotency should prevent this
- Check for multiple worker instances running
- Verify `message_ts` is being used as unique key

---

## Comparison: Socket Mode vs HTTP Webhooks

| Feature | Socket Mode ✓ | HTTP Webhooks |
|---------|---------------|---------------|
| Public URL needed | ❌ No | ✅ Yes (ngrok, etc.) |
| Signature verification | ❌ No | ✅ Yes (complex) |
| Works behind firewall | ✅ Yes | ❌ No |
| Setup complexity | Low | High |
| Local development | Easy | Requires tunneling |
| Production scaling | Good | Better |
| Connection type | WebSocket (persistent) | HTTP (per-event) |
| Authentication | App-level token | Signing secret |

**For this project**: Socket Mode is ideal for local development and small-scale deployments.

---

## Future Enhancements

- [ ] Support for message edits (handle `message_changed` subtype)
- [ ] React to @mentions directly
- [ ] Support multiple channels via configuration
- [ ] Implement job retry logic for transient failures
- [ ] Add metrics/monitoring for job processing times
- [ ] Support for Slack interactive components (buttons, modals)
- [ ] Graceful shutdown handling for Socket Mode
- [ ] Health check endpoint for monitoring
