#!/usr/bin/env python3
"""
Documentation generation automation script for CoachNTT.ai.

Integrates with the script automation framework to provide automated
documentation generation with safety validation and performance monitoring.

Usage:
    python3 generate-docs.py [options]

Options:
    --type TYPE            Documentation type: readme, api, changelog, all
    --output DIR           Output directory for generated docs
    --analyze-only         Only analyze code, don't generate docs
    --include-diagrams     Generate architecture diagrams
    --validate-safety      Validate generated content for safety compliance
    --help                 Show this help message

Example:
    python3 generate-docs.py --type all --include-diagrams
    python3 generate-docs.py --type readme --output ./docs
    python3 generate-docs.py --analyze-only --validate-safety
"""

import asyncio
import sys
import argparse
import time
from pathlib import Path
from typing import List, Optional
from decimal import Decimal

# Add framework and project paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from framework import ScriptRunner, ScriptConfig, ScriptType, ScriptLogger, LogLevel
from src.services.documentation import (
    DocumentationGenerator,
    DocumentationType,
    DocumentationConfig,
    DocumentationResult
)
from src.core.analysis.ast_analyzer import ASTAnalyzer
from src.core.validation.validator import SafetyValidator


class DocumentationAutomationScript:
    """
    Automated documentation generation script with framework integration.
    
    Provides command-line interface for documentation generation with
    safety validation, performance monitoring, and integration with
    the script automation framework.
    """
    
    def __init__(self, logger: Optional[ScriptLogger] = None):
        """
        Initialize documentation automation script.
        
        Args:
            logger: Logger instance for framework integration
        """
        self.logger = logger or ScriptLogger(
            script_name="generate-docs",
            log_level=LogLevel.INFO,
            abstract_content=True
        )
        
        # Detect project root
        self.project_root = self._detect_project_root()
        
        # Initialize components
        self.safety_validator = SafetyValidator()
        self.ast_analyzer = ASTAnalyzer(
            safety_validator=self.safety_validator,
            enable_pattern_detection=True,
            enable_complexity_analysis=True
        )
        
        self.logger.info("Documentation automation script initialized")
    
    def _detect_project_root(self) -> Path:
        """Auto-detect project root directory."""
        current_dir = Path(__file__).parent
        
        for _ in range(5):
            if (current_dir / ".git").exists() or (current_dir / "pyproject.toml").exists():
                return current_dir
            current_dir = current_dir.parent
        
        return Path.cwd()
    
    async def run_documentation_generation(
        self,
        doc_types: List[str],
        output_dir: Optional[Path] = None,
        analyze_only: bool = False,
        include_diagrams: bool = False,
        validate_safety: bool = True,
        project_name: str = "CoachNTT.ai"
    ) -> DocumentationResult:
        """
        Run comprehensive documentation generation.
        
        Args:
            doc_types: Types of documentation to generate
            output_dir: Output directory for generated docs
            analyze_only: Only perform code analysis
            include_diagrams: Generate architecture diagrams
            validate_safety: Validate generated content for safety
            project_name: Project name for documentation
            
        Returns:
            Documentation generation result
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting documentation generation: {', '.join(doc_types)}")
            
            # Configure documentation generation
            docs_dir = output_dir or (self.project_root / "docs")
            
            # Map string types to enums
            doc_type_map = {
                'readme': DocumentationType.README,
                'api': DocumentationType.API_DOCS,
                'changelog': DocumentationType.CHANGELOG,
                'architecture': DocumentationType.ARCHITECTURE,
                'diagrams': DocumentationType.DIAGRAMS,
                'reference': DocumentationType.CODE_REFERENCE
            }
            
            enabled_types = []
            for doc_type in doc_types:
                if doc_type == 'all':
                    enabled_types = list(doc_type_map.values())
                    break
                elif doc_type in doc_type_map:
                    enabled_types.append(doc_type_map[doc_type])
                else:
                    self.logger.warning(f"Unknown documentation type: {doc_type}")
            
            if include_diagrams and DocumentationType.DIAGRAMS not in enabled_types:
                enabled_types.append(DocumentationType.DIAGRAMS)
            
            # Create documentation configuration
            config = DocumentationConfig(
                project_root=self.project_root,
                docs_output_dir=docs_dir,
                project_name=project_name,
                project_description="AI development assistant with temporal memory and safety-first design",
                enabled_types=enabled_types,
                analyze_code=not analyze_only,
                include_complexity_metrics=True,
                include_dependency_analysis=True,
                enable_git_integration=True,
                safety_score_threshold=Decimal("0.8"),
                enforce_abstraction=True,
                validate_output=validate_safety,
                max_processing_time_seconds=300,
                enable_caching=True
            )
            
            # Initialize documentation generator
            generator = DocumentationGenerator(
                config=config,
                ast_analyzer=self.ast_analyzer,
                safety_validator=self.safety_validator
            )
            
            # Generate documentation
            result = await generator.generate_documentation()
            
            # Log results
            duration = (time.time() - start_time) * 1000
            
            if result.success:
                self.logger.info(
                    f"Documentation generation completed successfully in {duration:.1f}ms",
                    **result.get_summary()
                )
                
                # Log performance metrics
                self.logger.log_performance(
                    operation="documentation_generation",
                    duration_ms=int(duration),
                    memory_usage_mb=0  # Would be measured in real implementation
                )
                
                # Log safety validation
                self.logger.log_safety_validation(
                    content_type="generated_documentation",
                    safety_score=float(result.metadata.safety_score),
                    validation_passed=len(result.errors) == 0
                )
                
                # Report generated files
                for file_type, file_path in result.generated_files.items():
                    self.logger.info(f"Generated {file_type}: {file_path}")
            
            else:
                self.logger.error(
                    f"Documentation generation failed after {duration:.1f}ms",
                    errors=result.errors,
                    warnings=result.warnings
                )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Documentation generation script failed: {e}")
            raise
    
    async def analyze_documentation_coverage(self) -> dict:
        """
        Analyze current documentation coverage.
        
        Returns:
            Coverage analysis results
        """
        self.logger.info("Analyzing documentation coverage")
        
        try:
            # Quick analysis for coverage calculation
            config = DocumentationConfig(
                project_root=self.project_root,
                docs_output_dir=self.project_root / "docs",
                analyze_code=True,
                enabled_types=[],  # No generation, just analysis
                validate_output=False
            )
            
            generator = DocumentationGenerator(
                config=config,
                ast_analyzer=self.ast_analyzer,
                safety_validator=self.safety_validator
            )
            
            # Perform analysis only
            result = await generator.generate_documentation()
            
            # Calculate coverage metrics
            total_functions = result.metadata.functions_analyzed
            total_classes = result.metadata.classes_analyzed
            total_items = total_functions + total_classes
            
            # Check existing documentation
            docs_dir = self.project_root / "docs"
            existing_readme = (docs_dir / "README.md").exists()
            existing_api_docs = (docs_dir / "api-reference.md").exists()
            existing_changelog = (docs_dir / "CHANGELOG.md").exists()
            
            coverage_score = 0.0
            if total_items > 0:
                # Simple coverage calculation based on existing docs
                documented_items = 0
                if existing_api_docs:
                    documented_items += total_items * 0.8  # Assume 80% coverage from API docs
                if existing_readme:
                    documented_items += total_items * 0.2  # Assume 20% additional from README
                
                coverage_score = min(1.0, documented_items / total_items)
            
            coverage_analysis = {
                'total_functions': total_functions,
                'total_classes': total_classes,
                'total_items': total_items,
                'existing_documentation': {
                    'readme': existing_readme,
                    'api_docs': existing_api_docs,
                    'changelog': existing_changelog
                },
                'coverage_score': coverage_score,
                'coverage_percentage': coverage_score * 100,
                'recommendations': []
            }
            
            # Generate recommendations
            if coverage_score < 0.5:
                coverage_analysis['recommendations'].append("Generate comprehensive API documentation")
            if not existing_readme:
                coverage_analysis['recommendations'].append("Create project README with overview and usage")
            if not existing_changelog:
                coverage_analysis['recommendations'].append("Generate changelog from git history")
            if coverage_score < 0.8:
                coverage_analysis['recommendations'].append("Add code examples and usage documentation")
            
            self.logger.info(
                f"Documentation coverage analysis completed: {coverage_score:.1%} coverage",
                **coverage_analysis
            )
            
            return coverage_analysis
            
        except Exception as e:
            self.logger.error(f"Coverage analysis failed: {e}")
            raise
    
    def validate_documentation_safety(self, docs_dir: Path) -> dict:
        """
        Validate existing documentation for safety compliance.
        
        Args:
            docs_dir: Directory containing documentation files
            
        Returns:
            Safety validation results
        """
        self.logger.info(f"Validating documentation safety in {docs_dir}")
        
        validation_results = {
            'files_checked': 0,
            'files_passed': 0,
            'files_failed': 0,
            'total_violations': 0,
            'safety_score': 1.0,
            'violations_by_file': {}
        }
        
        try:
            # Find documentation files
            doc_files = []
            for pattern in ['*.md', '*.rst', '*.txt']:
                doc_files.extend(docs_dir.glob(f"**/{pattern}"))
            
            total_safety_score = 0.0
            
            for doc_file in doc_files:
                try:
                    content = doc_file.read_text(encoding='utf-8')
                    
                    # Validate content safety
                    validation_result = self.safety_validator.validate_content(content)
                    
                    validation_results['files_checked'] += 1
                    total_safety_score += validation_result.safety_score
                    
                    if validation_result.safety_score >= 0.8:
                        validation_results['files_passed'] += 1
                    else:
                        validation_results['files_failed'] += 1
                        validation_results['violations_by_file'][str(doc_file)] = {
                            'safety_score': validation_result.safety_score,
                            'violations': validation_result.violations
                        }
                        validation_results['total_violations'] += len(validation_result.violations)
                
                except Exception as e:
                    self.logger.warning(f"Failed to validate {doc_file}: {e}")
            
            # Calculate overall safety score
            if validation_results['files_checked'] > 0:
                validation_results['safety_score'] = total_safety_score / validation_results['files_checked']
            
            self.logger.info(
                f"Documentation safety validation completed: "
                f"{validation_results['files_passed']}/{validation_results['files_checked']} files passed",
                **validation_results
            )
            
            return validation_results
            
        except Exception as e:
            self.logger.error(f"Documentation safety validation failed: {e}")
            raise


async def main():
    """Main documentation generation automation function."""
    parser = argparse.ArgumentParser(
        description="Automated documentation generation for CoachNTT.ai",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--type",
        choices=["readme", "api", "changelog", "architecture", "diagrams", "reference", "all"],
        default="all",
        help="Documentation type to generate"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output directory for generated docs"
    )
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="Only analyze code, don't generate docs"
    )
    parser.add_argument(
        "--include-diagrams",
        action="store_true",
        help="Generate architecture diagrams"
    )
    parser.add_argument(
        "--validate-safety",
        action="store_true",
        default=True,
        help="Validate generated content for safety compliance"
    )
    parser.add_argument(
        "--coverage-analysis",
        action="store_true",
        help="Analyze documentation coverage"
    )
    parser.add_argument(
        "--safety-check",
        action="store_true",
        help="Check existing documentation for safety violations"
    )
    parser.add_argument(
        "--project-name",
        default="CoachNTT.ai",
        help="Project name for documentation"
    )
    
    args = parser.parse_args()
    
    # Initialize script
    script = DocumentationAutomationScript()
    
    try:
        # Perform coverage analysis if requested
        if args.coverage_analysis:
            coverage_result = await script.analyze_documentation_coverage()
            print(f"\nDocumentation Coverage Analysis:")
            print(f"Total Functions: {coverage_result['total_functions']}")
            print(f"Total Classes: {coverage_result['total_classes']}")
            print(f"Coverage Score: {coverage_result['coverage_percentage']:.1f}%")
            if coverage_result['recommendations']:
                print("Recommendations:")
                for rec in coverage_result['recommendations']:
                    print(f"  - {rec}")
        
        # Perform safety check if requested
        if args.safety_check:
            docs_dir = args.output or (script.project_root / "docs")
            if docs_dir.exists():
                safety_result = script.validate_documentation_safety(docs_dir)
                print(f"\nDocumentation Safety Validation:")
                print(f"Files Checked: {safety_result['files_checked']}")
                print(f"Files Passed: {safety_result['files_passed']}")
                print(f"Safety Score: {safety_result['safety_score']:.3f}")
                if safety_result['total_violations'] > 0:
                    print(f"Total Violations: {safety_result['total_violations']}")
            else:
                print(f"Documentation directory not found: {docs_dir}")
        
        # Generate documentation if not doing analysis only
        if not args.coverage_analysis and not args.safety_check:
            doc_types = [args.type] if args.type != "all" else ["all"]
            
            result = await script.run_documentation_generation(
                doc_types=doc_types,
                output_dir=args.output,
                analyze_only=args.analyze_only,
                include_diagrams=args.include_diagrams,
                validate_safety=args.validate_safety,
                project_name=args.project_name
            )
            
            # Print summary
            print(f"\nDocumentation Generation Results:")
            print(f"Success: {result.success}")
            print(f"Sections Generated: {len(result.sections)}")
            print(f"Diagrams Generated: {len(result.diagrams)}")
            print(f"Files Generated: {len(result.generated_files)}")
            print(f"Processing Time: {result.total_processing_time_ms}ms")
            print(f"Safety Score: {result.metadata.safety_score}")
            
            if result.errors:
                print(f"\nErrors ({len(result.errors)}):")
                for error in result.errors:
                    print(f"  - {error}")
            
            if result.warnings:
                print(f"\nWarnings ({len(result.warnings)}):")
                for warning in result.warnings:
                    print(f"  - {warning}")
            
            # Return appropriate exit code
            return 0 if result.success else 1
        
        return 0
        
    except KeyboardInterrupt:
        print("\nDocumentation generation cancelled by user.")
        return 1
    except Exception as e:
        print(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)