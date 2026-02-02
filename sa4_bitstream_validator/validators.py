"""
    Classes to perform validation rules.
"""

import abc
import json
import xml.etree.ElementTree as ET

import xmlschema


def extract_assertions_from_xsd(schema_path):
    """Extract assertion information from an XSD file.

    Args:
        schema_path: Path to the XSD schema file

    Returns:
        list: List of assertion details with test expressions and descriptions
    """
    assertions = []

    try:
        # Parse the XSD file
        tree = ET.parse(schema_path)
        root = tree.getroot()

        # Define namespace for XSD 1.1
        ns = {'xs': 'http://www.w3.org/2001/XMLSchema'}

        # Find all assertion elements
        for assert_elem in root.findall('.//xs:assert', ns):
            test_expr = assert_elem.get('test', '')

            # Extract description from preceding comment if available
            description = ""
            # Note: getprevious() is not available in standard ElementTree
            # We'll use the test expression as the description for now
            description = test_expr

            assertions.append({
                'test': test_expr,
                'description': description,
                'schema_path': schema_path
            })

    except Exception as e:
        # If parsing fails, return empty list
        print(f"Warning: Could not extract assertions from {schema_path}: {e}")

    return assertions


class BaseValidator(abc.ABC):
    @abc.abstractmethod
    def validate(self, description_path, schema_path):
        "Validate the description"

class XMLValidator(BaseValidator):
    def validate(self, description_path, schema_path):
        """Validate the description and collect all errors.

        Returns:
            tuple: (success: bool, errors: list of error details, assertion_results: dict)
        """
        errors = []
        assertion_results = {
            'passing_assertions': [],
            'failing_assertions': [],
            'total_assertions': 0
        }

        try:
            # Extract assertions from the schema
            assertions = extract_assertions_from_xsd(schema_path)
            assertion_results['total_assertions'] = len(assertions)

            schema = xmlschema.XMLSchema11(schema_path, validation="strict")
            validation_errors = list(schema.iter_errors(description_path))

            # If no errors, all assertions passed
            if len(validation_errors) == 0:
                assertion_results['passing_assertions'] = assertions
                return True, errors, assertion_results

            # Process validation errors
            for error in validation_errors:
                # Extract detailed error information
                error_detail = {
                    "reason": error.reason if error.reason else "assertion test is false",
                    "path": None
                }

                # Extract XPath context from validator
                if hasattr(error.validator, 'path') and error.validator.path:
                    error_detail["path"] = error.validator.path
                elif hasattr(error, 'path') and error.path:
                    error_detail["path"] = error.path

                errors.append(error_detail)

                # Try to match the error with specific assertions
                error_path = error_detail["path"] or ""
                for assertion in assertions:
                    if error_path and assertion['test'] in error_path:
                        # This assertion failed
                        failing_assertion = assertion.copy()
                        failing_assertion['error'] = error_detail["reason"]
                        failing_assertion['error_path'] = error_path
                        assertion_results['failing_assertions'].append(failing_assertion)
                    # Don't add to passing_assertions here - we'll handle that after processing all errors

            # After processing all errors, determine which assertions passed
            # An assertion passes if it's not in the failing_assertions list
            failing_tests = {assertion['test'] for assertion in assertion_results['failing_assertions']}
            for assertion in assertions:
                if assertion['test'] not in failing_tests:
                    assertion_results['passing_assertions'].append(assertion)

            # Remove duplicates from passing assertions
            passing_set = set()
            unique_passing = []
            for assertion in assertion_results['passing_assertions']:
                key = assertion['test']
                if key not in passing_set:
                    passing_set.add(key)
                    unique_passing.append(assertion)
            assertion_results['passing_assertions'] = unique_passing

            # Remove duplicates from failing assertions
            failing_set = set()
            unique_failing = []
            for assertion in assertion_results['failing_assertions']:
                key = assertion['test']
                if key not in failing_set:
                    failing_set.add(key)
                    unique_failing.append(assertion)
            assertion_results['failing_assertions'] = unique_failing

            return len(errors) == 0, errors, assertion_results

        except Exception as e:
            # For schema loading errors, create a single error entry
            error_detail = {
                "reason": f"Schema loading error: {str(e)}",
                "path": schema_path
            }
            return False, [error_detail], assertion_results

    def validate_multiple(self, description_path, schema_paths, verbose=True):
        """Validate the description against multiple XSD schemas.
        
        Args:
            description_path: Path to the XML description file
            schema_paths: List of paths to XSD schema files
            verbose: Whether to print detailed output to console
            
        Returns:
            dict: Validation results for each schema
        """
        results = {}
        overall_success = True
        
        for i, schema_path in enumerate(schema_paths, 1):
            if verbose:
                print(f"\n=== Validating against schema {i}/{len(schema_paths)}: {schema_path} ===")
            
            success, errors, assertion_results = self.validate(description_path, schema_path)

            # Store detailed results
            results[schema_path] = {
                "success": success,
                "errors": errors,
                "error_count": len(errors),
                "assertion_results": assertion_results
            }
            
            if verbose:
                if errors:
                    print(f"[FAILED] Validation failed with {len(errors)} error(s)")
                    for j, error in enumerate(errors, 1):
                        error_msg = error["reason"]
                        if error["path"]:
                            error_msg += f" at path {error['path']}"
                        print(f"  Error {j}: {error_msg}")

                    # Show only failing assertions for concise output
                    if assertion_results['failing_assertions']:
                        print(f"\n  Failing assertions ({len(assertion_results['failing_assertions'])}/{assertion_results['total_assertions']}):")
                        for j, assertion in enumerate(assertion_results['failing_assertions'], 1):
                            desc = assertion.get('description', 'No description')
                            print(f"    {j}. {desc}")
                            if 'error' in assertion:
                                print(f"       Error: {assertion['error']}")
                else:
                    print("[PASSED] Validation passed")

                    # Show assertion results for successful validation
                    if assertion_results['total_assertions'] > 0:
                        print(f"  All {assertion_results['total_assertions']} assertions passed")
                    
            if not success:
                overall_success = False
        
        if verbose:
            print(f"\n=== Overall Validation Result ===")
            if overall_success:
                print("[SUCCESS] All validations passed")
            else:
                print("[FAILED] One or more validations failed")
            
        return {
            "overall_success": overall_success,
            "schema_results": results,
            "total_schemas": len(schema_paths),
            "passed_schemas": sum(1 for r in results.values() if r["success"]),
            "failed_schemas": sum(1 for r in results.values() if not r["success"])
        }
