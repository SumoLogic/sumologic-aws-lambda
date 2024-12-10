

# Define the JSON schema
AWS_TAG_FILTERS_SCHEMA = {
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "patternProperties": {
    "^[A-Za-z0-9_/]+$": {
      "type": "object",
      "properties": {
        "tags": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "[a-zA-Z0-9=_;,]+$"
          }
        }
      },
      "required": ["tags"],
      "additionalProperties": False
    }
  },
  "additionalProperties": False
}
