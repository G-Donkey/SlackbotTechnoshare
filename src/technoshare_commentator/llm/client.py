"""OpenAI client wrapper with tool support.

Provides structured output parsing with optional tool calls
for dynamic web content retrieval during LLM inference.
"""

import json
from typing import TypeVar, Generic, List, Optional, Union
from openai import OpenAI
from pydantic import BaseModel
from ..config import get_settings
from ..retrieval.fetch import fetcher
from ..retrieval.extract import extract_content

settings = get_settings()

T = TypeVar("T")

class RunMeta(BaseModel):
    tool_calls: List[str]
    sources: List[str]
    model: str

class RunResponse(BaseModel, Generic[T]):
    parsed: T
    meta: RunMeta

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

    def run_with_tools(self, prompt: str, schema_model: type[T], model: str = "gpt-4o", return_meta: bool = False) -> Union[T, RunResponse[T]]:
        """
        Run a completion with tool-calling capabilities.
        If return_meta=True, returns RunResponse[T] with metadata.
        """
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
        used_tools = []
        used_sources = []
        
        # Initial call
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
                used_tools.append(tool_call.function.name)
                
                if tool_call.function.name == "search":
                    args = json.loads(tool_call.function.arguments)
                    url = args["url"]
                    used_sources.append(url)
                    content = get_web_content(url)
                    
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": "search",
                        "content": content
                    })
            
            # Final call to get structured result
            completion = self.client.beta.chat.completions.parse(
                model=model,
                messages=messages,
                response_format=schema_model
            )
            parsed = completion.choices[0].message.parsed
        else:
            # Fallback if no tool called (direct parse of original prompt or response?)
            # Actually if response_message content is present, use it? 
            # Similar to logic before: force a parse run.
            completion = self.client.beta.chat.completions.parse(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format=schema_model
            )
            parsed = completion.choices[0].message.parsed

        if return_meta:
            return RunResponse(
                parsed=parsed,
                meta=RunMeta(
                    tool_calls=used_tools,
                    sources=used_sources,
                    model=model
                )
            )
        return parsed

llm_client = LLMClient()
