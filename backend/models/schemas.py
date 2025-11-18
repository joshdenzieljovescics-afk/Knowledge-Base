"""JSON schemas for API requests and responses."""

JSON_SCHEMA = """{
  "chunks": [
    {
      "text": "string",
      "metadata": {
        "type": "heading|paragraph|list|table|image",
        "section": "string",
        "context": "string (maximum one sentence)",
        "tags": ["string"],
        "row_index": "integer (for tables only) or null",
        "continues": "boolean",
        "is_page_break": "boolean",
        "siblings": ["string"],  
        "page": "integer"
      }
    }
  ]
}"""
