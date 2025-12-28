# CRS Commenting System - SPEC-004.3 Implementation

## Overview

This document describes the implementation of the commenting mechanism for CRS (Client Requirements Specification) feedback, as specified in **SPEC-004.3**.

## Specification Requirements

**SPEC-004.3**: Commenting Mechanism
- BA can add comments, suggestions, and clarifications on CRS documents
- Clients can view and respond to comments
- Comments support collaborative feedback workflow

## Architecture

### Database Schema

**Comment Model** (`app/models/comment.py`)
```
comments
├── id (PK)
├── crs_id (FK -> crs_documents.id)
├── author_id (FK -> users.id)
├── content (Text)
├── created_at (DateTime)
└── Relationships:
    ├── crs_document (CRSDocument)
    └── author (User)
```

### API Endpoints

All endpoints are prefixed with `/api` and tagged as `comments`.

#### Access Control

The API enforces the following access control rules:

1.  **Authentication**: All endpoints require a valid JWT token.
2.  **Role-Based Access**:
    *   **BAs**: Can view and comment on CRS documents for **projects they are assigned to**, provided the CRS is **not in Draft status**.
    *   **Clients**: Can view and comment on CRS documents for projects where they are a team member or the project creator.
3.  **Ownership**:
    *   Update/Delete operations are restricted to the author of the comment.
    *   Validation ensures a user cannot modify another user's comments.

### Validation

- **CRS Status**: BAs cannot access or comment on CRS documents with status `draft`.
- **Project Membership**: Both BAs and Clients must be members of the project's team to access its CRS comments.
- **Content**: Comments must be non-empty and less than 5000 characters.
- **Existence**: Checks for valid `crs_id` and `comment_id`.

#### 1. Create Comment
- **Endpoint**: `POST /api/comments`
- **Authentication**: Required (BA or Client)
- **Access Control**:
  - BAs can comment on CRS (non-draft) for projects they are assigned to
  - Clients can comment on CRS for projects they have access to
- **Request Body**:
  ```json
  {
    "crs_id": 1,
    "content": "Please clarify the authentication requirements in section 2.3"
  }
  ```
- **Response**: `201 Created`
  ```json
  {
    "id": 1,
    "crs_id": 1,
    "author_id": 2,
    "content": "Please clarify...",
    "created_at": "2025-12-26T19:38:20Z",
    "author": {
      "id": 2,
      "full_name": "John Doe",
      "email": "john@example.com",
      "role": "ba"
    }
  }
  ```

#### 2. Get CRS Comments
- **Endpoint**: `GET /api/crs/{crs_id}/comments`
- **Authentication**: Required
- **Query Parameters**:
  - `skip` (default: 0) - Pagination offset
  - `limit` (default: 100, max: 500) - Number of comments to return
- **Response**: `200 OK`
  ```json
  {
    "comments": [...],
    "total": 15,
    "skip": 0,
    "limit": 100
  }
  ```
- **Ordering**: Comments are returned in descending order by `created_at` (newest first)

#### 3. Get Single Comment
- **Endpoint**: `GET /api/comments/{comment_id}`
- **Authentication**: Required
- **Response**: `200 OK` - Single comment object with author information

#### 4. Update Comment
- **Endpoint**: `PUT /api/comments/{comment_id}`
- **Authentication**: Required
- **Access Control**: Users can only update their own comments
- **Request Body**:
  ```json
  {
    "content": "Updated comment with more details"
  }
  ```
- **Response**: `200 OK` - Updated comment object

#### 5. Delete Comment
- **Endpoint**: `DELETE /api/comments/{comment_id}`
- **Authentication**: Required
- **Access Control**: Users can only delete their own comments
- **Response**: `204 No Content`

## Service Layer

**Comment Service** (`app/services/comment_service.py`)

Provides business logic for comment operations:
- `create_comment()` - Create a new comment with validation
- `get_comments_by_crs()` - Retrieve comments with pagination
- `get_comment_by_id()` - Retrieve a specific comment
- `update_comment()` - Update comment content
- `delete_comment()` - Delete a comment
- `get_comments_count_by_crs()` - Get total comment count for pagination

## Access Control

### BA Users
- Can view/comment on CRS documents for **projects they are assigned to**
- Can ONLY access CRS documents that are **NOT in Draft status**
- Can update/delete their own comments

### Client Users
- Can only view CRS documents for projects they have access to:
  - Projects they created
  - Projects where they are team members
- Can add comments to accessible CRS documents
- Can update/delete their own comments

### Verification Flow
1. Verify CRS document exists
2. Check user role:
   - **BA**: Verify project team membership AND ensure CRS is not `draft`
   - **Client**: Verify project ownership or team membership
3. For update/delete: Verify comment ownership

## Validation

### Comment Content
- **Required**: Cannot be empty
- **Min Length**: 1 character
- **Max Length**: 5000 characters
- **Type**: Plain text (no HTML sanitization in current version)

## Integration with Existing Features

### CRS Workflow (SPEC-004)
Comments integrate with the CRS review workflow:
1. **SPEC-004.1**: BA accesses CRS documents
2. **SPEC-004.2**: BA reviews CRS in structured format
3. **SPEC-004.3**: BA adds comments (THIS FEATURE)
4. **SPEC-004.4**: Client receives notification of feedback
5. **SPEC-004.5**: CRS status updated based on feedback resolution

### Notification System
When a comment is created, the system should trigger notifications:
- Notify project team members
- Notify CRS creator
- Notify BA assigned to the project

**Note**: Notification integration is not implemented in this version but is recommended for SPEC-004.4.

## Testing

Comprehensive test suite in `tests/test_comments.py` covers:
- ✅ Comment creation by BA and Client
- ✅ Access control verification
- ✅ Pagination and ordering
- ✅ Comment retrieval (list and single)
- ✅ Comment updates (owner only)
- ✅ Comment deletion (owner only)
- ✅ Validation (empty content, max length)
- ✅ Cross-project access prevention

### Running Tests
```bash
pytest tests/test_comments.py -v
```

## Usage Examples

### BA Adding Feedback
```python
# BA reviews CRS and adds clarification request
POST /api/comments
{
  "crs_id": 123,
  "content": "Section 2.3 mentions 'secure authentication' but doesn't specify the method. Please clarify if you need OAuth2, JWT, or another approach."
}
```

### Client Responding to Feedback
```python
# Client responds to BA's comment
POST /api/comments
{
  "crs_id": 123,
  "content": "We need OAuth2 with Google and GitHub providers. I'll update section 2.3 to reflect this."
}
```

### Viewing All Comments on a CRS
```python
# Get all comments for review
GET /api/crs/123/comments?skip=0&limit=50
```

## Future Enhancements

1. **Threading/Replies**: Allow comments to reply to other comments
2. **Mentions**: Support @mentions to notify specific users
3. **Rich Text**: Support markdown formatting in comments
4. **Attachments**: Allow file attachments with comments
5. **Comment Resolution**: Mark comments as resolved/unresolved
6. **Comment Types**: Categorize comments (question, suggestion, issue, etc.)
7. **Real-time Updates**: WebSocket support for live comment updates
8. **Email Notifications**: Send email when comments are added (SPEC-004.4)

## API Documentation

Full API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

Look for the `comments` tag in the API documentation.

## Error Handling

| Status Code | Description |
|-------------|-------------|
| 201 | Comment created successfully |
| 200 | Comment retrieved/updated successfully |
| 204 | Comment deleted successfully |
| 400 | Invalid request (validation error) |
| 401 | Unauthorized (no authentication) |
| 403 | Forbidden (no access to resource) |
| 404 | Comment or CRS not found |
| 422 | Validation error (Pydantic) |
| 500 | Internal server error |

## Security Considerations

1. **Authentication**: All endpoints require valid JWT token
2. **Authorization**: Role-based and ownership-based access control
3. **Input Validation**: Pydantic schemas validate all inputs
4. **SQL Injection**: SQLAlchemy ORM prevents SQL injection
5. **XSS Prevention**: Consider sanitizing HTML if rich text is added

## Database Migration

The `comments` table is included in the initial schema (`531baa9737e9`). No new migration is required if the database was initialized with the standard schema.

To ensure your database is up to date:

```bash
alembic upgrade head
```

## Monitoring and Logging

The service layer logs important events:
- Comment creation: `INFO` level
- Comment updates: `INFO` level
- Comment deletion: `INFO` level
- Errors: `ERROR` level

Example log:
```
INFO: Comment 42 created on CRS 123 by user 5
INFO: Comment 42 updated
INFO: Comment 42 deleted
```

## Performance Considerations

1. **Pagination**: Default limit of 100, max 500 to prevent large queries
2. **Indexing**: Foreign keys are indexed for efficient queries
3. **Eager Loading**: Author information is loaded separately (consider JOIN optimization)
4. **Caching**: Consider caching comment counts for high-traffic CRS documents

## Conclusion

This implementation provides a solid foundation for the CRS commenting system as specified in SPEC-004.3. It enables collaborative feedback between BAs and clients, with proper access control and a clean API interface.
