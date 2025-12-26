#!/usr/bin/env python3
"""
Configuration management for Ollama Pipeline.
Loads settings from YAML with environment variable overrides.
"""

import os
import yaml
from pathlib import Path


DEFAULT_CONFIG = {
    'models': {
        'classifier': 'llama3.2:1b',
        'default': 'llama3.2:1b'
    },
    'model_assignments': {
        'code_review': 'llama3.2:1b',
        'documentation': 'llama3.2:1b',
        'bug_analysis': 'llama3.2:1b'
    },
    'prompts': {
        'classify': 'Classify as: code_review, documentation, or bug_analysis'
    },
    'thresholds': {
        'max_response_time': 60,
        'min_response_length': 50
    },
    'cache': {
        'enabled': True,
        'directory': '~/.ollama'
    }
}


def load_config(path='config.yaml'):
    """Load configuration from YAML file with defaults."""
    config = DEFAULT_CONFIG.copy()
    
    config_path = Path(path)
    if config_path.exists():
        with open(config_path) as f:
            file_config = yaml.safe_load(f)
            if file_config:
                # Deep merge for nested dictionaries
                for key, value in file_config.items():
                    if isinstance(value, dict) and key in config:
                        config[key].update(value)
                    else:
                        config[key] = value
        print(f"Loaded configuration from {path}")
    else:
        print(f"Config file {path} not found, using defaults")
    
    # Environment variable overrides
    if os.getenv('OLLAMA_MODEL'):
        config['models']['default'] = os.getenv('OLLAMA_MODEL')
        print(f"Override: OLLAMA_MODEL={os.getenv('OLLAMA_MODEL')}")
    
    if os.getenv('OLLAMA_TIMEOUT'):
        config['thresholds']['max_response_time'] = int(os.getenv('OLLAMA_TIMEOUT'))
        print(f"Override: OLLAMA_TIMEOUT={os.getenv('OLLAMA_TIMEOUT')}")
    
    return config


def get_model_for_task(config, task_type):
    """Get the assigned model for a task type."""
    return config.get('model_assignments', {}).get(
        task_type, 
        config.get('models', {}).get('default', 'llama3.2:1b')
    )


def get_prompt(config, prompt_type):
    """Get a prompt template by type."""
    return config.get('prompts', {}).get(prompt_type, '')
