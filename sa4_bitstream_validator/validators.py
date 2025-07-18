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
        "Validate the description"
        try:
            schema = xmlschema.XMLSchema11(schema_path, validation="lax")
            schema.validate(description_path)
            return True
        except xmlschema.XMLSchemaValidationError as e:
            print(f"Validation failed: {e}")
            return False
        except Exception as e:
            print(f"Error during validation: {e}")
            return False
