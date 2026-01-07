from dotenv import load_dotenv
import uuid
import datetime
from technoshare_commentator.slack.client import slack_client
from technoshare_commentator.pipeline.run import pipeline
from technoshare_commentator.config import get_settings

def run():
    print("Loading environment...")
    load_dotenv()
    settings = get_settings()
    channel_id = settings.TECHNOSHARE_CHANNEL_ID
    
    print(f"Fetching latest message from channel {channel_id}...")
    # Fetch 1 latest message
    messages = slack_client.get_latest_messages(channel_id, limit=1)
    
    if not messages:
        print("No messages found in channel.")
        return

    latest_msg = messages[0]
    text = latest_msg.get("text", "")
    ts = latest_msg.get("ts")
    user = latest_msg.get("user")
    
    print(f"Found message from user {user} at {ts}:")
    print(f"Text: {text[:100]}...")
    
    if "http" not in text:
        print("Latest message does not appear to contain a URL. Warning: Pipeline might skip it.")
    
    # Generate a job ID
    job_id = str(uuid.uuid4())
    
    print(f"Starting pipeline job {job_id}...")
    pipeline.process_job(job_id, channel_id, ts, text)
    print("Pipeline execution finished.")

if __name__ == "__main__":
    run()
