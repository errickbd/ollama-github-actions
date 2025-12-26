#!/usr/bin/env python3
"""
Historical report generator for Ollama Pipeline.
Analyzes accumulated results across workflow runs.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict


def parse_workflow_summaries(results_dir='results'):
    """
    Parse all workflow summary files from results directory.
    
    Args:
        results_dir: Path to results directory
    
    Returns:
        List of summary dictionaries, sorted newest first
    """
    summaries = []
    results_path = Path(results_dir)
    
    if not results_path.exists():
        print(f"⚠️  Results directory not found: {results_dir}")
        return summaries
    
    for summary_file in results_path.rglob('workflow_summary.json'):
        try:
            with open(summary_file) as f:
                summary = json.load(f)
                summary['_source_file'] = str(summary_file)
                summaries.append(summary)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  Failed to read {summary_file}: {e}")
    
    # Sort by timestamp, newest first
    summaries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    print(f"📊 Found {len(summaries)} workflow summaries")
    return summaries


def calculate_trends(summaries):
    """
    Calculate trends from historical data.
    
    Args:
        summaries: List of workflow summaries
    
    Returns:
        Dictionary with trend analysis
    """
    # Always include all keys with defaults
    trends = {
        'status': 'ok',
        'message': '',
        'run_count': len(summaries),
        'recent_runs': min(len(summaries), 5),
        'models_used': defaultdict(int),
        'task_types': defaultdict(int),
        'timing': {
            'total_times': [],
            'average': 0,
            'trend': 'stable'
        },
        'success_rate': {
            'successful': 0,
            'failed': 0,
            'rate': 0,
            'trend': 'stable'
        },
        'files_analyzed': {
            'total': 0,
            'by_type': defaultdict(int)
        }
    }
    
    if len(summaries) < 2:
        trends['status'] = 'insufficient_data'
        trends['message'] = f'Need at least 2 runs for trends, have {len(summaries)}'
        return trends
    
    # Analyze each summary
    for summary in summaries:
        # Count files
        files = summary.get('files_created', [])
        trends['files_analyzed']['total'] += len(files)
        
        for file_name in files:
            if file_name.endswith('.txt'):
                trends['files_analyzed']['by_type']['txt'] += 1
            elif file_name.endswith('.json'):
                trends['files_analyzed']['by_type']['json'] += 1
            elif file_name.endswith('.md'):
                trends['files_analyzed']['by_type']['md'] += 1
    
    # Calculate success rate (based on presence of analysis files)
    for summary in summaries:
        files = summary.get('files_created', [])
        has_analysis = any('analysis' in f.lower() for f in files)
        if has_analysis:
            trends['success_rate']['successful'] += 1
        else:
            trends['success_rate']['failed'] += 1
    
    total = trends['success_rate']['successful'] + trends['success_rate']['failed']
    if total > 0:
        trends['success_rate']['rate'] = round(
            (trends['success_rate']['successful'] / total) * 100, 1
        )
    
    # Determine success trend (compare first half to second half)
    if len(summaries) >= 4:
        mid = len(summaries) // 2
        recent_success = sum(1 for s in summaries[:mid] 
                           if any('analysis' in f.lower() for f in s.get('files_created', [])))
        older_success = sum(1 for s in summaries[mid:] 
                          if any('analysis' in f.lower() for f in s.get('files_created', [])))
        
        recent_rate = recent_success / mid if mid > 0 else 0
        older_rate = older_success / (len(summaries) - mid) if (len(summaries) - mid) > 0 else 0
        
        if recent_rate > older_rate + 0.1:
            trends['success_rate']['trend'] = 'improving'
        elif recent_rate < older_rate - 0.1:
            trends['success_rate']['trend'] = 'declining'
    
    return trends


def get_trend_emoji(trend):
    """Get emoji for trend direction."""
    if trend == 'improving':
        return '📈'
    elif trend == 'declining':
        return '📉'
    else:
        return '➡️'


def generate_markdown_report(summaries, trends):
    """
    Generate markdown report from summaries and trends.
    
    Args:
        summaries: List of workflow summaries
        trends: Trend analysis dictionary
    
    Returns:
        Markdown report string
    """
    report = []
    
    # Header
    report.append("# Historical Analysis Report")
    report.append("")
    report.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"**Total Runs Analyzed:** {len(summaries)}")
    report.append("")
    
    # Executive Summary
    report.append("## Executive Summary")
    report.append("")
    
    if trends['status'] == 'insufficient_data':
        report.append(f"⚠️ {trends['message']}")
        report.append("")
        report.append("Run more workflows to enable trend analysis.")
        report.append("")
    else:
        success_emoji = get_trend_emoji(trends['success_rate']['trend'])
        report.append(f"- **Success Rate:** {trends['success_rate']['rate']}% {success_emoji}")
        report.append(f"- **Total Files Generated:** {trends['files_analyzed']['total']}")
        report.append(f"- **Runs Analyzed:** {trends['run_count']}")
        report.append("")
    
    # Trends Table
    report.append("## Trends")
    report.append("")
    report.append("| Metric | Value | Trend |")
    report.append("|--------|-------|-------|")
    
    if trends['status'] == 'ok':
        report.append(f"| Success Rate | {trends['success_rate']['rate']}% | {get_trend_emoji(trends['success_rate']['trend'])} {trends['success_rate']['trend']} |")
        report.append(f"| Total Runs | {trends['run_count']} | ➡️ stable |")
        report.append(f"| Files Generated | {trends['files_analyzed']['total']} | ➡️ stable |")
    else:
        report.append("| Data | Insufficient | ⚠️ Need more runs |")
    
    report.append("")
    
    # File Types Breakdown
    report.append("## File Types Generated")
    report.append("")
    report.append("| Type | Count |")
    report.append("|------|-------|")
    
    by_type = trends.get('files_analyzed', {}).get('by_type', {})
    if by_type:
        for file_type, count in by_type.items():
            report.append(f"| .{file_type} | {count} |")
    else:
        report.append("| (none) | 0 |")
    
    report.append("")
    
    # Recent Runs
    report.append("## Recent Workflow Runs")
    report.append("")
    
    if summaries:
        report.append("| Timestamp | Files Created | Directory |")
        report.append("|-----------|---------------|-----------|")
        
        for summary in summaries[:10]:  # Show last 10 runs
            timestamp = summary.get('timestamp', 'unknown')[:19]  # Trim to seconds
            files_count = len(summary.get('files_created', []))
            result_dir = summary.get('result_directory', 'unknown')
            # Get just the directory name
            dir_name = Path(result_dir).name if result_dir != 'unknown' else 'unknown'
            report.append(f"| {timestamp} | {files_count} | {dir_name} |")
    else:
        report.append("No workflow runs found yet.")
    
    report.append("")
    
    # Recommendations
    report.append("## Recommendations")
    report.append("")
    
    if trends['status'] == 'insufficient_data' or not summaries:
        report.append("1. Run more workflows to generate historical data")
        report.append("2. Ensure workflow commits results to the repository")
        report.append("3. Check that workflow_summary.json is being created")
    else:
        if trends['success_rate']['rate'] < 80:
            report.append("1. ⚠️ Success rate below 80% - investigate failures")
        if trends['success_rate']['trend'] == 'declining':
            report.append("2. 📉 Success rate declining - review recent changes")
        if trends['success_rate']['rate'] >= 90 and trends['success_rate']['trend'] != 'declining':
            report.append("1. ✅ Workflow performing well")
            report.append("2. Consider adding more analysis types")
            report.append("3. Review older results for cleanup opportunities")
    
    report.append("")
    report.append("---")
    report.append(f"*Report generated by Ollama Pipeline v0.1.0*")
    
    return "\n".join(report)


def main():
    """Main function to generate historical report."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate historical analysis report')
    parser.add_argument('--results-dir', default='results', help='Results directory path')
    parser.add_argument('--output', default='historical_report.md', help='Output file path')
    parser.add_argument('--commit', action='store_true', help='Commit report to git')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("📊 HISTORICAL REPORT GENERATOR")
    print("=" * 60)
    
    # Parse summaries
    summaries = parse_workflow_summaries(args.results_dir)
    
    if not summaries:
        print("⚠️  No workflow summaries found")
        print("   Run some workflows first to generate data")
    
    # Calculate trends
    trends = calculate_trends(summaries)
    
    # Generate report
    report = generate_markdown_report(summaries, trends)
    
    # Save report
    output_path = Path(args.output)
    output_path.write_text(report)
    print(f"\n✅ Report saved to: {output_path}")
    
    # Optionally commit to git
    if args.commit:
        import subprocess
        try:
            subprocess.run(['git', 'add', str(output_path)], check=True)
            subprocess.run(['git', 'commit', '-m', f'Update historical report - {datetime.now().strftime("%Y-%m-%d")}'], check=True)
            print("✅ Report committed to git")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Git commit failed: {e}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("📈 REPORT SUMMARY")
    print("=" * 60)
    print(f"   Runs analyzed: {len(summaries)}")
    if trends['status'] == 'ok':
        print(f"   Success rate: {trends['success_rate']['rate']}%")
        print(f"   Trend: {trends['success_rate']['trend']}")
    else:
        print(f"   Status: {trends['message']}")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
