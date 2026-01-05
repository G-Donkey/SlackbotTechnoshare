# Running Local Tunnel

You need a public URL for Slack to send events to your local machine.

## How to get your tunnel URL (ngrok SDK example)

Since you've added `ngrok` as a python dependency, you can use the SDK instead of installing the global CLI:

1.  **Add your Authtoken** to `.env`:
    `NGROK_AUTHTOKEN=your_token_here` (Get one at [dashboard.ngrok.com](https://dashboard.ngrok.com/get-started/your-authtoken))
2.  **Start your ingest server** in one terminal:
    ```bash
    uv run uvicorn technoshare_commentator.main_ingest:app --port 3000
    ```
3.  **Run the tunnel script** in another terminal:
    ```bash
    uv run python scripts/run_ngrok.py
    ```
4.  **Copy the URL** that appears (e.g., `https://1234.ngrok-free.app`).
5.  **Update Slack**: Use `https://<url>/slack/events`.

## Alternative: Global ngrok CLI
If you want to use the `ngrok` command directly in your shell:
1.  **Install**: `brew install ngrok`
2.  **Run**: `ngrok http 3000`

## Alternative: cloudflared
If you prefer Cloudflare Tunnels:
```bash
cloudflared tunnel --url http://localhost:3000
```
Then use the provided `.trycloudflare.com` URL.
