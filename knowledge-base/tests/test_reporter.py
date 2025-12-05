"""
Test Reporter - Custom pytest plugin for generating structured test reports.

Generates reports matching the test case template format:
- Test Case ID
- Test Priority
- Module Name
- Test Title
- Description
- Precondition
- Dependencies
- Test Steps
- Expected Results
- Actual Result
- Status
- Notes

Output formats: JSON, CSV, HTML
"""
import json
import csv
import os
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from pathlib import Path


@dataclass
class TestStep:
    """Individual test step."""
    step_number: int
    description: str
    test_data: str = ""
    expected_result: str = ""
    actual_result: str = ""
    status: str = ""  # PASS, FAIL, SKIP


@dataclass
class TestCaseResult:
    """Complete test case result matching the template format."""
    test_case_id: str
    test_priority: str  # Critical, High, Medium, Low
    module_name: str
    test_title: str
    description: str
    precondition: str = ""
    dependencies: str = ""
    steps: List[TestStep] = field(default_factory=list)
    postcondition: str = ""
    status: str = "NOT_RUN"  # PASS, FAIL, SKIP, ERROR
    actual_result: str = ""
    notes: str = ""
    error_message: str = ""
    stack_trace: str = ""
    execution_time_ms: float = 0.0
    executed_at: str = ""
    executed_by: str = "Automated Test"


class TestReporter:
    """
    Test reporter that collects and exports test results.
    
    Usage:
        reporter = TestReporter()
        
        # Add test result
        reporter.add_result(TestCaseResult(...))
        
        # Export reports
        reporter.export_all("./test_results")
    """
    
    def __init__(self, test_designed_by: str = "Paul Andrew T. Chua"):
        self.results: List[TestCaseResult] = []
        self.test_designed_by = test_designed_by
        self.test_designed_date = datetime.now().strftime("%m/%d/%Y")
        self.start_time = datetime.now()
        
    def add_result(self, result: TestCaseResult):
        """Add a test result."""
        if not result.executed_at:
            result.executed_at = datetime.now().isoformat()
        self.results.append(result)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get test execution summary."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == "PASS")
        failed = sum(1 for r in self.results if r.status == "FAIL")
        skipped = sum(1 for r in self.results if r.status == "SKIP")
        errors = sum(1 for r in self.results if r.status == "ERROR")
        
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "errors": errors,
            "pass_rate": f"{(passed/total*100):.1f}%" if total > 0 else "N/A",
            "execution_time_ms": sum(r.execution_time_ms for r in self.results),
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat()
        }
    
    def export_json(self, output_path: str) -> str:
        """Export results to JSON file."""
        filepath = Path(output_path)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "metadata": {
                "test_designed_by": self.test_designed_by,
                "test_designed_date": self.test_designed_date,
                "test_executed_by": "Automated Test Suite",
                "test_execution_date": datetime.now().strftime("%m/%d/%Y"),
                "report_generated_at": datetime.now().isoformat()
            },
            "summary": self.get_summary(),
            "test_cases": [asdict(r) for r in self.results]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return str(filepath)
    
    def export_csv(self, output_path: str) -> str:
        """Export results to CSV file (matching spreadsheet template)."""
        filepath = Path(output_path)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header row matching template
            writer.writerow([
                "Test Case ID",
                "Test Priority", 
                "Module Name",
                "Test Title",
                "Description",
                "Precondition",
                "Dependencies",
                "Step #",
                "Test Steps",
                "Test Data",
                "Expected Results",
                "Actual Result",
                "Status",
                "Notes"
            ])
            
            # Write each test case
            for result in self.results:
                if result.steps:
                    # Write first step with full test case info
                    first_step = result.steps[0] if result.steps else TestStep(1, "N/A")
                    writer.writerow([
                        result.test_case_id,
                        result.test_priority,
                        result.module_name,
                        result.test_title,
                        result.description,
                        result.precondition,
                        result.dependencies,
                        first_step.step_number,
                        first_step.description,
                        first_step.test_data,
                        first_step.expected_result,
                        result.actual_result or first_step.actual_result,
                        result.status,
                        result.notes or result.error_message
                    ])
                    
                    # Write remaining steps (with empty test case info)
                    for step in result.steps[1:]:
                        writer.writerow([
                            "",  # Test Case ID
                            "",  # Priority
                            "",  # Module
                            "",  # Title
                            "",  # Description
                            "",  # Precondition
                            "",  # Dependencies
                            step.step_number,
                            step.description,
                            step.test_data,
                            step.expected_result,
                            step.actual_result,
                            step.status,
                            ""
                        ])
                else:
                    # No steps defined - write single row
                    writer.writerow([
                        result.test_case_id,
                        result.test_priority,
                        result.module_name,
                        result.test_title,
                        result.description,
                        result.precondition,
                        result.dependencies,
                        1,
                        "Execute test",
                        "",
                        "Test passes",
                        result.actual_result,
                        result.status,
                        result.notes or result.error_message
                    ])
        
        return str(filepath)
    
    def export_html(self, output_path: str) -> str:
        """Export results to HTML report."""
        filepath = Path(output_path)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        summary = self.get_summary()
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Knowledge Base Test Report - {datetime.now().strftime("%Y-%m-%d")}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f5f5; padding: 20px; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; }}
        .header h1 {{ margin-bottom: 10px; }}
        .metadata {{ display: flex; gap: 30px; flex-wrap: wrap; margin-top: 15px; font-size: 14px; opacity: 0.9; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .summary-card {{ background: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .summary-card.passed {{ border-left: 4px solid #22c55e; }}
        .summary-card.failed {{ border-left: 4px solid #ef4444; }}
        .summary-card.skipped {{ border-left: 4px solid #f59e0b; }}
        .summary-card .number {{ font-size: 32px; font-weight: bold; }}
        .summary-card .label {{ color: #666; font-size: 14px; }}
        .test-cases {{ background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .test-case {{ border-bottom: 1px solid #eee; }}
        .test-case:last-child {{ border-bottom: none; }}
        .test-case-header {{ padding: 15px 20px; cursor: pointer; display: flex; align-items: center; gap: 15px; }}
        .test-case-header:hover {{ background: #f9f9f9; }}
        .status-badge {{ padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; text-transform: uppercase; }}
        .status-badge.pass {{ background: #dcfce7; color: #166534; }}
        .status-badge.fail {{ background: #fee2e2; color: #991b1b; }}
        .status-badge.skip {{ background: #fef3c7; color: #92400e; }}
        .status-badge.error {{ background: #fce7f3; color: #9d174d; }}
        .priority-badge {{ padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 500; }}
        .priority-badge.critical {{ background: #fee2e2; color: #991b1b; }}
        .priority-badge.high {{ background: #ffedd5; color: #9a3412; }}
        .priority-badge.medium {{ background: #fef9c3; color: #854d0e; }}
        .priority-badge.low {{ background: #ecfdf5; color: #065f46; }}
        .test-case-id {{ font-family: monospace; color: #666; min-width: 120px; }}
        .test-case-title {{ flex: 1; font-weight: 500; }}
        .test-case-module {{ color: #888; font-size: 13px; }}
        .test-case-details {{ display: none; padding: 20px; background: #fafafa; border-top: 1px solid #eee; }}
        .test-case.expanded .test-case-details {{ display: block; }}
        .detail-section {{ margin-bottom: 15px; }}
        .detail-section h4 {{ color: #444; margin-bottom: 8px; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .detail-section p {{ color: #666; line-height: 1.6; }}
        .steps-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        .steps-table th, .steps-table td {{ padding: 10px; text-align: left; border: 1px solid #ddd; }}
        .steps-table th {{ background: #f0f0f0; font-weight: 600; }}
        .error-box {{ background: #fee2e2; border: 1px solid #fecaca; border-radius: 6px; padding: 15px; margin-top: 10px; }}
        .error-box pre {{ font-family: monospace; font-size: 12px; white-space: pre-wrap; word-break: break-all; color: #991b1b; }}
        .execution-time {{ color: #888; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 Knowledge Base Test Report</h1>
            <p>Automated Test Execution Results</p>
            <div class="metadata">
                <span>📅 Designed: {self.test_designed_date}</span>
                <span>👤 Designer: {self.test_designed_by}</span>
                <span>🕐 Executed: {datetime.now().strftime("%m/%d/%Y %H:%M:%S")}</span>
                <span>⏱️ Duration: {summary['execution_time_ms']:.0f}ms</span>
            </div>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <div class="number">{summary['total']}</div>
                <div class="label">Total Tests</div>
            </div>
            <div class="summary-card passed">
                <div class="number" style="color: #22c55e;">{summary['passed']}</div>
                <div class="label">Passed</div>
            </div>
            <div class="summary-card failed">
                <div class="number" style="color: #ef4444;">{summary['failed']}</div>
                <div class="label">Failed</div>
            </div>
            <div class="summary-card skipped">
                <div class="number" style="color: #f59e0b;">{summary['skipped']}</div>
                <div class="label">Skipped</div>
            </div>
            <div class="summary-card">
                <div class="number" style="color: #667eea;">{summary['pass_rate']}</div>
                <div class="label">Pass Rate</div>
            </div>
        </div>
        
        <div class="test-cases">
"""
        
        for result in self.results:
            status_class = result.status.lower()
            priority_class = result.test_priority.lower()
            
            steps_html = ""
            if result.steps:
                steps_html = """
                <table class="steps-table">
                    <tr><th>#</th><th>Step</th><th>Test Data</th><th>Expected</th><th>Actual</th><th>Status</th></tr>
"""
                for step in result.steps:
                    steps_html += f"""
                    <tr>
                        <td>{step.step_number}</td>
                        <td>{step.description}</td>
                        <td>{step.test_data or '-'}</td>
                        <td>{step.expected_result}</td>
                        <td>{step.actual_result or '-'}</td>
                        <td>{step.status or '-'}</td>
                    </tr>
"""
                steps_html += "</table>"
            
            error_html = ""
            if result.error_message or result.stack_trace:
                error_html = f"""
                <div class="error-box">
                    <h4 style="color: #991b1b; margin-bottom: 10px;">❌ Error Details</h4>
                    <p><strong>Message:</strong> {result.error_message}</p>
                    {'<pre>' + result.stack_trace + '</pre>' if result.stack_trace else ''}
                </div>
"""
            
            html += f"""
            <div class="test-case" onclick="this.classList.toggle('expanded')">
                <div class="test-case-header">
                    <span class="status-badge {status_class}">{result.status}</span>
                    <span class="test-case-id">{result.test_case_id}</span>
                    <span class="priority-badge {priority_class}">{result.test_priority}</span>
                    <span class="test-case-title">{result.test_title}</span>
                    <span class="test-case-module">{result.module_name}</span>
                    <span class="execution-time">{result.execution_time_ms:.0f}ms</span>
                </div>
                <div class="test-case-details">
                    <div class="detail-section">
                        <h4>Description</h4>
                        <p>{result.description}</p>
                    </div>
                    {f'<div class="detail-section"><h4>Precondition</h4><p>{result.precondition}</p></div>' if result.precondition else ''}
                    {f'<div class="detail-section"><h4>Dependencies</h4><p>{result.dependencies}</p></div>' if result.dependencies else ''}
                    <div class="detail-section">
                        <h4>Test Steps</h4>
                        {steps_html or '<p>No detailed steps recorded.</p>'}
                    </div>
                    <div class="detail-section">
                        <h4>Result</h4>
                        <p><strong>Actual:</strong> {result.actual_result or 'N/A'}</p>
                        {f'<p><strong>Notes:</strong> {result.notes}</p>' if result.notes else ''}
                    </div>
                    {error_html}
                </div>
            </div>
"""
        
        html += """
        </div>
    </div>
</body>
</html>
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return str(filepath)
    
    def export_failures(self, output_dir: str) -> List[str]:
        """Export detailed failure logs for each failed test."""
        failures_dir = Path(output_dir) / "failures"
        failures_dir.mkdir(parents=True, exist_ok=True)
        
        failure_files = []
        for result in self.results:
            if result.status in ["FAIL", "ERROR"]:
                filename = f"{result.test_case_id}_failure.txt"
                filepath = failures_dir / filename
                
                content = f"""Test Case Failure Report
========================
Generated: {datetime.now().isoformat()}

Test Case ID: {result.test_case_id}
Module: {result.module_name}
Title: {result.test_title}
Priority: {result.test_priority}
Status: {result.status}

Description:
{result.description}

Precondition:
{result.precondition or 'None'}

Dependencies:
{result.dependencies or 'None'}

Test Steps:
"""
                for step in result.steps:
                    content += f"""
  Step {step.step_number}: {step.description}
    Test Data: {step.test_data or 'N/A'}
    Expected: {step.expected_result}
    Actual: {step.actual_result or 'N/A'}
    Status: {step.status or 'N/A'}
"""
                
                content += f"""
Actual Result:
{result.actual_result}

Error Message:
{result.error_message or 'None'}

Stack Trace:
{result.stack_trace or 'None'}

Notes:
{result.notes or 'None'}
"""
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                failure_files.append(str(filepath))
        
        return failure_files
    
    def export_all(self, output_dir: str) -> Dict[str, Any]:
        """Export all report formats."""
        output_dir = Path(output_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        json_path = self.export_json(output_dir / f"test_report_{timestamp}.json")
        csv_path = self.export_csv(output_dir / f"test_report_{timestamp}.csv")
        html_path = self.export_html(output_dir / f"test_report_{timestamp}.html")
        failure_files = self.export_failures(output_dir)
        
        return {
            "json": json_path,
            "csv": csv_path,
            "html": html_path,
            "failures": failure_files,
            "summary": self.get_summary()
        }


# Singleton reporter instance for use across test files
_reporter: Optional[TestReporter] = None


def get_reporter() -> TestReporter:
    """Get or create singleton reporter instance."""
    global _reporter
    if _reporter is None:
        _reporter = TestReporter()
    return _reporter


def reset_reporter():
    """Reset the reporter (for new test runs)."""
    global _reporter
    _reporter = None
