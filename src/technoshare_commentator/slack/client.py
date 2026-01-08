from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from ..config import get_settings
from ..log import get_logger

logger = get_logger("slack_client")
settings = get_settings()

class SlackClientWrapper:
    def __init__(self):
        self.client = WebClient(token=settings.SLACK_BOT_TOKEN)

    @retry(
        retry=retry_if_exception_type(SlackApiError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def post_reply(self, channel_id: str, thread_ts: str, text: str):
        """
        Posts a threaded reply with Slack mrkdwn formatting enabled.
        Note: If thread_ts is None, it posts a top-level message (usually we want thread).
        """
        try:
            self.client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts,
                text=text,
                mrkdwn=True,  # Enable Slack mrkdwn formatting
                unfurl_links=False, # cleaner replies
                unfurl_media=False
            )
        except SlackApiError as e:
            if e.response["error"] == "ratelimited":
                logger.warning("Slack rate limited, retrying...")
                raise e
            logger.error(f"Slack API error: {e.response['error']}")
            raise

    def get_latest_messages(self, channel_id: str, limit: int = 5):
        """
        Reads the last few messages from a channel.
        Requires 'conversations.history' scope.
        """
        try:
            response = self.client.conversations_history(
                channel=channel_id,
                limit=limit
            )
            return response["messages"]
        except SlackApiError as e:
            logger.error(f"Error fetching history: {e.response['error']}")
            raise

    def post_payload(self, payload: dict):
        """
        Post a prepared payload (dict) directly to Slack using chat_postMessage.
        This is useful when callers want to use Block Kit blocks.
        """
        try:
            self.client.chat_postMessage(**payload)
        except SlackApiError as e:
            if e.response["error"] == "ratelimited":
                logger.warning("Slack rate limited, retrying...")
                raise e
            logger.error(f"Slack API error: {e.response['error']}")
            raise

slack_client = SlackClientWrapper()
