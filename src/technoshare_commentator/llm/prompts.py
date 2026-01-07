import yaml
from pathlib import Path

def load_prompt(name: str) -> str:
    # Prioritize .yaml for structured prompts
    yaml_path = Path("data/prompts") / f"{name}.yaml"
    if yaml_path.exists():
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)
            return data.get("content", "")
            
    # Fallback to .md
    md_path = Path("data/prompts") / f"{name}.md"
    if md_path.exists():
        with open(md_path, "r") as f:
            return f.read()
            
    raise FileNotFoundError(f"Prompt {name} not found as .yaml or .md")
