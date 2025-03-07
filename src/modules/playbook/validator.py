from typing import Dict, Any
import yaml
from .config import PlaybookConfig, PlaybookStep


class PlaybookYamlValidator:
    """Validates YAML content and creates PlaybookConfig instances."""

    REQUIRED_FIELDS = {"session", "steps"}
    ALLOWED_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH"}
    REQUIRED_STEP_FIELDS = {"method", "endpoint"}

    @classmethod
    def validate_and_load(cls, yaml_content: str) -> PlaybookConfig:
        """
        Validate YAML content and create a PlaybookConfig instance.
        
        Args:
            yaml_content: The YAML content to validate
            
        Returns:
            PlaybookConfig: The validated playbook configuration
            
        Raises:
            ValueError: If the YAML content is invalid
        """
        try:
            # Parse YAML
            data = yaml.safe_load(yaml_content)
            
            # Basic structure validation
            if not isinstance(data, dict):
                raise ValueError("Playbook must be a YAML object")

            # Check required fields
            missing_fields = cls.REQUIRED_FIELDS - set(data.keys())
            if missing_fields:
                raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

            # Validate steps
            if not isinstance(data["steps"], list):
                raise ValueError("Steps must be a list")

            # Validate each step
            validated_steps: list[PlaybookStep] = []
            for i, step in enumerate(data["steps"], 1):
                if not isinstance(step, dict):
                    raise ValueError(f"Step {i} must be an object")

                # Check required step fields
                missing_step_fields = cls.REQUIRED_STEP_FIELDS - set(step.keys())
                if missing_step_fields:
                    raise ValueError(f"Step {i} missing required fields: {', '.join(missing_step_fields)}")

                # Validate method
                if step["method"].upper() not in cls.ALLOWED_METHODS:
                    raise ValueError(
                        f"Step {i} has invalid method. Allowed methods: {', '.join(cls.ALLOWED_METHODS)}"
                    )

                # Normalize method to uppercase
                step["method"] = step["method"].upper()

                # Create validated step
                validated_steps.append(PlaybookConfig.create_step(step))

            # Create and return config
            return PlaybookConfig(
                session_name=data["session"],
                steps=validated_steps
            )

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {str(e)}")
        except KeyError as e:
            raise ValueError(f"Missing required field: {str(e)}")
        except Exception as e:
            raise ValueError(f"Invalid playbook format: {str(e)}") 