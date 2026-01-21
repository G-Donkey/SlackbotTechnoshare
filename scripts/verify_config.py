#!/usr/bin/env python3
"""
Quick test script to verify Socket Mode connection.
Run this to ensure your Slack app is properly configured for Socket Mode.
"""
from dotenv import load_dotenv
import os

load_dotenv()

def check_env():
    """Check if required environment variables are set."""
    required = {
        "SLACK_BOT_TOKEN": "Bot User OAuth Token (xoxb-...)",
        "SLACK_APP_TOKEN": "App-Level Token for Socket Mode (xapp-...)",
        "TECHNOSHARE_CHANNEL_ID": "Channel ID to monitor (C...)",
    }
    
    print("=" * 60)
    print("Socket Mode Configuration Check")
    print("=" * 60)
    
    all_good = True
    for var, description in required.items():
        value = os.getenv(var)
        if value:
            # Mask the token for security
            if "TOKEN" in var:
                masked = value[:8] + "..." if len(value) > 8 else "***"
                print(f"✓ {var}: {masked}")
            else:
                print(f"✓ {var}: {value}")
        else:
            print(f"✗ {var}: NOT SET ({description})")
            all_good = False
    
    print("=" * 60)
    
    if all_good:
        print("\n✓ All required environment variables are set!")
        print("\nNext steps:")
        print("1. Run Socket Mode listener:")
        print("   python -m src.technoshare_commentator.main_socket")
        print("\n2. In another terminal, run the worker:")
        print("   python -m src.technoshare_commentator.main_worker")
        print("\n3. Post a message with a URL in your Slack channel")
        print("   and watch the logs!")
    else:
        print("\n✗ Some environment variables are missing.")
        print("Please add them to your .env file.")
        print("\nExample .env:")
        print("SLACK_BOT_TOKEN=xoxb-your-bot-token")
        print("SLACK_APP_TOKEN=xapp-your-app-token")
        print("TECHNOSHARE_CHANNEL_ID=C123ABC")
        print("OPENAI_API_KEY=sk-your-key")
    
    print()

if __name__ == "__main__":
    check_env()
