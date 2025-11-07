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
                    print(f"Error {i}: {error}")
                return False
            else:
                return True
        except Exception as e:
            print(f"Error during validation: {e}")
            return False
