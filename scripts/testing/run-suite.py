#!/usr/bin/env python3
"""
Comprehensive test execution and reporting script for CoachNTT.ai.

Provides automated test execution with safety validation, coverage reporting,
and integration with the script automation framework.

Usage:
    python3 run-suite.py [options]

Options:
    --suite SUITE          Test suite: unit, integration, safety, performance, all
    --module MODULE        Specific module to test
    --coverage             Generate coverage report
    --safety-only          Run only safety tests
    --parallel             Run tests in parallel
    --output FORMAT        Output format: text, json, xml
    --report-file FILE     Report output file
    --help                 Show this help message

Example:
    python3 run-suite.py --suite unit --coverage
    python3 run-suite.py --module vault --safety-only
    python3 run-suite.py --suite all --parallel --output json
"""

import asyncio
import sys
import argparse
import subprocess
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add framework path
sys.path.insert(0, str(Path(__file__).parent.parent))

from framework import ScriptLogger, LogLevel


@dataclass
class TestResult:
    """Individual test result."""
    
    name: str
    status: str  # passed, failed, skipped, error
    duration_seconds: float
    message: str = ""
    traceback: str = ""
    
    # Safety metrics
    safety_validated: bool = False
    safety_score: float = 1.0
    
    # Coverage metrics
    coverage_percent: Optional[float] = None
    lines_covered: Optional[int] = None
    lines_total: Optional[int] = None


@dataclass
class TestSuiteResult:
    """Test suite execution result."""
    
    suite_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    
    # Test results
    tests: List[TestResult] = field(default_factory=list)
    
    # Summary statistics
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    error_tests: int = 0
    
    # Performance metrics
    total_duration_seconds: float = 0.0
    average_test_duration: float = 0.0
    
    # Coverage metrics
    overall_coverage_percent: Optional[float] = None
    coverage_report_path: Optional[Path] = None
    
    # Safety metrics
    safety_tests_run: int = 0
    safety_tests_passed: int = 0
    overall_safety_score: float = 1.0
    
    # Errors and warnings
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate test success rate."""
        if self.total_tests == 0:
            return 0.0
        return self.passed_tests / self.total_tests
    
    @property
    def duration_seconds(self) -> float:
        """Total execution duration."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get test suite summary."""
        return {
            'suite_name': self.suite_name,
            'total_tests': self.total_tests,
            'passed_tests': self.passed_tests,
            'failed_tests': self.failed_tests,
            'skipped_tests': self.skipped_tests,
            'error_tests': self.error_tests,
            'success_rate': self.success_rate,
            'duration_seconds': self.duration_seconds,
            'coverage_percent': self.overall_coverage_percent,
            'safety_score': self.overall_safety_score,
            'errors_count': len(self.errors),
            'warnings_count': len(self.warnings)
        }


class TestSuiteRunner:
    """
    Comprehensive test suite runner with safety validation and reporting.
    
    Provides automated execution of unit, integration, safety, and performance
    tests with coverage reporting and safety compliance validation.
    """
    
    def __init__(
        self,
        project_root: Optional[Path] = None,
        logger: Optional[ScriptLogger] = None
    ):
        """
        Initialize test suite runner.
        
        Args:
            project_root: Project root directory
            logger: Logger instance
        """
        self.project_root = project_root or self._detect_project_root()
        self.logger = logger or ScriptLogger(
            script_name="test-runner",
            log_level=LogLevel.INFO,
            abstract_content=True
        )
        
        # Test directories
        self.tests_dir = self.project_root / "tests"
        self.unit_tests_dir = self.tests_dir / "unit"
        self.integration_tests_dir = self.tests_dir / "integration"
        self.safety_tests_dir = self.tests_dir / "safety"
        self.performance_tests_dir = self.tests_dir / "performance"
        
        # Reports directory
        self.reports_dir = self.project_root / "logs" / "test_reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Python executable
        self.python_exec = sys.executable
        
        self.logger.info(
            "TestSuiteRunner initialized",
            project_root=str(self.project_root),
            tests_dir=str(self.tests_dir)
        )
    
    def _detect_project_root(self) -> Path:
        """Auto-detect project root directory."""
        current_dir = Path(__file__).parent
        
        for _ in range(5):
            if (current_dir / ".git").exists() or (current_dir / "pyproject.toml").exists():
                return current_dir
            current_dir = current_dir.parent
        
        return Path.cwd()
    
    async def run_test_suite(
        self,
        suite_name: str,
        module_filter: Optional[str] = None,
        include_coverage: bool = False,
        safety_only: bool = False,
        parallel: bool = False,
        output_format: str = "text"
    ) -> TestSuiteResult:
        """
        Run comprehensive test suite.
        
        Args:
            suite_name: Test suite to run (unit, integration, safety, performance, all)
            module_filter: Filter tests by module name
            include_coverage: Generate coverage report
            safety_only: Run only safety tests
            parallel: Run tests in parallel
            output_format: Output format (text, json, xml)
            
        Returns:
            Test suite results
        """
        result = TestSuiteResult(
            suite_name=suite_name,
            start_time=datetime.now()
        )
        
        self.logger.info(f"Starting test suite: {suite_name}")
        
        try:
            # Determine which test suites to run
            suites_to_run = self._get_suites_to_run(suite_name, safety_only)
            
            # Run each test suite
            for suite in suites_to_run:
                suite_result = await self._run_individual_suite(
                    suite,
                    module_filter,
                    include_coverage,
                    parallel
                )
                
                # Merge results
                result.tests.extend(suite_result.tests)
                result.errors.extend(suite_result.errors)
                result.warnings.extend(suite_result.warnings)
            
            # Calculate summary statistics
            self._calculate_summary_stats(result)
            
            # Generate coverage report if requested
            if include_coverage:
                await self._generate_coverage_report(result)
            
            # Run safety validation on test code
            await self._validate_test_safety(result)
            
            # Generate test report
            await self._generate_test_report(result, output_format)
            
        except Exception as e:
            error_msg = f"Test suite execution failed: {str(e)}"
            self.logger.error(error_msg)
            result.errors.append(error_msg)
        
        finally:
            result.end_time = datetime.now()
            self._log_suite_completion(result)
        
        return result
    
    def _get_suites_to_run(self, suite_name: str, safety_only: bool) -> List[str]:
        """Determine which test suites to run."""
        if safety_only:
            return ["safety"]
        
        if suite_name == "all":
            return ["unit", "integration", "safety", "performance"]
        elif suite_name in ["unit", "integration", "safety", "performance"]:
            return [suite_name]
        else:
            raise ValueError(f"Unknown test suite: {suite_name}")
    
    async def _run_individual_suite(
        self,
        suite_name: str,
        module_filter: Optional[str],
        include_coverage: bool,
        parallel: bool
    ) -> TestSuiteResult:
        """Run an individual test suite."""
        self.logger.info(f"Running {suite_name} tests")
        
        result = TestSuiteResult(
            suite_name=suite_name,
            start_time=datetime.now()
        )
        
        # Get test directory
        test_dir = getattr(self, f"{suite_name}_tests_dir")
        if not test_dir.exists():
            self.logger.warning(f"Test directory not found: {test_dir}")
            return result
        
        # Find test files
        test_files = self._find_test_files(test_dir, module_filter)
        if not test_files:
            self.logger.warning(f"No test files found in {test_dir}")
            return result
        
        # Run tests
        if parallel and len(test_files) > 1:
            results = await self._run_tests_parallel(test_files, include_coverage)
        else:
            results = await self._run_tests_sequential(test_files, include_coverage)
        
        result.tests.extend(results)
        result.end_time = datetime.now()
        
        return result
    
    def _find_test_files(self, test_dir: Path, module_filter: Optional[str]) -> List[Path]:
        """Find test files in directory."""
        test_files = []
        
        # Find Python test files
        for pattern in ["test_*.py", "*_test.py"]:
            test_files.extend(test_dir.glob(f"**/{pattern}"))
        
        # Apply module filter
        if module_filter:
            test_files = [f for f in test_files if module_filter in str(f)]
        
        return sorted(test_files)
    
    async def _run_tests_sequential(
        self,
        test_files: List[Path],
        include_coverage: bool
    ) -> List[TestResult]:
        """Run tests sequentially."""
        results = []
        
        for test_file in test_files:
            test_result = await self._run_single_test_file(test_file, include_coverage)
            results.extend(test_result)
        
        return results
    
    async def _run_tests_parallel(
        self,
        test_files: List[Path],
        include_coverage: bool
    ) -> List[TestResult]:
        """Run tests in parallel."""
        results = []
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit all test files
            futures = {
                executor.submit(self._run_test_file_sync, test_file, include_coverage): test_file
                for test_file in test_files
            }
            
            # Collect results as they complete
            for future in as_completed(futures):
                try:
                    test_results = future.result()
                    results.extend(test_results)
                except Exception as e:
                    test_file = futures[future]
                    self.logger.error(f"Test file {test_file} failed: {e}")
                    # Create error result
                    error_result = TestResult(
                        name=str(test_file),
                        status="error",
                        duration_seconds=0.0,
                        message=str(e)
                    )
                    results.append(error_result)
        
        return results
    
    def _run_test_file_sync(self, test_file: Path, include_coverage: bool) -> List[TestResult]:
        """Synchronous wrapper for running test file (for thread executor)."""
        return asyncio.run(self._run_single_test_file(test_file, include_coverage))
    
    async def _run_single_test_file(
        self,
        test_file: Path,
        include_coverage: bool
    ) -> List[TestResult]:
        """Run a single test file."""
        self.logger.debug(f"Running test file: {test_file}")
        
        try:
            # Build pytest command
            cmd = [self.python_exec, "-m", "pytest", str(test_file), "-v", "--tb=short"]
            
            if include_coverage:
                cmd.extend(["--cov=src", "--cov-report=term-missing"])
            
            # Add JSON output for parsing
            json_report = self.reports_dir / f"pytest_{test_file.stem}_{int(time.time())}.json"
            cmd.extend(["--json-report", f"--json-report-file={json_report}"])
            
            # Run test
            start_time = time.time()
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.project_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            duration = time.time() - start_time
            
            # Parse results
            results = self._parse_test_results(
                json_report, test_file, duration, stdout.decode(), stderr.decode()
            )
            
            # Clean up temporary files
            if json_report.exists():
                json_report.unlink()
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to run test file {test_file}: {e}")
            return [TestResult(
                name=str(test_file),
                status="error",
                duration_seconds=0.0,
                message=str(e)
            )]
    
    def _parse_test_results(
        self,
        json_report: Path,
        test_file: Path,
        duration: float,
        stdout: str,
        stderr: str
    ) -> List[TestResult]:
        """Parse test results from pytest JSON output."""
        results = []
        
        try:
            if json_report.exists():
                with open(json_report, 'r') as f:
                    data = json.load(f)
                
                # Parse individual test results
                for test in data.get('tests', []):
                    result = TestResult(
                        name=test.get('nodeid', str(test_file)),
                        status=test.get('outcome', 'unknown'),
                        duration_seconds=test.get('duration', 0.0),
                        message=test.get('call', {}).get('longrepr', ''),
                        traceback=test.get('call', {}).get('longrepr', '')
                    )
                    
                    # Check if this is a safety test
                    if 'safety' in result.name.lower():
                        result.safety_validated = True
                        # Extract safety score from test output if available
                        if 'safety_score' in result.message:
                            try:
                                import re
                                score_match = re.search(r'safety_score[:\s]*([0-9.]+)', result.message)
                                if score_match:
                                    result.safety_score = float(score_match.group(1))
                            except Exception:
                                pass
                    
                    results.append(result)
            
            else:
                # Fallback parsing from stdout/stderr
                if "FAILED" in stdout or "ERROR" in stdout:
                    status = "failed"
                elif "PASSED" in stdout:
                    status = "passed"
                else:
                    status = "unknown"
                
                results.append(TestResult(
                    name=str(test_file),
                    status=status,
                    duration_seconds=duration,
                    message=stderr if stderr else stdout[:200]
                ))
        
        except Exception as e:
            self.logger.warning(f"Failed to parse test results: {e}")
            results.append(TestResult(
                name=str(test_file),
                status="error",
                duration_seconds=duration,
                message=f"Result parsing failed: {str(e)}"
            ))
        
        return results
    
    def _calculate_summary_stats(self, result: TestSuiteResult):
        """Calculate summary statistics for test suite."""
        result.total_tests = len(result.tests)
        result.passed_tests = len([t for t in result.tests if t.status == "passed"])
        result.failed_tests = len([t for t in result.tests if t.status == "failed"])
        result.skipped_tests = len([t for t in result.tests if t.status == "skipped"])
        result.error_tests = len([t for t in result.tests if t.status == "error"])
        
        if result.tests:
            result.total_duration_seconds = sum(t.duration_seconds for t in result.tests)
            result.average_test_duration = result.total_duration_seconds / len(result.tests)
        
        # Safety metrics
        safety_tests = [t for t in result.tests if t.safety_validated]
        result.safety_tests_run = len(safety_tests)
        result.safety_tests_passed = len([t for t in safety_tests if t.status == "passed"])
        
        if safety_tests:
            result.overall_safety_score = sum(t.safety_score for t in safety_tests) / len(safety_tests)
    
    async def _generate_coverage_report(self, result: TestSuiteResult):
        """Generate coverage report."""
        try:
            self.logger.info("Generating coverage report")
            
            # Run coverage report
            cmd = [self.python_exec, "-m", "coverage", "report", "--show-missing"]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.project_root,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                # Parse coverage percentage
                coverage_output = stdout.decode()
                import re
                match = re.search(r'TOTAL\s+\d+\s+\d+\s+(\d+)%', coverage_output)
                if match:
                    result.overall_coverage_percent = float(match.group(1))
                
                # Generate HTML report
                html_report_dir = self.reports_dir / "coverage_html"
                cmd_html = [self.python_exec, "-m", "coverage", "html", "-d", str(html_report_dir)]
                await asyncio.create_subprocess_exec(*cmd_html, cwd=self.project_root)
                
                result.coverage_report_path = html_report_dir / "index.html"
                self.logger.info(f"Coverage report generated: {result.coverage_report_path}")
            
            else:
                result.warnings.append("Coverage report generation failed")
                
        except Exception as e:
            self.logger.warning(f"Coverage report generation failed: {e}")
            result.warnings.append(f"Coverage error: {str(e)}")
    
    async def _validate_test_safety(self, result: TestSuiteResult):
        """Validate safety of test code itself."""
        try:
            self.logger.info("Validating test code safety")
            
            # Simple safety check on test files
            safety_violations = 0
            
            for test_file in self.tests_dir.glob("**/*.py"):
                try:
                    content = test_file.read_text(encoding='utf-8')
                    
                    # Check for hardcoded sensitive data patterns
                    import re
                    
                    # Look for potential hardcoded secrets
                    secret_patterns = [
                        r'password\s*=\s*["\'][^"\']+["\']',
                        r'api_key\s*=\s*["\'][^"\']+["\']',
                        r'secret\s*=\s*["\'][^"\']+["\']',
                        r'token\s*=\s*["\'][^"\']+["\']'
                    ]
                    
                    for pattern in secret_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            safety_violations += 1
                            result.warnings.append(f"Potential hardcoded secret in {test_file.name}")
                    
                    # Check for absolute paths
                    if re.search(r'["\']\/[^"\']*["\']', content):
                        result.warnings.append(f"Hardcoded absolute path in {test_file.name}")
                
                except Exception:
                    continue
            
            if safety_violations == 0:
                self.logger.info("Test code safety validation passed")
            else:
                self.logger.warning(f"Test code safety violations: {safety_violations}")
                
        except Exception as e:
            self.logger.warning(f"Test safety validation failed: {e}")
    
    async def _generate_test_report(self, result: TestSuiteResult, output_format: str):
        """Generate comprehensive test report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if output_format == "json":
            await self._generate_json_report(result, timestamp)
        elif output_format == "xml":
            await self._generate_xml_report(result, timestamp)
        else:
            await self._generate_text_report(result, timestamp)
    
    async def _generate_text_report(self, result: TestSuiteResult, timestamp: str):
        """Generate text format test report."""
        report_path = self.reports_dir / f"test_report_{timestamp}.md"
        
        report_content = f"""# Test Suite Report

**Suite**: {result.suite_name}
**Executed**: {result.start_time.isoformat()}
**Duration**: {result.duration_seconds:.2f} seconds

## Summary

- **Total Tests**: {result.total_tests}
- **Passed**: {result.passed_tests} ({result.success_rate:.1%})
- **Failed**: {result.failed_tests}
- **Skipped**: {result.skipped_tests}
- **Errors**: {result.error_tests}
- **Average Duration**: {result.average_test_duration:.3f}s

## Coverage

- **Overall Coverage**: {result.overall_coverage_percent or 'N/A'}%

## Safety

- **Safety Tests Run**: {result.safety_tests_run}
- **Safety Tests Passed**: {result.safety_tests_passed}
- **Overall Safety Score**: {result.overall_safety_score:.3f}

## Test Results

"""
        
        # Group tests by status
        for status in ["failed", "error", "passed", "skipped"]:
            tests_with_status = [t for t in result.tests if t.status == status]
            if tests_with_status:
                report_content += f"### {status.title()} Tests ({len(tests_with_status)})\n\n"
                for test in tests_with_status:
                    report_content += f"- **{test.name}** ({test.duration_seconds:.3f}s)\n"
                    if test.message and status in ["failed", "error"]:
                        report_content += f"  - Error: {test.message[:100]}{'...' if len(test.message) > 100 else ''}\n"
                report_content += "\n"
        
        if result.errors:
            report_content += "## Errors\n\n"
            for error in result.errors:
                report_content += f"- {error}\n"
            report_content += "\n"
        
        if result.warnings:
            report_content += "## Warnings\n\n"
            for warning in result.warnings:
                report_content += f"- {warning}\n"
            report_content += "\n"
        
        report_content += f"""
---
*Report generated by CoachNTT.ai Test Runner at {datetime.now().isoformat()}*
"""
        
        report_path.write_text(report_content, encoding='utf-8')
        self.logger.info(f"Test report saved: {report_path}")
    
    async def _generate_json_report(self, result: TestSuiteResult, timestamp: str):
        """Generate JSON format test report."""
        report_path = self.reports_dir / f"test_report_{timestamp}.json"
        
        report_data = {
            'suite_name': result.suite_name,
            'start_time': result.start_time.isoformat(),
            'end_time': result.end_time.isoformat() if result.end_time else None,
            'duration_seconds': result.duration_seconds,
            'summary': result.get_summary(),
            'tests': [
                {
                    'name': t.name,
                    'status': t.status,
                    'duration_seconds': t.duration_seconds,
                    'message': t.message,
                    'safety_validated': t.safety_validated,
                    'safety_score': t.safety_score
                }
                for t in result.tests
            ],
            'errors': result.errors,
            'warnings': result.warnings,
            'generated_at': datetime.now().isoformat()
        }
        
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        self.logger.info(f"JSON test report saved: {report_path}")
    
    async def _generate_xml_report(self, result: TestSuiteResult, timestamp: str):
        """Generate XML format test report (JUnit style)."""
        report_path = self.reports_dir / f"test_report_{timestamp}.xml"
        
        # Simple XML generation (in production, would use proper XML library)
        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="{result.suite_name}" 
           tests="{result.total_tests}" 
           failures="{result.failed_tests}" 
           errors="{result.error_tests}" 
           skipped="{result.skipped_tests}" 
           time="{result.duration_seconds:.3f}">
"""
        
        for test in result.tests:
            xml_content += f'  <testcase name="{test.name}" time="{test.duration_seconds:.3f}"'
            
            if test.status == "passed":
                xml_content += " />\n"
            elif test.status == "failed":
                xml_content += ">\n"
                xml_content += f'    <failure message="{test.message[:100]}">{test.message}</failure>\n'
                xml_content += "  </testcase>\n"
            elif test.status == "error":
                xml_content += ">\n"
                xml_content += f'    <error message="{test.message[:100]}">{test.message}</error>\n'
                xml_content += "  </testcase>\n"
            elif test.status == "skipped":
                xml_content += ">\n"
                xml_content += f'    <skipped message="{test.message[:100]}" />\n'
                xml_content += "  </testcase>\n"
        
        xml_content += "</testsuite>\n"
        
        report_path.write_text(xml_content, encoding='utf-8')
        self.logger.info(f"XML test report saved: {report_path}")
    
    def _log_suite_completion(self, result: TestSuiteResult):
        """Log test suite completion."""
        if result.success_rate >= 0.9:
            self.logger.info(
                f"Test suite {result.suite_name} completed successfully",
                **result.get_summary()
            )
        else:
            self.logger.warning(
                f"Test suite {result.suite_name} completed with failures",
                **result.get_summary()
            )


async def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description="Comprehensive test execution for CoachNTT.ai",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--suite",
        choices=["unit", "integration", "safety", "performance", "all"],
        default="all",
        help="Test suite to run"
    )
    parser.add_argument(
        "--module",
        help="Filter tests by module name"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    parser.add_argument(
        "--safety-only",
        action="store_true",
        help="Run only safety tests"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run tests in parallel"
    )
    parser.add_argument(
        "--output",
        choices=["text", "json", "xml"],
        default="text",
        help="Output format"
    )
    parser.add_argument(
        "--report-file",
        help="Report output file"
    )
    
    args = parser.parse_args()
    
    # Initialize test runner
    test_runner = TestSuiteRunner()
    
    try:
        # Run test suite
        result = await test_runner.run_test_suite(
            suite_name=args.suite,
            module_filter=args.module,
            include_coverage=args.coverage,
            safety_only=args.safety_only,
            parallel=args.parallel,
            output_format=args.output
        )
        
        # Print summary
        print(f"\nTest Suite Results ({args.suite}):")
        print("=" * 50)
        print(f"Total Tests: {result.total_tests}")
        print(f"Passed: {result.passed_tests} ({result.success_rate:.1%})")
        print(f"Failed: {result.failed_tests}")
        print(f"Errors: {result.error_tests}")
        print(f"Skipped: {result.skipped_tests}")
        print(f"Duration: {result.duration_seconds:.2f} seconds")
        
        if result.overall_coverage_percent is not None:
            print(f"Coverage: {result.overall_coverage_percent:.1f}%")
        
        print(f"Safety Score: {result.overall_safety_score:.3f}")
        
        if result.errors:
            print(f"\nErrors ({len(result.errors)}):")
            for error in result.errors:
                print(f"  - {error}")
        
        if result.warnings:
            print(f"\nWarnings ({len(result.warnings)}):")
            for warning in result.warnings:
                print(f"  - {warning}")
        
        # Return appropriate exit code
        return 0 if result.success_rate >= 0.9 else 1
        
    except KeyboardInterrupt:
        print("\nTest execution cancelled by user.")
        return 1
    except Exception as e:
        print(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)