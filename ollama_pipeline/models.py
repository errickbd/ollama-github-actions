#!/usr/bin/env python3
"""
Model operations module for Ollama Pipeline.
Centralizes all Ollama interactions in one place.
"""

import subprocess
import time
from functools import wraps


class OllamaError(Exception):
    """Custom exception for Ollama operations."""
    
    def __init__(self, message, model=None, timeout=None):
        super().__init__(message)
        self.message = message
        self.model = model
        self.timeout = timeout
    
    def __str__(self):
        parts = [self.message]
        if self.model:
            parts.append(f"Model: {self.model}")
        if self.timeout:
            parts.append(f"Timeout: {self.timeout}s")
        return " | ".join(parts)


def timed_operation(func):
    """Decorator that logs execution time for any operation."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start
            print(f"⏱️  {func.__name__} completed in {duration:.1f}s")
            return result
        except Exception as e:
            duration = time.time() - start
            print(f"⏱️  {func.__name__} failed after {duration:.1f}s")
            raise
    return wrapper


@timed_operation
def run_model_query(model, prompt, timeout=60):
    """
    Execute Ollama query and return response.
    
    Args:
        model: Name of the Ollama model to use
        prompt: Prompt text to send to the model
        timeout: Maximum seconds to wait for response
    
    Returns:
        Response text from the model
    
    Raises:
        OllamaError: If the query fails or times out
    """
    print(f"🤖 Querying model: {model}")
    
    try:
        result = subprocess.run(
            ['ollama', 'run', model, prompt],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode != 0:
            raise OllamaError(
                f"Query failed: {result.stderr.strip()}",
                model=model
            )
        
        response = result.stdout.strip()
        print(f"✅ Received response ({len(response)} chars)")
        return response
        
    except subprocess.TimeoutExpired:
        raise OllamaError(
            f"Query timed out after {timeout}s",
            model=model,
            timeout=timeout
        )
    except FileNotFoundError:
        raise OllamaError(
            "Ollama not installed or not in PATH",
            model=model
        )


def check_model_available(model, download_if_missing=False):
    """
    Check if a model is available locally.
    
    Args:
        model: Name of the model to check
        download_if_missing: If True, download the model if not found
    
    Returns:
        True if model is available, False otherwise
    """
    print(f"🔍 Checking model availability: {model}")
    
    try:
        result = subprocess.run(
            ['ollama', 'list'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            print(f"❌ Failed to list models: {result.stderr}")
            return False
        
        # Check if model name appears in the list
        if model in result.stdout:
            print(f"✅ Model {model} is available")
            return True
        else:
            print(f"⚠️  Model {model} not found locally")
            
            if download_if_missing:
                return download_model(model)
            
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Timeout checking model list")
        return False
    except FileNotFoundError:
        print("❌ Ollama not installed")
        return False


def download_model(model):
    """
    Download a model from Ollama.
    
    Args:
        model: Name of the model to download
    
    Returns:
        True if download successful, False otherwise
    """
    print(f"⬇️  Downloading model: {model}")
    
    try:
        result = subprocess.run(
            ['ollama', 'pull', model],
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes for large models
        )
        
        if result.returncode == 0:
            print(f"✅ Model {model} downloaded successfully")
            return True
        else:
            print(f"❌ Failed to download model: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ Download timed out for model {model}")
        return False


def get_ollama_version():
    """Get the installed Ollama version."""
    try:
        result = subprocess.run(
            ['ollama', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


class ModelRouter:
    """
    Routes tasks to appropriate models based on content classification.
    """
    
    def __init__(self, config):
        """
        Initialize router with configuration.
        
        Args:
            config: Configuration dictionary from load_config()
        """
        self.config = config
        self.assignments = config.get('model_assignments', {})
        self.classifier_model = config.get('models', {}).get('classifier', 'llama3.2:1b')
        self.default_model = config.get('models', {}).get('default', 'llama3.2:1b')
        self.prompts = config.get('prompts', {})
        
        print(f"🔀 ModelRouter initialized")
        print(f"   Classifier: {self.classifier_model}")
        print(f"   Default: {self.default_model}")
        print(f"   Assignments: {self.assignments}")
    
    def classify_task(self, content):
        """
        Use fast model to classify content type.
        
        Args:
            content: Content to classify
        
        Returns:
            Task type: 'code_review', 'documentation', or 'bug_analysis'
        """
        print(f"\n📋 Classifying content ({len(content)} chars)...")
        
        classify_prompt = self.prompts.get('classify', 
            'Classify as: code_review, documentation, or bug_analysis')
        
        # Truncate content to avoid overwhelming the classifier
        truncated = content[:500] if len(content) > 500 else content
        full_prompt = f"{classify_prompt}\n\nContent:\n{truncated}"
        
        try:
            result = run_model_query(self.classifier_model, full_prompt, timeout=30)
            result_lower = result.lower()
            
            # Parse classification from response
            valid_types = ['code_review', 'documentation', 'bug_analysis']
            for task_type in valid_types:
                if task_type in result_lower:
                    print(f"✅ Classified as: {task_type}")
                    return task_type
            
            # Default if no clear classification
            print(f"⚠️  Classification unclear (got: {result[:50]}), defaulting to 'documentation'")
            return 'documentation'
            
        except OllamaError as e:
            print(f"❌ Classification failed: {e}")
            print(f"⚠️  Defaulting to 'documentation'")
            return 'documentation'
    
    def select_model(self, task_type):
        """
        Select appropriate model for task type.
        
        Args:
            task_type: Type of task (code_review, documentation, bug_analysis)
        
        Returns:
            Model name to use
        """
        if task_type in self.assignments:
            model = self.assignments[task_type]
            print(f"🎯 Selected model '{model}' for task type '{task_type}'")
        else:
            model = self.default_model
            print(f"🎯 Unknown task type '{task_type}', using default model '{model}'")
        
        return model
    
    def analyze(self, content):
        """
        Full analysis pipeline: classify, route, and analyze.
        
        Args:
            content: Content to analyze
        
        Returns:
            Dictionary with analysis results and metadata
        """
        import time
        start_time = time.time()
        
        print("\n" + "=" * 50)
        print("🚀 Starting routed analysis")
        print("=" * 50)
        
        # Step 1: Classify
        classify_start = time.time()
        task_type = self.classify_task(content)
        classify_duration = time.time() - classify_start
        
        # Step 2: Select model
        model = self.select_model(task_type)
        
        # Step 3: Get appropriate prompt
        analysis_prompt = self.prompts.get(task_type, 'Analyze this content.')
        full_prompt = f"{analysis_prompt}\n\nContent:\n{content}"
        
        # Step 4: Run analysis
        print(f"\n📝 Running {task_type} analysis with {model}...")
        analysis_start = time.time()
        
        try:
            analysis_result = run_model_query(model, full_prompt, timeout=60)
            analysis_duration = time.time() - analysis_start
            success = True
            error = None
        except OllamaError as e:
            analysis_result = None
            analysis_duration = time.time() - analysis_start
            success = False
            error = str(e)
        
        total_duration = time.time() - start_time
        
        # Build result with metadata
        result = {
            'success': success,
            'task_type': task_type,
            'model_used': model,
            'analysis': analysis_result,
            'error': error,
            'timing': {
                'classification': round(classify_duration, 2),
                'analysis': round(analysis_duration, 2),
                'total': round(total_duration, 2)
            },
            'content_length': len(content)
        }
        
        # Log summary
        print("\n" + "=" * 50)
        print("📊 Analysis Summary")
        print("=" * 50)
        print(f"   Task Type: {task_type}")
        print(f"   Model Used: {model}")
        print(f"   Success: {success}")
        print(f"   Classification Time: {classify_duration:.1f}s")
        print(f"   Analysis Time: {analysis_duration:.1f}s")
        print(f"   Total Time: {total_duration:.1f}s")
        print("=" * 50 + "\n")
        
        return result
