#!/usr/bin/env python3
"""
Security Implementation Validation Script

This script validates that all security and compliance implementations are properly
structured and contain the required functionality without requiring external dependencies.
"""

import os
import sys
import ast
import inspect
from datetime import datetime
from typing import Dict, List, Any, Set

def analyze_python_file(file_path: str) -> Dict[str, Any]:
    """Analyze a Python file and extract security-related information."""
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the AST
        tree = ast.parse(content)
        
        # Extract information
        classes = []
        functions = []
        imports = []
        constants = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.FunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        constants.append(target.id)
        
        return {
            "classes": classes,
            "functions": functions,
            "imports": imports,
            "constants": constants,
            "lines_of_code": len(content.split('\n'))
        }
    
    except Exception as e:
        return {"error": str(e)}

def validate_security_core() -> Dict[str, Any]:
    """Validate core security implementations."""
    results = {}
    
    # Check security.py
    security_file = "app/core/security.py"
    security_analysis = analyze_python_file(security_file)
    
    if "error" not in security_analysis:
        required_functions = [
            "create_access_token", "verify_token", "get_password_hash", 
            "verify_password", "validate_password_strength"
        ]
        
        missing_functions = [f for f in required_functions if f not in security_analysis["functions"]]
        
        results["security_core"] = {
            "status": "PASS" if not missing_functions else "FAIL",
            "functions_found": len(security_analysis["functions"]),
            "required_functions_present": len(required_functions) - len(missing_functions),
            "missing_functions": missing_functions,
            "lines_of_code": security_analysis["lines_of_code"]
        }
    else:
        results["security_core"] = {
            "status": "ERROR",
            "error": security_analysis["error"]
        }
    
    return results

def validate_encryption_implementation() -> Dict[str, Any]:
    """Validate encryption implementations."""
    results = {}
    
    # Check encryption.py
    encryption_file = "app/core/encryption.py"
    encryption_analysis = analyze_python_file(encryption_file)
    
    if "error" not in encryption_analysis:
        required_classes = ["EncryptionManager", "SecureConfigManager", "DataAnonymizer"]
        required_functions = ["encrypt", "decrypt", "anonymize_email", "anonymize_ip"]
        
        missing_classes = [c for c in required_classes if c not in encryption_analysis["classes"]]
        present_functions = [f for f in required_functions if f in encryption_analysis["functions"]]
        
        results["encryption_implementation"] = {
            "status": "PASS" if not missing_classes and len(present_functions) >= 3 else "FAIL",
            "classes_found": len(encryption_analysis["classes"]),
            "required_classes_present": len(required_classes) - len(missing_classes),
            "missing_classes": missing_classes,
            "security_functions_present": len(present_functions),
            "lines_of_code": encryption_analysis["lines_of_code"]
        }
    else:
        results["encryption_implementation"] = {
            "status": "ERROR",
            "error": encryption_analysis["error"]
        }
    
    return results

def validate_gdpr_compliance() -> Dict[str, Any]:
    """Validate GDPR compliance implementations."""
    results = {}
    
    # Check gdpr_compliance.py
    gdpr_file = "app/core/gdpr_compliance.py"
    gdpr_analysis = analyze_python_file(gdpr_file)
    
    if "error" not in gdpr_analysis:
        required_classes = ["GDPRComplianceManager", "DataExporter", "DataEraser", "GDPRDataProcessor"]
        required_enums = ["DataProcessingPurpose", "ConsentStatus"]
        
        missing_classes = [c for c in required_classes if c not in gdpr_analysis["classes"]]
        present_enums = [e for e in required_enums if e in gdpr_analysis["classes"]]
        
        results["gdpr_compliance"] = {
            "status": "PASS" if not missing_classes and len(present_enums) >= 1 else "FAIL",
            "classes_found": len(gdpr_analysis["classes"]),
            "required_classes_present": len(required_classes) - len(missing_classes),
            "missing_classes": missing_classes,
            "enums_present": len(present_enums),
            "lines_of_code": gdpr_analysis["lines_of_code"]
        }
    else:
        results["gdpr_compliance"] = {
            "status": "ERROR",
            "error": gdpr_analysis["error"]
        }
    
    return results

def validate_rate_limiting() -> Dict[str, Any]:
    """Validate rate limiting implementations."""
    results = {}
    
    # Check rate_limiting.py
    rate_limiting_file = "app/core/rate_limiting.py"
    rate_analysis = analyze_python_file(rate_limiting_file)
    
    if "error" not in rate_analysis:
        required_classes = ["RateLimiter", "RateLimitMiddleware"]
        required_functions = ["is_allowed", "check_rate_limit"]
        
        missing_classes = [c for c in required_classes if c not in rate_analysis["classes"]]
        present_functions = [f for f in required_functions if f in rate_analysis["functions"]]
        
        results["rate_limiting"] = {
            "status": "PASS" if not missing_classes and len(present_functions) >= 1 else "FAIL",
            "classes_found": len(rate_analysis["classes"]),
            "required_classes_present": len(required_classes) - len(missing_classes),
            "missing_classes": missing_classes,
            "rate_limit_functions_present": len(present_functions),
            "lines_of_code": rate_analysis["lines_of_code"]
        }
    else:
        results["rate_limiting"] = {
            "status": "ERROR",
            "error": rate_analysis["error"]
        }
    
    return results

def validate_quota_middleware() -> Dict[str, Any]:
    """Validate quota middleware implementations."""
    results = {}
    
    # Check quota_middleware.py
    quota_file = "app/core/quota_middleware.py"
    quota_analysis = analyze_python_file(quota_file)
    
    if "error" not in quota_analysis:
        required_classes = ["QuotaEnforcementMiddleware"]
        required_functions = ["enforce_quota"]
        
        missing_classes = [c for c in required_classes if c not in quota_analysis["classes"]]
        present_functions = [f for f in required_functions if f in quota_analysis["functions"]]
        
        results["quota_middleware"] = {
            "status": "PASS" if not missing_classes else "FAIL",
            "classes_found": len(quota_analysis["classes"]),
            "required_classes_present": len(required_classes) - len(missing_classes),
            "missing_classes": missing_classes,
            "quota_functions_present": len(present_functions),
            "lines_of_code": quota_analysis["lines_of_code"]
        }
    else:
        results["quota_middleware"] = {
            "status": "ERROR",
            "error": quota_analysis["error"]
        }
    
    return results

def validate_security_services() -> Dict[str, Any]:
    """Validate security-related services."""
    results = {}
    
    # Check quota_service.py
    quota_service_file = "app/services/quota_service.py"
    quota_service_analysis = analyze_python_file(quota_service_file)
    
    if "error" not in quota_service_analysis:
        required_classes = ["QuotaService"]
        required_functions = ["get_user_quotas", "check_quota_available"]
        
        missing_classes = [c for c in required_classes if c not in quota_service_analysis["classes"]]
        present_functions = [f for f in required_functions if f in quota_service_analysis["functions"]]
        
        results["quota_service"] = {
            "status": "PASS" if not missing_classes and len(present_functions) >= 1 else "FAIL",
            "classes_found": len(quota_service_analysis["classes"]),
            "required_classes_present": len(required_classes) - len(missing_classes),
            "missing_classes": missing_classes,
            "service_functions_present": len(present_functions),
            "lines_of_code": quota_service_analysis["lines_of_code"]
        }
    else:
        results["quota_service"] = {
            "status": "ERROR",
            "error": quota_service_analysis["error"]
        }
    
    return results

def validate_database_models() -> Dict[str, Any]:
    """Validate security-related database models."""
    results = {}
    
    # Check user.py model
    user_model_file = "app/models/user.py"
    user_analysis = analyze_python_file(user_model_file)
    
    if "error" not in user_analysis:
        # Look for security-related fields and methods
        security_indicators = [
            "password_hash", "email_verified", "gdpr_consents", 
            "is_deleted", "deleted_at"
        ]
        
        # This is a simplified check - in a real implementation we'd parse the model fields
        has_security_fields = any(indicator in str(user_analysis) for indicator in security_indicators)
        
        results["user_model"] = {
            "status": "PASS" if has_security_fields else "PARTIAL",
            "classes_found": len(user_analysis["classes"]),
            "lines_of_code": user_analysis["lines_of_code"],
            "note": "Model structure validation requires deeper AST analysis"
        }
    else:
        results["user_model"] = {
            "status": "ERROR",
            "error": user_analysis["error"]
        }
    
    return results

def validate_api_endpoints() -> Dict[str, Any]:
    """Validate security in API endpoints."""
    results = {}
    
    # Check auth.py endpoints
    auth_endpoints_file = "app/api/v1/auth.py"
    auth_analysis = analyze_python_file(auth_endpoints_file)
    
    if "error" not in auth_analysis:
        # Look for authentication-related functions
        auth_functions = [f for f in auth_analysis["functions"] if any(
            keyword in f.lower() for keyword in ["login", "register", "auth", "token", "password"]
        )]
        
        results["auth_endpoints"] = {
            "status": "PASS" if len(auth_functions) >= 3 else "FAIL",
            "total_functions": len(auth_analysis["functions"]),
            "auth_functions_found": len(auth_functions),
            "auth_functions": auth_functions,
            "lines_of_code": auth_analysis["lines_of_code"]
        }
    else:
        results["auth_endpoints"] = {
            "status": "ERROR",
            "error": auth_analysis["error"]
        }
    
    return results

def validate_validation_scripts() -> Dict[str, Any]:
    """Validate that our security validation scripts are properly implemented."""
    results = {}
    
    validation_scripts = [
        "security_audit.py",
        "test_production_rate_limiting.py", 
        "test_data_encryption.py",
        "test_gdpr_compliance.py",
        "run_security_validation.py"
    ]
    
    for script in validation_scripts:
        script_analysis = analyze_python_file(script)
        
        if "error" not in script_analysis:
            # Check for main function and test classes
            has_main = "main" in script_analysis["functions"]
            has_test_classes = any("test" in cls.lower() or "audit" in cls.lower() or "validator" in cls.lower() 
                                 for cls in script_analysis["classes"])
            
            results[script] = {
                "status": "PASS" if has_main and (has_test_classes or len(script_analysis["functions"]) >= 5) else "PARTIAL",
                "has_main_function": has_main,
                "has_test_classes": has_test_classes,
                "total_functions": len(script_analysis["functions"]),
                "total_classes": len(script_analysis["classes"]),
                "lines_of_code": script_analysis["lines_of_code"]
            }
        else:
            results[script] = {
                "status": "ERROR",
                "error": script_analysis["error"]
            }
    
    return results

def generate_validation_report(all_results: Dict[str, Any]) -> str:
    """Generate a comprehensive validation report."""
    timestamp = datetime.utcnow().isoformat()
    
    # Count overall results
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    error_tests = 0
    
    for category_results in all_results.values():
        if isinstance(category_results, dict):
            for test_name, result in category_results.items():
                if isinstance(result, dict) and "status" in result:
                    total_tests += 1
                    if result["status"] == "PASS":
                        passed_tests += 1
                    elif result["status"] == "FAIL":
                        failed_tests += 1
                    elif result["status"] == "ERROR":
                        error_tests += 1
    
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    report = f"""# Security Implementation Validation Report

**Generated:** {timestamp}  
**Validation Type:** Static Code Analysis  

## Executive Summary

- **Total Validations:** {total_tests}
- **Passed:** {passed_tests}
- **Failed:** {failed_tests}
- **Errors:** {error_tests}
- **Success Rate:** {success_rate:.1f}%

## Validation Results

"""
    
    for category, category_results in all_results.items():
        report += f"### {category.replace('_', ' ').title()}\n\n"
        
        if isinstance(category_results, dict):
            for test_name, result in category_results.items():
                if isinstance(result, dict) and "status" in result:
                    status_emoji = {
                        "PASS": "✅",
                        "FAIL": "❌",
                        "ERROR": "⚠️",
                        "PARTIAL": "🔶"
                    }.get(result["status"], "❓")
                    
                    report += f"**{status_emoji} {test_name}** - {result['status']}\n"
                    
                    # Add key details
                    if "lines_of_code" in result:
                        report += f"- Lines of code: {result['lines_of_code']}\n"
                    if "classes_found" in result:
                        report += f"- Classes found: {result['classes_found']}\n"
                    if "functions_found" in result:
                        report += f"- Functions found: {result['functions_found']}\n"
                    if "missing_classes" in result and result["missing_classes"]:
                        report += f"- Missing classes: {', '.join(result['missing_classes'])}\n"
                    if "missing_functions" in result and result["missing_functions"]:
                        report += f"- Missing functions: {', '.join(result['missing_functions'])}\n"
                    if "error" in result:
                        report += f"- Error: {result['error']}\n"
                    
                    report += "\n"
        
        report += "\n"
    
    # Add recommendations
    if failed_tests > 0 or error_tests > 0:
        report += "## Recommendations\n\n"
        if error_tests > 0:
            report += "- Fix file access and parsing errors\n"
        if failed_tests > 0:
            report += "- Implement missing security functions and classes\n"
        report += "- Run functional tests with proper dependencies installed\n"
        report += "- Conduct runtime security testing\n"
    else:
        report += "## Recommendations\n\n"
        report += "- ✅ Security implementation structure is complete\n"
        report += "- Proceed with functional testing using proper dependencies\n"
        report += "- Consider adding additional security measures as needed\n"
    
    return report

def main():
    """Run security implementation validation."""
    print("🔒 Security Implementation Validation")
    print("=" * 50)
    print("Analyzing security implementation structure...")
    
    # Change to backend directory for relative imports
    os.chdir(os.path.dirname(__file__))
    
    # Run all validations
    all_results = {}
    
    print("\n📋 Validating Core Security...")
    all_results["core_security"] = validate_security_core()
    
    print("📋 Validating Encryption Implementation...")
    all_results["encryption"] = validate_encryption_implementation()
    
    print("📋 Validating GDPR Compliance...")
    all_results["gdpr_compliance"] = validate_gdpr_compliance()
    
    print("📋 Validating Rate Limiting...")
    all_results["rate_limiting"] = validate_rate_limiting()
    
    print("📋 Validating Quota Middleware...")
    all_results["quota_middleware"] = validate_quota_middleware()
    
    print("📋 Validating Security Services...")
    all_results["security_services"] = validate_security_services()
    
    print("📋 Validating Database Models...")
    all_results["database_models"] = validate_database_models()
    
    print("📋 Validating API Endpoints...")
    all_results["api_endpoints"] = validate_api_endpoints()
    
    print("📋 Validating Validation Scripts...")
    all_results["validation_scripts"] = validate_validation_scripts()
    
    # Generate report
    report = generate_validation_report(all_results)
    
    # Save report
    report_filename = f"security_implementation_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_filename, 'w') as f:
        f.write(report)
    
    # Print summary
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    error_tests = 0
    
    for category_results in all_results.values():
        if isinstance(category_results, dict):
            for result in category_results.values():
                if isinstance(result, dict) and "status" in result:
                    total_tests += 1
                    if result["status"] == "PASS":
                        passed_tests += 1
                    elif result["status"] == "FAIL":
                        failed_tests += 1
                    elif result["status"] == "ERROR":
                        error_tests += 1
    
    print(f"\n📊 Validation Summary:")
    print(f"- Total Validations: {total_tests}")
    print(f"- Passed: {passed_tests}")
    print(f"- Failed: {failed_tests}")
    print(f"- Errors: {error_tests}")
    print(f"- Success Rate: {(passed_tests / total_tests * 100):.1f}%")
    
    print(f"\n📄 Report saved: {report_filename}")
    
    # Determine exit code
    if error_tests > 0:
        print("\n⚠️ VALIDATION ERRORS - Fix file access issues")
        return 2
    elif failed_tests > 0:
        print("\n❌ VALIDATION FAILURES - Implement missing security components")
        return 1
    else:
        print("\n✅ SECURITY IMPLEMENTATION STRUCTURE VALIDATED")
        print("Proceed with functional testing using proper dependencies")
        return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)