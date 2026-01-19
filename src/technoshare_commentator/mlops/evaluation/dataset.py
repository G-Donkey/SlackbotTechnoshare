"""
Evaluation dataset management for TechnoShare Commentator.
Handles loading, storing, and managing evaluation examples.
"""
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field


class EvalExample(BaseModel):
    """A single evaluation example."""
    id: str = Field(..., description="Unique identifier for the example")
    url: str = Field(..., description="URL to evaluate")
    slack_text: str = Field(..., description="Original Slack message text")
    expected_theme: Optional[str] = Field(None, description="Expected theme classification")
    notes: Optional[str] = Field(None, description="Additional notes about this example")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")


class EvalDataset(BaseModel):
    """Collection of evaluation examples."""
    name: str = Field(..., description="Dataset name")
    description: Optional[str] = Field(None, description="Dataset description")
    examples: List[EvalExample] = Field(default_factory=list, description="Evaluation examples")
    version: str = Field("1.0", description="Dataset version")
    
    def add_example(self, example: EvalExample):
        """Add an example to the dataset."""
        self.examples.append(example)
    
    def get_by_id(self, example_id: str) -> Optional[EvalExample]:
        """Get an example by ID."""
        for example in self.examples:
            if example.id == example_id:
                return example
        return None
    
    def filter_by_tags(self, tags: List[str]) -> List[EvalExample]:
        """Filter examples by tags."""
        return [
            example for example in self.examples
            if any(tag in example.tags for tag in tags)
        ]
    
    def save(self, path: Path):
        """Save dataset to JSON file."""
        with open(path, 'w') as f:
            json.dump(self.model_dump(), f, indent=2)
    
    @classmethod
    def load(cls, path: Path) -> 'EvalDataset':
        """Load dataset from JSON file."""
        with open(path, 'r') as f:
            data = json.load(f)
        return cls(**data)
    
    @classmethod
    def create_default(cls) -> 'EvalDataset':
        """Create a default dataset with example entries."""
        dataset = cls(
            name="technoshare_eval",
            description="Evaluation dataset for TechnoShare Commentator",
            version="1.0"
        )
        
        # Add some example entries
        dataset.add_example(EvalExample(
            id="arxiv_example_1",
            url="https://arxiv.org/abs/2401.00001",
            slack_text="Check this out: https://arxiv.org/abs/2401.00001",
            expected_theme="AI/ML",
            notes="ArXiv paper about machine learning",
            tags=["arxiv", "ml"]
        ))
        
        dataset.add_example(EvalExample(
            id="github_example_1",
            url="https://github.com/example/repo",
            slack_text="Interesting repo: https://github.com/example/repo",
            expected_theme="Development Tools",
            notes="GitHub repository",
            tags=["github", "tools"]
        ))
        
        return dataset


def load_or_create_dataset(path: Path) -> EvalDataset:
    """Load existing dataset or create a new one if it doesn't exist."""
    if path.exists():
        return EvalDataset.load(path)
    else:
        dataset = EvalDataset.create_default()
        path.parent.mkdir(parents=True, exist_ok=True)
        dataset.save(path)
        return dataset
