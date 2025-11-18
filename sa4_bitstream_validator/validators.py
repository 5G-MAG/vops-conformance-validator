"""
    Classes to perform validation rules.
"""

import abc
import json

import xmlschema

class BaseValidator(abc.ABC):
    @abc.abstractmethod
    def validate(self, description_path, schema_path):
        "Validate the description"

class XMLValidator(BaseValidator):
    def validate(self, description_path, schema_path):
        """Validate the description and collect all errors.
        
        Returns:
            tuple: (success: bool, errors: list of error details)
        """
        errors = []
        try:
            schema = xmlschema.XMLSchema11(schema_path, validation="strict")
            validation_errors = list(schema.iter_errors(description_path))
            
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
            
            return len(errors) == 0, errors
            
        except Exception as e:
            # For schema loading errors, create a single error entry
            error_detail = {
                "reason": f"Schema loading error: {str(e)}",
                "path": schema_path
            }
            return False, [error_detail]

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
            
            success, errors = self.validate(description_path, schema_path)
            
            # Store detailed results
            results[schema_path] = {
                "success": success,
                "errors": errors,
                "error_count": len(errors)
            }
            
            if verbose:
                if errors:
                    print(f"[FAILED] Validation failed with {len(errors)} error(s)")
                    for j, error in enumerate(errors, 1):
                        error_msg = error["reason"]
                        if error["path"]:
                            error_msg += f" at path {error['path']}"
                        print(f"  Error {j}: {error_msg}")
                else:
                    print("[PASSED] Validation passed")
                    
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
