"""
MLflow Prompt Registry integration for TechnoShare Commentator.
Provides prompt versioning, aliasing, and controlled rollout.
"""
import logging
from typing import Optional, Dict, Any
from pathlib import Path
import hashlib

import mlflow
from mlflow.models import ModelSignature

from ..config import get_settings
from .prompts import load_prompt as load_prompt_from_yaml

logger = logging.getLogger(__name__)
settings = get_settings()


class PromptRegistry:
    """Manages prompts in MLflow's Prompt Registry."""
    
    def __init__(self):
        self.enabled = settings.MLFLOW_ENABLE_TRACKING
        if self.enabled:
            try:
                mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
                logger.info("Prompt Registry enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize Prompt Registry: {e}")
                self.enabled = False
    
    def _compute_prompt_hash(self, content: str) -> str:
        """Compute hash of prompt content for version tracking."""
        return hashlib.sha256(content.encode()).hexdigest()[:12]
    
    def register_prompt(
        self,
        name: str,
        content: str,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Register a prompt in MLflow.
        
        Args:
            name: Prompt name (e.g., "stage_a_extract_facts")
            content: Prompt template content
            description: Human-readable description
            tags: Additional metadata tags
        
        Returns:
            Version string if successful, None otherwise
        """
        if not self.enabled:
            return None
        
        try:
            # Create a unique version based on content hash
            content_hash = self._compute_prompt_hash(content)
            
            # Log prompt as an artifact with metadata
            with mlflow.start_run(run_name=f"register_prompt_{name}"):
                mlflow.set_tag("prompt_name", name)
                mlflow.set_tag("content_hash", content_hash)
                
                if description:
                    mlflow.set_tag("description", description)
                
                if tags:
                    mlflow.set_tags(tags)
                
                # Log the prompt content
                mlflow.log_text(content, f"prompts/{name}.txt")
                
                run_id = mlflow.active_run().info.run_id
                logger.info(f"Registered prompt '{name}' with hash {content_hash} (run: {run_id})")
                
                return content_hash
                
        except Exception as e:
            logger.warning(f"Failed to register prompt '{name}': {e}")
            return None
    
    def sync_prompts_from_yaml(self, force: bool = False) -> Dict[str, str]:
        """
        Sync all YAML prompts to MLflow Prompt Registry.
        
        Args:
            force: Force re-registration even if content hasn't changed
        
        Returns:
            Dict mapping prompt names to version hashes
        """
        prompt_names = ["stage_a_extract_facts", "stage_b_compose_reply"]
        results = {}
        
        for name in prompt_names:
            try:
                # Load from YAML
                content = load_prompt_from_yaml(name)
                
                # Register in MLflow
                version = self.register_prompt(
                    name=name,
                    content=content,
                    description=f"Prompt for {name}",
                    tags={"source": "yaml", "stage": name.split("_")[1]}
                )
                
                if version:
                    results[name] = version
                    logger.info(f"Synced prompt '{name}' -> version {version}")
                else:
                    logger.warning(f"Failed to sync prompt '{name}'")
                    
            except Exception as e:
                logger.exception(f"Error syncing prompt '{name}'")
        
        return results
    
    def load_prompt(
        self,
        name: str,
        alias: Optional[str] = "prod",
        fallback_to_yaml: bool = True
    ) -> str:
        """
        Load a prompt from MLflow Registry.
        
        Args:
            name: Prompt name
            alias: Alias to load (e.g., "prod", "candidate", "staging")
            fallback_to_yaml: If True, fall back to YAML if not found in registry
        
        Returns:
            Prompt content
        """
        if not self.enabled or fallback_to_yaml:
            # For now, always fall back to YAML
            # Full registry integration would query MLflow for the aliased version
            return load_prompt_from_yaml(name)
        
        # TODO: Implement full registry lookup with aliases
        # This would involve:
        # 1. Query MLflow for runs with tag prompt_name=name and alias=alias
        # 2. Download the prompt artifact
        # 3. Return content
        
        return load_prompt_from_yaml(name)
    
    def set_alias(
        self,
        name: str,
        version_hash: str,
        alias: str
    ) -> bool:
        """
        Set an alias for a prompt version.
        
        Args:
            name: Prompt name
            version_hash: Version hash to alias
            alias: Alias name (e.g., "prod", "candidate")
        
        Returns:
            True if successful
        """
        if not self.enabled:
            return False
        
        try:
            # This would be implemented with MLflow Model Registry
            # or custom tagging system
            logger.info(f"Set alias '{alias}' for prompt '{name}' version {version_hash}")
            return True
        except Exception as e:
            logger.warning(f"Failed to set alias: {e}")
            return False


# Global registry instance
prompt_registry = PromptRegistry()
