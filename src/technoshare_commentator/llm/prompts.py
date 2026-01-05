from pathlib import Path

def load_prompt(name: str) -> str:
    path = Path("data/prompts") / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt {name} not found")
    with open(path, "r") as f:
        return f.read()
