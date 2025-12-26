#!/usr/bin/env python3
"""
Analysis orchestration module for Ollama Pipeline.
Coordinates multi-model analysis with routing and storage.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from .config import load_config
from .models import ModelRouter, run_model_query, OllamaError
from .storage import ResultStorage


@dataclass
class AnalysisResult:
    """Structured result from content analysis."""
    
    content_preview: str
    task_type: str
    model_used: str
    analysis: Optional[str]
    execution_time: float
    timestamp: str
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'content_preview': self.content_preview,
            'task_type': self.task_type,
            'model_used': self.model_used,
            'analysis': self.analysis,
            'execution_time': self.execution_time,
            'timestamp': self.timestamp,
            'success': self.success,
            'error': self.error,
            'metadata': self.metadata
        }


def analyze_content(content, config=None, save_result=False, storage=None):
    """
    Analyze content using the multi-model pipeline.
    
    Args:
        content: Content string to analyze
        config: Optional configuration dictionary
        save_result: Whether to save result to storage
        storage: Optional ResultStorage instance
    
    Returns:
        AnalysisResult with analysis and metadata
    """
    start_time = time.time()
    timestamp = datetime.now().isoformat()
    
    print("\n" + "=" * 60)
    print("🔬 CONTENT ANALYSIS")
    print("=" * 60)
    
    # Load config if not provided
    if config is None:
        config = load_config()
    
    # Initialize router
    router = ModelRouter(config)
    
    # Run routed analysis
    result = router.analyze(content)
    
    execution_time = time.time() - start_time
    
    # Create structured result
    analysis_result = AnalysisResult(
        content_preview=content[:100] + "..." if len(content) > 100 else content,
        task_type=result['task_type'],
        model_used=result['model_used'],
        analysis=result['analysis'],
        execution_time=round(execution_time, 2),
        timestamp=timestamp,
        success=result['success'],
        error=result.get('error'),
        metadata={
            'timing': result['timing'],
            'content_length': len(content)
        }
    )
    
    # Save result if requested
    if save_result and storage:
        filename = f"analysis-{result['task_type']}-{int(time.time())}.txt"
        if analysis_result.analysis:
            storage.save_analysis(filename, analysis_result.analysis, analysis_result.to_dict())
    
    print(f"\n✅ Analysis complete in {execution_time:.1f}s")
    
    return analysis_result


def analyze_file(file_path, config=None):
    """
    Analyze a single file.
    
    Args:
        file_path: Path to the file to analyze
        config: Optional configuration dictionary
    
    Returns:
        AnalysisResult for the file
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        return AnalysisResult(
            content_preview=str(file_path),
            task_type='unknown',
            model_used='none',
            analysis=None,
            execution_time=0,
            timestamp=datetime.now().isoformat(),
            success=False,
            error=f"File not found: {file_path}"
        )
    
    print(f"\n📄 Analyzing file: {file_path}")
    
    content = file_path.read_text()
    result = analyze_content(content, config)
    result.metadata['file_path'] = str(file_path)
    result.metadata['file_name'] = file_path.name
    
    return result


def analyze_repository(repo_path=".", config=None, file_patterns=None):
    """
    Analyze multiple files in a repository.
    
    Args:
        repo_path: Path to the repository root
        config: Optional configuration dictionary
        file_patterns: List of glob patterns to match (default: README*, *.py, *.yml)
    
    Returns:
        List of AnalysisResult objects
    """
    repo_path = Path(repo_path)
    
    if config is None:
        config = load_config()
    
    if file_patterns is None:
        file_patterns = ['README*', '*.py', '*.yml', '*.yaml']
    
    print("\n" + "=" * 60)
    print("🏗️  REPOSITORY ANALYSIS")
    print("=" * 60)
    print(f"Repository: {repo_path.absolute()}")
    print(f"Patterns: {file_patterns}")
    
    # Collect files to analyze
    files_to_analyze = []
    for pattern in file_patterns:
        matches = list(repo_path.glob(pattern))
        # Also check subdirectories for Python files
        if pattern == '*.py':
            matches.extend(repo_path.glob('**/*.py'))
        files_to_analyze.extend(matches)
    
    # Remove duplicates and filter out __pycache__
    files_to_analyze = list(set(files_to_analyze))
    files_to_analyze = [f for f in files_to_analyze if '__pycache__' not in str(f)]
    files_to_analyze = [f for f in files_to_analyze if f.is_file()]
    
    print(f"Found {len(files_to_analyze)} files to analyze")
    
    # Analyze each file independently (parallel-ready structure)
    results: List[AnalysisResult] = []
    
    for file_path in files_to_analyze[:5]:  # Limit to 5 files to avoid long runs
        try:
            result = analyze_file(file_path, config)
            results.append(result)
        except Exception as e:
            print(f"❌ Error analyzing {file_path}: {e}")
            results.append(AnalysisResult(
                content_preview=str(file_path),
                task_type='error',
                model_used='none',
                analysis=None,
                execution_time=0,
                timestamp=datetime.now().isoformat(),
                success=False,
                error=str(e)
            ))
    
    # Generate summary
    successful = sum(1 for r in results if r.success)
    total_time = sum(r.execution_time for r in results)
    
    print("\n" + "=" * 60)
    print("📊 REPOSITORY ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"Files analyzed: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(results) - successful}")
    print(f"Total time: {total_time:.1f}s")
    print("=" * 60)
    
    return results


def generate_analysis_report(results: List[AnalysisResult], output_path=None):
    """
    Generate a markdown report from analysis results.
    
    Args:
        results: List of AnalysisResult objects
        output_path: Optional path to save the report
    
    Returns:
        Report as markdown string
    """
    report_lines = [
        "# Analysis Report",
        "",
        f"Generated: {datetime.now().isoformat()}",
        f"Total files analyzed: {len(results)}",
        "",
        "## Summary",
        "",
        "| File | Task Type | Model | Status | Time |",
        "|------|-----------|-------|--------|------|"
    ]
    
    for result in results:
        file_name = result.metadata.get('file_name', 'unknown')
        status = "✅" if result.success else "❌"
        report_lines.append(
            f"| {file_name} | {result.task_type} | {result.model_used} | {status} | {result.execution_time}s |"
        )
    
    report_lines.extend([
        "",
        "## Detailed Results",
        ""
    ])
    
    for i, result in enumerate(results, 1):
        file_name = result.metadata.get('file_name', 'unknown')
        report_lines.extend([
            f"### {i}. {file_name}",
            "",
            f"- **Task Type:** {result.task_type}",
            f"- **Model:** {result.model_used}",
            f"- **Status:** {'Success' if result.success else 'Failed'}",
            f"- **Time:** {result.execution_time}s",
            ""
        ])
        
        if result.analysis:
            report_lines.extend([
                "**Analysis:**",
                "",
                result.analysis[:500] + "..." if len(result.analysis) > 500 else result.analysis,
                ""
            ])
        
        if result.error:
            report_lines.extend([
                f"**Error:** {result.error}",
                ""
            ])
    
    report = "\n".join(report_lines)
    
    if output_path:
        Path(output_path).write_text(report)
        print(f"📄 Report saved to: {output_path}")
    
    return report
