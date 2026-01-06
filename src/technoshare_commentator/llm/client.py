import json
from openai import OpenAI
from ..config import get_settings
from ..retrieval.fetch import fetcher
from ..retrieval.extract import extract_content

settings = get_settings()

def get_web_content(url: str) -> str:
    """Fetch and extract main text from a URL."""
    try:
        html = fetcher.fetch_url(url)
        data = extract_content(html, url)
        return data.get("text", "No content found.")
    except Exception as e:
        return f"Error fetching {url}: {str(e)}"

class LLMClient:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def run_structured(self, prompt: str, schema_model: type, model: str = "gpt-4o"):
        completion = self.client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            response_format=schema_model,
        )
        return completion.choices[0].message.parsed

    def run_with_tools(self, prompt: str, schema_model: type, model: str = "gpt-4o"):
        """Run a completion with tool-calling capabilities (e.g. search/browse)."""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search",
                    "description": "Searches or reads the content of a specific URL to gather information.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "The URL to read content from."}
                        },
                        "required": ["url"]
                    }
                }
            }
        ]
        
        messages = [{"role": "user", "content": prompt}]
        
        # Initial call to see if model wants to use tools
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        
        response_message = response.choices[0].message
        messages.append(response_message)
        
        if response_message.tool_calls:
            for tool_call in response_message.tool_calls:
                if tool_call.function.name == "search":
                    args = json.loads(tool_call.function.arguments)
                    content = get_web_content(args["url"])
                    
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": "search",
                        "content": content
                    })
            
            # Final call to get the structured result
            # We use .parse here for the final structured output
            completion = self.client.beta.chat.completions.parse(
                model=model,
                messages=messages,
                response_format=schema_model
            )
            return completion.choices[0].message.parsed
            
        # fallback if no tool was called
        completion = self.client.beta.chat.completions.parse(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format=schema_model
        )
        return completion.choices[0].message.parsed

llm_client = LLMClient()
