# Documentation Generation Templates

This directory contains standardized templates for generating comprehensive documentation for the Conversational State Engine (CSE) project. These templates are designed to be filled out by engineers as they analyze the codebase and identify gaps between design specifications and actual implementation.

## Template Structure

### 1. Component Analysis Templates
- `component-analysis.md` - For analyzing individual components
- `api-analysis.md` - For analyzing API endpoints and contracts
- `database-analysis.md` - For analyzing database schema and operations

### 2. Gap Analysis Templates
- `design-gap-analysis.md` - For identifying discrepancies between design.md and implementation
- `feature-gap-analysis.md` - For tracking missing or incomplete features

### 3. Architecture Documentation Templates
- `system-overview.md` - High-level system architecture documentation
- `data-flow.md` - Data flow and state management documentation
- `integration-points.md` - External integrations and interfaces

## Usage Instructions

1. **Choose appropriate template** based on the component or area you're analyzing
2. **Fill in all sections** thoroughly, marking "N/A" for non-applicable items
3. **Include code references** using the pattern `file_path:line_number`
4. **Document gaps clearly** with severity levels and recommended actions
5. **Save completed documentation** in the `docs/` directory with descriptive filenames

## Quality Standards

- **Accuracy**: All information must be verified against actual code
- **Completeness**: All template sections must be addressed
- **Clarity**: Use clear, concise language suitable for technical stakeholders
- **Traceability**: Include specific file and line references for all claims
- **Actionability**: Gap findings must include concrete next steps

## File Naming Convention

Completed documentation should follow this pattern:
- Component analysis: `docs/components/[component-name]-analysis.md`
- API analysis: `docs/api/[endpoint-group]-analysis.md`
- Gap analysis: `docs/gaps/[area]-gaps.md`
- Architecture docs: `docs/architecture/[system-area].md`