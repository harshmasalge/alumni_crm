# Legacy Prototype Assessment

## `crm html code.txt`

Useful visual/interaction reference for an early CRM mock-up. It is a single-file HTML/CSS/JavaScript prototype and is not suitable as the production codebase: it has no typed domain model, routing, API boundary, permissions, test structure, or maintainable component system.

## `CRM Codes.txt`

Useful reference for existing Google Sheets column names and earlier workflow assumptions. It is Google Apps Script tied to spreadsheet storage and is not suitable as the system of record required by the RFP. Its data mappings may inform migration templates later.

## Decision

Retain both files unchanged as historical input. Build the new React/FastAPI application independently, and document any adopted field mappings during the M3 migration-workbench checkpoint.
