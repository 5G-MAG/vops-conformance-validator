"""
    Classes to perform validation rules.
"""

import abc

import xmlschema

class BaseValidator(abc.ABC):
    @abc.abstractmethod
    def validate(self, description_path, schema_path):
        "Validate the description"

class XMLValidator(BaseValidator):
    def validate(self, description_path, schema_path):
        "Validate the description and collect all errors"
        try:
            schema = xmlschema.XMLSchema11(schema_path, validation="strict")
            errors = list(schema.iter_errors(description_path))
            
            if errors:
                print(f"Validation failed with {len(errors)} error(s):")
                for i, error in enumerate(errors, 1):
                    # Extract concise error information
                    error_msg = ""
                    
                    # Get the reason if available
                    if error.reason:
                        error_msg = error.reason
                    else:
                        error_msg = "assertion test is false"
                    
                    # Extract XPath context from validator
                    if hasattr(error.validator, 'path') and error.validator.path:
                        # Truncate long XPath expressions for readability
                        xpath = error.validator.path
                        if len(xpath) > 80:
                            xpath = xpath[:77] + "..."
                        error_msg += f" for XPath: {xpath}"
                    elif hasattr(error, 'path') and error.path:
                        error_msg += f" at path {error.path}"
                    
                    print(f"Error {i}: {error_msg}")
                return False
            else:
                return True
        except Exception as e:
            print(f"Error during validation: {e}")
            return False

    def validate_multiple(self, description_path, schema_paths):
        """Validate the description against multiple XSD schemas and report results for each."""
        overall_success = True
        
        for i, schema_path in enumerate(schema_paths, 1):
            print(f"\n=== Validating against schema {i}/{len(schema_paths)}: {schema_path} ===")
            
            try:
                schema = xmlschema.XMLSchema11(schema_path, validation="strict")
                errors = list(schema.iter_errors(description_path))
                
                if errors:
                    print(f"[FAILED] Validation failed with {len(errors)} error(s)")
                    for j, error in enumerate(errors, 1):
                        # Extract concise error information
                        error_msg = ""
                        
                        # Get the reason if available
                        if error.reason:
                            error_msg = error.reason
                        else:
                            error_msg = "assertion test is false"
                        
                        # Extract XPath context from validator
                        if hasattr(error.validator, 'path') and error.validator.path:
                            # Truncate long XPath expressions for readability
                            xpath = error.validator.path
                            if len(xpath) > 80:
                                xpath = xpath[:77] + "..."
                            error_msg += f" for XPath: {xpath}"
                        elif hasattr(error, 'path') and error.path:
                            error_msg += f" at path {error.path}"
                        
                        print(f"  Error {j}: {error_msg}")
                    overall_success = False
                else:
                    print("[PASSED] Validation passed")
                    
            except Exception as e:
                print(f"[ERROR] Error during validation: {e}")
                overall_success = False
        
        print(f"\n=== Overall Validation Result ===")
        if overall_success:
            print("[SUCCESS] All validations passed")
        else:
            print("[FAILED] One or more validations failed")
            
        return overall_success
