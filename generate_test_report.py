#!/usr/bin/env python3
"""
Test Report Generator
Generates comprehensive HTML and JSON reports from test results
"""

import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Any
import subprocess

class TestReportGenerator:
    """Generates comprehensive test reports"""
    
    def __init__(self):
        self.report_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "environment": self.get_environment_info(),
            "test_suites": {},
            "summary": {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "skipped_tests": 0,
                "success_rate": 0.0,
                "total_duration": 0.0
            },
            "coverage": {},
            "performance_metrics": {},
            "recommendations": []
        }
        
    def get_environment_info(self) -> Dict[str, Any]:
        """Get environment information"""
        try:
            return {
                "python_version": sys.version,
                "platform": sys.platform,
                "cwd": os.getcwd(),
                "user": os.getenv("USER", "unknown"),
                "hostname": os.getenv("HOSTNAME", "unknown"),
                "git_commit": self.get_git_commit(),
                "git_branch": self.get_git_branch()
            }
        except Exception as e:
            return {"error": str(e)}
            
    def get_git_commit(self) -> str:
        """Get current git commit hash"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except:
            return "unknown"
            
    def get_git_branch(self) -> str:
        """Get current git branch"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except:
            return "unknown"
            
    def add_test_suite_result(self, suite_name: str, results: Dict[str, Any]):
        """Add test suite results to the report"""
        self.report_data["test_suites"][suite_name] = {
            "name": suite_name,
            "timestamp": datetime.utcnow().isoformat(),
            "results": results,
            "status": "passed" if results.get("failed", 0) == 0 else "failed"
        }
        
        # Update summary
        self.report_data["summary"]["total_tests"] += results.get("total", 0)
        self.report_data["summary"]["passed_tests"] += results.get("passed", 0)
        self.report_data["summary"]["failed_tests"] += results.get("failed", 0)
        self.report_data["summary"]["skipped_tests"] += results.get("skipped", 0)
        
    def calculate_summary(self):
        """Calculate summary statistics"""
        total = self.report_data["summary"]["total_tests"]
        passed = self.report_data["summary"]["passed_tests"]
        
        if total > 0:
            self.report_data["summary"]["success_rate"] = (passed / total) * 100
            
    def add_coverage_data(self, coverage_data: Dict[str, Any]):
        """Add code coverage data"""
        self.report_data["coverage"] = coverage_data
        
    def add_performance_metrics(self, metrics: Dict[str, Any]):
        """Add performance metrics"""
        self.report_data["performance_metrics"] = metrics
        
    def generate_recommendations(self):
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Check success rate
        success_rate = self.report_data["summary"]["success_rate"]
        if success_rate < 80:
            recommendations.append({
                "type": "critical",
                "title": "Low Test Success Rate",
                "description": f"Test success rate is {success_rate:.1f}%. Investigate failing tests before deployment.",
                "action": "Review failed tests and fix underlying issues"
            })
        elif success_rate < 95:
            recommendations.append({
                "type": "warning",
                "title": "Moderate Test Success Rate",
                "description": f"Test success rate is {success_rate:.1f}%. Consider improving test reliability.",
                "action": "Review and stabilize failing tests"
            })
            
        # Check coverage
        if "backend" in self.report_data["coverage"]:
            backend_coverage = self.report_data["coverage"]["backend"].get("line_coverage", 0)
            if backend_coverage < 80:
                recommendations.append({
                    "type": "warning",
                    "title": "Low Backend Code Coverage",
                    "description": f"Backend code coverage is {backend_coverage}%. Add more unit tests.",
                    "action": "Write additional unit tests for uncovered code paths"
                })
                
        if "frontend" in self.report_data["coverage"]:
            frontend_coverage = self.report_data["coverage"]["frontend"].get("line_coverage", 0)
            if frontend_coverage < 75:
                recommendations.append({
                    "type": "warning",
                    "title": "Low Frontend Code Coverage",
                    "description": f"Frontend code coverage is {frontend_coverage}%. Add more component tests.",
                    "action": "Write additional React component tests"
                })
                
        # Check performance
        if "api_response_time" in self.report_data["performance_metrics"]:
            avg_response_time = self.report_data["performance_metrics"]["api_response_time"]
            if avg_response_time > 2000:
                recommendations.append({
                    "type": "warning",
                    "title": "Slow API Response Times",
                    "description": f"Average API response time is {avg_response_time}ms. Optimize performance.",
                    "action": "Profile and optimize slow API endpoints"
                })
                
        # Check failed test suites
        failed_suites = [
            name for name, suite in self.report_data["test_suites"].items() 
            if suite["status"] == "failed"
        ]
        
        if failed_suites:
            recommendations.append({
                "type": "critical",
                "title": "Failed Test Suites",
                "description": f"The following test suites failed: {', '.join(failed_suites)}",
                "action": "Investigate and fix failing test suites before deployment"
            })
            
        self.report_data["recommendations"] = recommendations
        
    def generate_html_report(self, output_file: str = "test_report.html"):
        """Generate HTML test report"""
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Japanese Stock Analysis Platform - Test Report</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5em;
        }
        .header p {
            margin: 10px 0 0 0;
            opacity: 0.9;
        }
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }
        .metric {
            text-align: center;
            padding: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .metric-label {
            color: #666;
            font-size: 0.9em;
        }
        .success { color: #28a745; }
        .warning { color: #ffc107; }
        .danger { color: #dc3545; }
        .info { color: #17a2b8; }
        
        .section {
            padding: 30px;
            border-bottom: 1px solid #eee;
        }
        .section h2 {
            margin-top: 0;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .test-suite {
            margin-bottom: 20px;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
        }
        .test-suite-header {
            padding: 15px 20px;
            background: #f8f9fa;
            border-bottom: 1px solid #ddd;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .test-suite-name {
            font-weight: bold;
            font-size: 1.1em;
        }
        .test-suite-status {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
            text-transform: uppercase;
        }
        .status-passed {
            background: #d4edda;
            color: #155724;
        }
        .status-failed {
            background: #f8d7da;
            color: #721c24;
        }
        .test-suite-details {
            padding: 20px;
        }
        .recommendation {
            margin-bottom: 15px;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid;
        }
        .recommendation.critical {
            background: #f8d7da;
            border-color: #dc3545;
        }
        .recommendation.warning {
            background: #fff3cd;
            border-color: #ffc107;
        }
        .recommendation.info {
            background: #d1ecf1;
            border-color: #17a2b8;
        }
        .recommendation-title {
            font-weight: bold;
            margin-bottom: 5px;
        }
        .recommendation-action {
            font-style: italic;
            margin-top: 10px;
            color: #666;
        }
        .environment-info {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 0.9em;
        }
        .progress-bar {
            width: 100%;
            height: 20px;
            background: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #28a745, #20c997);
            transition: width 0.3s ease;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏛️ Test Report</h1>
            <p>Japanese Stock Analysis Platform - Comprehensive Integration Tests</p>
            <p>Generated on {timestamp}</p>
        </div>
        
        <div class="summary">
            <div class="metric">
                <div class="metric-value success">{total_tests}</div>
                <div class="metric-label">Total Tests</div>
            </div>
            <div class="metric">
                <div class="metric-value success">{passed_tests}</div>
                <div class="metric-label">Passed</div>
            </div>
            <div class="metric">
                <div class="metric-value danger">{failed_tests}</div>
                <div class="metric-label">Failed</div>
            </div>
            <div class="metric">
                <div class="metric-value info">{success_rate:.1f}%</div>
                <div class="metric-label">Success Rate</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📊 Overall Progress</h2>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {success_rate}%"></div>
            </div>
            <p>Test execution completed with {success_rate:.1f}% success rate</p>
        </div>
        
        {test_suites_html}
        
        {recommendations_html}
        
        <div class="section">
            <h2>🔧 Environment Information</h2>
            <div class="environment-info">
                <strong>Platform:</strong> {platform}<br>
                <strong>Python Version:</strong> {python_version}<br>
                <strong>Git Branch:</strong> {git_branch}<br>
                <strong>Git Commit:</strong> {git_commit}<br>
                <strong>Timestamp:</strong> {timestamp}
            </div>
        </div>
    </div>
</body>
</html>
        """
        
        # Generate test suites HTML
        test_suites_html = ""
        if self.report_data["test_suites"]:
            test_suites_html = '<div class="section"><h2>🧪 Test Suites</h2>'
            
            for suite_name, suite_data in self.report_data["test_suites"].items():
                status_class = "status-passed" if suite_data["status"] == "passed" else "status-failed"
                results = suite_data["results"]
                
                test_suites_html += f"""
                <div class="test-suite">
                    <div class="test-suite-header">
                        <div class="test-suite-name">{suite_name}</div>
                        <div class="test-suite-status {status_class}">{suite_data["status"]}</div>
                    </div>
                    <div class="test-suite-details">
                        <p><strong>Total:</strong> {results.get('total', 0)} | 
                           <strong>Passed:</strong> {results.get('passed', 0)} | 
                           <strong>Failed:</strong> {results.get('failed', 0)}</p>
                        {f'<p><strong>Duration:</strong> {results.get("duration", "N/A")}</p>' if results.get("duration") else ''}
                    </div>
                </div>
                """
            
            test_suites_html += '</div>'
            
        # Generate recommendations HTML
        recommendations_html = ""
        if self.report_data["recommendations"]:
            recommendations_html = '<div class="section"><h2>💡 Recommendations</h2>'
            
            for rec in self.report_data["recommendations"]:
                recommendations_html += f"""
                <div class="recommendation {rec['type']}">
                    <div class="recommendation-title">{rec['title']}</div>
                    <div>{rec['description']}</div>
                    <div class="recommendation-action">Action: {rec['action']}</div>
                </div>
                """
            
            recommendations_html += '</div>'
            
        # Fill template
        html_content = html_template.format(
            timestamp=self.report_data["timestamp"],
            total_tests=self.report_data["summary"]["total_tests"],
            passed_tests=self.report_data["summary"]["passed_tests"],
            failed_tests=self.report_data["summary"]["failed_tests"],
            success_rate=self.report_data["summary"]["success_rate"],
            test_suites_html=test_suites_html,
            recommendations_html=recommendations_html,
            platform=self.report_data["environment"].get("platform", "unknown"),
            python_version=self.report_data["environment"].get("python_version", "unknown").split()[0],
            git_branch=self.report_data["environment"].get("git_branch", "unknown"),
            git_commit=self.report_data["environment"].get("git_commit", "unknown")[:8]
        )
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        print(f"✅ HTML report generated: {output_file}")
        
    def generate_json_report(self, output_file: str = "test_report.json"):
        """Generate JSON test report"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.report_data, f, indent=2, default=str)
            
        print(f"✅ JSON report generated: {output_file}")
        
    def generate_reports(self, html_file: str = "test_report.html", json_file: str = "test_report.json"):
        """Generate both HTML and JSON reports"""
        self.calculate_summary()
        self.generate_recommendations()
        self.generate_html_report(html_file)
        self.generate_json_report(json_file)
        
        print(f"\n📋 Test Report Summary:")
        print(f"   Total Tests: {self.report_data['summary']['total_tests']}")
        print(f"   Success Rate: {self.report_data['summary']['success_rate']:.1f}%")
        print(f"   Reports: {html_file}, {json_file}")

def main():
    """Main function for standalone usage"""
    generator = TestReportGenerator()
    
    # Example usage - in real scenario, this would be called by test runner
    generator.add_test_suite_result("Backend Integration", {
        "total": 15,
        "passed": 13,
        "failed": 2,
        "duration": "45.2s"
    })
    
    generator.add_test_suite_result("Frontend Integration", {
        "total": 8,
        "passed": 8,
        "failed": 0,
        "duration": "23.1s"
    })
    
    generator.add_coverage_data({
        "backend": {"line_coverage": 85, "branch_coverage": 78},
        "frontend": {"line_coverage": 72, "branch_coverage": 65}
    })
    
    generator.add_performance_metrics({
        "api_response_time": 1250,
        "database_query_time": 450,
        "page_load_time": 2100
    })
    
    generator.generate_reports()

if __name__ == "__main__":
    main()