"""
Ollama AI Pipeline - Multi-model analysis for GitHub workflows
"""

from .config import load_config, get_model_for_task, get_prompt
from .models import (
    OllamaError,
    run_model_query,
    check_model_available,
    download_model,
    timed_operation,
    ModelRouter
)
from .storage import (
    DirectoryManager,
    ResultStorage,
    run_git_command,
    commit_results,
    checkout_results_branch
)
from .analysis import (
    AnalysisResult,
    analyze_content,
    analyze_file,
    analyze_repository,
    generate_analysis_report
)

__version__ = "0.1.0"

__all__ = [
    'load_config',
    'get_model_for_task',
    'get_prompt',
    'OllamaError',
    'run_model_query',
    'check_model_available',
    'download_model',
    'timed_operation',
    'ModelRouter',
    'DirectoryManager',
    'ResultStorage',
    'run_git_command',
    'commit_results',
    'checkout_results_branch',
    'AnalysisResult',
    'analyze_content',
    'analyze_file',
    'analyze_repository',
    'generate_analysis_report',
]
