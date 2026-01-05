import ngrok
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def start_tunnel():
    # Use NGROK_AUTHTOKEN from .env if available
    authtoken = os.getenv("NGROK_AUTHTOKEN")
    
    print("Starting ngrok tunnel...")
    # This uses the official ngrok-python SDK
    # It will look for the authtoken in NGROK_AUTHTOKEN env var or ~/.ngrok2/ngrok.yml
    try:
        listener = await ngrok.forward(3000, authtoken=authtoken)
        print(f"\n[SUCCESS] Tunnel established!")
        print(f"Public URL: {listener.url()}")
        print(f"Slack Request URL: {listener.url()}/slack/events")
        print("\nKeep this script running to maintain the tunnel.")
        
        # Keep alive
        while True:
            await asyncio.sleep(3600)
    except Exception as e:
        print(f"[ERROR] Failed to start ngrok: {e}")
        print("Make sure you have NGROK_AUTHTOKEN in your .env file.")
        print("Get one at: https://dashboard.ngrok.com/get-started/your-authtoken")

if __name__ == "__main__":
    asyncio.run(start_tunnel())
