# CRS CSV Export Schema

The CRS CSV export flattens the hierarchical CRS document into a list of artifacts. Each row in the CSV represents a single artifact (Header, Text, Requirement, etc.).

## Columns

| Column | Description |
|--------|-------------|
| `artifact_id` | Unique identifier for the artifact (e.g., "FR-001", "SEC-1-2"). |
| `type` | Type of artifact: `header`, `text`, `req`, `constraint`, `note`. |
| `label` | Optional label. |
| `parent_id` | ID of the parent artifact (for hierarchy). |
| `order_index` | Integer defining the order of the artifact document. |
| `title` | Title of the section or requirement. |
| `content` | The main text content or description. |
| `doc_id` | ID of the CRS document. |
| `doc_version` | Version number of the CRS document. |
| `doc_section_path` | Breadcrumb path (e.g., "/Project/Functional Requirements"). |
| `req_type` | Specific requirement type: `functional`, `performance`, `security`, `objective`, etc. |
| `priority` | Priority level: `high`, `medium`, `low`. |
| `stakeholder` | Related stakeholder (if available). |
| `acceptance_criteria` | Acceptance criteria textual representation. |
| `status` | Artifact status (default blank/active). |
| `source` | Source of the requirement. |
| `related_artifact_id` | IDs of related artifacts. |
| `rationale` | Rationale for the requirement. |
| `verification_method` | Method to verify the requirement (e.g., "Test", "Inspection"). |
| `risk_level` | Associated risk level. |
| `complexity` | Complexity estimation. |
| `created_by` | User ID who created the document. |
| `created_date` | Date of document creation. |
| `last_modified` | Date of last modification. |
| `in_scope` | Boolean indicating if the item is in scope. |

## Example Row

```csv
artifact_id,type,label,parent_id,order_index,title,content,doc_id,doc_version,doc_section_path,req_type,priority,stakeholder,acceptance_criteria,status,source,related_artifact_id,rationale,verification_method,risk_level,complexity,created_by,created_date,last_modified,in_scope
FR-001,req,,SEC-4,15,User Login,Users must be able to log in with email and password,101,2,/My Project/Functional Requirements,functional,high,,,,,,,,,Test,,,user_1,2023-10-27T10:00:00,,True
```
