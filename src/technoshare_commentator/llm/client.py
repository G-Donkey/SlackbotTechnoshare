from openai import OpenAI
from ..config import get_settings

settings = get_settings()

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

llm_client = LLMClient()
