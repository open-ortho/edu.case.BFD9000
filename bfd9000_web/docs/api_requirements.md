# API Requirements for Frontend

- [API Requirements for Frontend](#api-requirements-for-frontend)
  - [UC01: Add New Records - API Requirements](#uc01-add-new-records---api-requirements)
    - [Complete Workflow for UC01](#complete-workflow-for-uc01)
    - [1. Subject Management](#1-subject-management)
      - [1.1 Search for Subject](#11-search-for-subject)
      - [1.2 Create New Subject](#12-create-new-subject)
      - [1.3 Get Subject Details](#13-get-subject-details)
    - [2. Encounter Management](#2-encounter-management)
      - [2.1 List Encounters for Subject](#21-list-encounters-for-subject)
      - [2.2 Create New Encounter](#22-create-new-encounter)
      - [2.3 Get Encounter Details](#23-get-encounter-details)
      - [2.4 Update Encounter](#24-update-encounter)
      - [2.5 Delete Encounter](#25-delete-encounter)
    - [3. Metadata and Enumerations](#3-metadata-and-enumerations)
      - [3.1 Get All Metadata](#31-get-all-metadata)
    - [4. Record Management](#4-record-management)
      - [4.1 List Records for Encounter](#41-list-records-for-encounter)
      - [4.2 Search Records (Alternative)](#42-search-records-alternative)
    - [5. Record Creation \& Management](#5-record-creation--management)
      - [5.1 Create Record with File Upload](#51-create-record-with-file-upload)
      - [5.2 Get Record Details](#52-get-record-details)
      - [5.3 Update Record Metadata](#53-update-record-metadata)
      - [5.4 Delete Record](#54-delete-record)
    - [6. Image Serving](#6-image-serving)
      - [6.1 Get Record Full Image](#61-get-record-full-image)
      - [6.2 Get Record Thumbnail](#62-get-record-thumbnail)
      - [6.3 Get Record DICOM File](#63-get-record-dicom-file)
    - [7. Background Processing Status](#7-background-processing-status)
      - [7.1 Retry Failed Processing](#71-retry-failed-processing)
  - [UC02: Browse for Records - API Requirements](#uc02-browse-for-records---api-requirements)
    - [Workflow Mapping](#workflow-mapping)
      - [Step 1: Browse/Search Subjects](#step-1-browsesearch-subjects)
      - [Step 2: View Subject Details with Encounters](#step-2-view-subject-details-with-encounters)
      - [Step 3: View Encounter with Records](#step-3-view-encounter-with-records)
      - [Step 4: View Full Record](#step-4-view-full-record)
  - [UC04: Export and Sharing - API Requirements](#uc04-export-and-sharing---api-requirements)
  - [Design Notes and Conventions](#design-notes-and-conventions)
    - [RESTful Resource Hierarchy](#restful-resource-hierarchy)
    - [ID Types](#id-types)
    - [Pagination](#pagination)
    - [Timestamps](#timestamps)
    - [Image URLs](#image-urls)
    - [Nested vs. Direct Access](#nested-vs-direct-access)
    - [Status Enumerations](#status-enumerations)
    - [Real-time Updates](#real-time-updates)
  - [Error Handling and HTTP Status Codes](#error-handling-and-http-status-codes)
    - [Standard Status Codes](#standard-status-codes)
    - [Error Response Format](#error-response-format)
    - [Common Error Codes](#common-error-codes)
    - [Validation Rules](#validation-rules)
  - [Authentication \& Authorization](#authentication--authorization)
    - [9. Authentication](#9-authentication)
      - [9.1 Get Current User](#91-get-current-user)
    - [Authorization Notes](#authorization-notes)
  - [Summary of Required Endpoints](#summary-of-required-endpoints)
    - [Subject Management](#subject-management)
    - [Encounter Management](#encounter-management)
    - [Metadata \& Enumerations](#metadata--enumerations)
    - [Record Management](#record-management)
    - [Image Serving](#image-serving)
    - [Authentication](#authentication)
    - [Total Endpoints: 21](#total-endpoints-21)


Based on the use cases defined in `use_cases.md`, the following API endpoints are required to support the frontend workflow.

**Note**: UC03 (Record maintenance and administration) will use Django's built-in admin interface and does not require custom API endpoints.

---

## UC01: Add New Records - API Requirements

### Complete Workflow for UC01

1. **Search for subject** → `GET /api/subjects/?search={identifier}`
2. **Create subject if not found** → `POST /api/subjects/`
3. **Create or select encounter** → `POST /api/subjects/{subject_id}/encounters/` or select existing
4. **Check for duplicate records** → `GET /api/subjects/{subject_id}/records/?age_at_encounter={age}&record_type={type}`
5. **Get metadata options** → `GET /api/metadata/` (called once on page load)
6. **User scans via localhost** → Browser communicates with BFD9010 bridge on localhost, receives PNG or STL file
7. **Upload and create record with metadata** → `POST /api/encounters/{encounter_id}/records/` with file upload
8. **Monitor DICOM/PACS status** → Poll `GET /api/records/{id}/` for status updates

### 1. Subject Management

#### 1.1 Search for Subject
**User Action**: Operator searches for subject by identifier

**API Requirement**:
- **Endpoint**: `GET /api/subjects/?search={query}`
- **Query Parameters**: 
  - `search`: subject identifier (string)
  - `collection`: optional filter by collection name
  - `page`: pagination page number (default: 1)
  - `page_size`: items per page (default: 20)
- **Response**: Paginated list of matching subjects with fields:
  - `id`, `identifier`, `collection`, `sex`, `date_of_birth` (optional), `dental_classification`, `created_date`
  - `encounter_count`: total number of encounters
  - `record_count`: total number of records

#### 1.2 Create New Subject
**User Action**: Operator creates new subject if not found

**API Requirement**:
- **Endpoint**: `POST /api/subjects/`
- **Request Body** (required fields):
  - `identifier` (string)
  - `collection` (string)
  - `sex` (string, one of: M/F/O)
- **Optional fields**:
  - `date_of_birth` (date)
  - `dental_classification` (string)
- **Response**: Created subject object with generated `id` and all fields

#### 1.3 Get Subject Details
**User Action**: View full subject information with list of encounters

**API Requirement**:
- **Endpoint**: `GET /api/subjects/{id}/`
- **Response**: Complete subject object with:
  - All subject fields
  - `encounters`: array of basic encounter info (id, encounter_date, age_at_encounter, record_count)

---

### 2. Encounter Management

#### 2.1 List Encounters for Subject
**User Action**: View all encounters for a subject

**API Requirement**:
- **Endpoint**: `GET /api/subjects/{subject_id}/encounters/`
- **Query Parameters**:
  - `page`: pagination page number
  - `page_size`: items per page
- **Response**: Paginated list of encounters with:
  - `id`, `encounter_date`, `age_at_encounter`, `record_count`
  - `modalities`: array of unique modalities present in records (e.g., ["RG", "M3D"])
  - `record_types`: array of unique record types (e.g., ["Lateral", "PA"])

#### 2.2 Create New Encounter
**User Action**: Operator creates encounter (may be implicit when adding first record)

**API Requirement**:
- **Endpoint**: `POST /api/subjects/{subject_id}/encounters/`
- **Request Body**:
  - `encounter_date` (date, required)
  - `age_at_encounter` (float, optional - can be calculated from subject DOB if available)
- **Response**: Created encounter object with `id`

#### 2.3 Get Encounter Details
**User Action**: View specific encounter with all records

**API Requirement**:
- **Endpoint**: `GET /api/encounters/{id}/`
- **Response**: Complete encounter object with:
  - `id`, `subject_id`, `encounter_date`, `age_at_encounter`
  - `subject`: basic subject info (id, identifier, collection, sex)
  - `records`: array of record summaries (see Record Management section)

#### 2.4 Update Encounter
**User Action**: Correct encounter date or age

**API Requirement**:
- **Endpoint**: `PATCH /api/encounters/{id}/`
- **Request Body**: Partial update of encounter fields
- **Response**: Updated encounter object

#### 2.5 Delete Encounter
**User Action**: Remove encounter (admin only, cascades to records)

**API Requirement**:
- **Endpoint**: `DELETE /api/encounters/{id}/`
- **Response**: 204 No Content on success

---

### 3. Metadata and Enumerations

#### 3.1 Get All Metadata
**User Action**: Frontend needs dropdown options and field constraints

**API Requirement**:
- **Endpoint**: `GET /api/metadata/`
- **Response**: Object containing all enumeration values and constraints:
  ```json
  {
    "record_types": [
      {"value": "lateral", "label": "Lateral"},
      {"value": "pa", "label": "PA"},
      {"value": "hand", "label": "Hand"}
    ],
    "orientations": [
      {"value": "left", "label": "Left"},
      {"value": "right", "label": "Right"}
    ],
    "collections": [
      {"value": "bolton_brush", "label": "Bolton-Brush"}
    ],
    "sex_options": [
      {"value": "M", "label": "Male"},
      {"value": "F", "label": "Female"},
      {"value": "O", "label": "Other"}
    ],
    "modalities": [
      {"value": "RG", "label": "Radiography"},
      {"value": "M3D", "label": "3D Model"},
      {"value": "PX", "label": "Photo"},
      {"value": "DX", "label": "Digital X-Ray"}
    ]
  }
  ```

---

### 4. Record Management

#### 4.1 List Records for Encounter
**User Action**: View all records in an encounter or search across subject

**API Requirement**:
- **Endpoint**: `GET /api/encounters/{encounter_id}/records/`
- **Query Parameters**:
  - `record_type`: filter by type
  - `modality`: filter by modality
  - `page`, `page_size`: pagination
- **Response**: Paginated list of records with:
  - `id`, `record_type`, `orientation`, `modality`, `operator`
  - `acquisition_date`, `file_size`, `image_type`
  - `thumbnail_url`: URL to thumbnail image
  - `dicom_status`: conversion status
  - `pacs_status`: upload status

#### 4.2 Search Records (Alternative)
**User Action**: Search for records across subject to check for duplicates

**API Requirement**:
- **Endpoint**: `GET /api/subjects/{subject_id}/records/`
- **Query Parameters**:
  - `age_at_encounter`: filter by age (float)
  - `record_type`: filter by type
  - `encounter_date`: filter by date
  - `page`, `page_size`: pagination
- **Response**: Same as 4.1

---

### 5. Record Creation & Management

#### 5.1 Create Record with File Upload
**User Action**: Operator uploads scanned file (PNG or STL) and creates record with metadata

**Note**: Scanning happens directly on localhost via BFD9010 bridge. The frontend communicates with the bridge, receives the file, and then uploads it to BFD9000.

**API Requirement**:
- **Endpoint**: `POST /api/encounters/{encounter_id}/records/`
- **Content-Type**: `multipart/form-data`
- **Request Body** (form fields):
  - `file` (file upload, required): PNG or STL file from scanner
  - `record_type` (string, required): from metadata endpoint
  - `orientation` (string, required): from metadata endpoint
  - `modality` (string, required): e.g., "RG", "M3D", "PX", "DX"
  - `operator` (string, optional - defaults to authenticated user)
  - `acquisition_date` (date, optional - defaults to today)
  - `notes` (string, optional)
- **Response**: Created record object with:
  - `id` (integer)
  - `encounter_id` (integer)
  - `record_type`, `orientation`, `modality`, `operator`
  - `acquisition_date` (date)
  - `file_size` (integer, bytes)
  - `file_format` (string): "PNG" or "STL"
  - `image_type` (string): e.g., "TIFF", "JPEG2000" (after conversion)
  - `thumbnail_url` (string): path to thumbnail (served via API)
  - `image_url` (string): path to full image (served via API)
  - `dicom_status` (string): "pending", "processing", "complete", "failed"
  - `pacs_status` (string): "pending", "uploading", "complete", "failed"
  - `created_at` (datetime)

#### 5.2 Get Record Details
**User Action**: View complete record information

**API Requirement**:
- **Endpoint**: `GET /api/records/{id}/`
- **Response**: Complete record object (same fields as 5.1) plus:
  - `encounter`: nested encounter object with subject info
  - `dicom_url` (string, nullable): path to DICOM file if conversion complete
  - `error_message` (string, nullable): if processing failed

#### 5.3 Update Record Metadata
**User Action**: Operator corrects metadata after record creation

**API Requirement**:
- **Endpoint**: `PATCH /api/records/{id}/`
- **Request Body**: Partial update of editable fields:
  - `record_type`, `orientation`, `modality`
  - `acquisition_date`, `operator`, `notes`
- **Response**: Updated record object
- **Note**: Cannot change `encounter_id` after creation. File cannot be replaced after upload.

#### 5.4 Delete Record
**User Action**: Remove record (admin or if DICOM/PACS upload not complete)

**API Requirement**:
- **Endpoint**: `DELETE /api/records/{id}/`
- **Response**: 204 No Content on success
- **Validation**: May prevent deletion if record has been uploaded to PACS

---

### 6. Image Serving

**Strategy**: All images are served through authenticated API endpoints to maintain access control.

#### 6.1 Get Record Full Image
**User Action**: Display full-resolution record image

**API Requirement**:
- **Endpoint**: `GET /api/records/{id}/image/`
- **Response**: Image file with appropriate `Content-Type` (image/png, image/tiff, image/jpeg, model/stl, etc.)
- **Authentication**: Required
- **Caching**: Support `ETag` and `Last-Modified` headers

#### 6.2 Get Record Thumbnail
**User Action**: Display thumbnail in list views

**API Requirement**:
- **Endpoint**: `GET /api/records/{id}/thumbnail/`
- **Response**: JPEG thumbnail image (max 300x300px)
- **Authentication**: Required
- **Caching**: Support `ETag` and `Last-Modified` headers
- **Note**: For STL files, thumbnail should be a rendered preview image

#### 6.3 Get Record DICOM File
**User Action**: Download DICOM file for external use

**API Requirement**:
- **Endpoint**: `GET /api/records/{id}/dicom/`
- **Response**: DICOM file (.dcm) with `Content-Disposition: attachment`
- **Authentication**: Required
- **Note**: Returns 404 if DICOM conversion not yet complete

---

### 7. Background Processing Status

**Note**: Status is embedded in record object. For real-time updates, poll `GET /api/records/{id}/` or use WebSocket at `ws://server/api/records/{id}/stream/`

#### 7.1 Retry Failed Processing
**User Action**: Manually retry failed DICOM conversion or PACS upload

**API Requirement**:
- **Endpoint**: `POST /api/records/{id}/retry-processing/`
- **Request Body**:
  - `operation` (string): "dicom_conversion" or "pacs_upload"
- **Response**: Updated record object with status reset to "pending"

---

## UC02: Browse for Records - API Requirements

**Note**: Browse endpoints are covered in sections 1-4 above. This section provides the complete workflow mapping.

### Workflow Mapping

#### Step 1: Browse/Search Subjects
- **Use**: `GET /api/subjects/` (Section 1.1)
- Returns subjects with encounter_count, record_count, dental_classification

#### Step 2: View Subject Details with Encounters
- **Use**: `GET /api/subjects/{id}/` (Section 1.3)
- Returns subject with list of encounters including modalities and record counts

#### Step 3: View Encounter with Records
- **Use**: `GET /api/encounters/{id}/` (Section 2.3)
- Returns encounter with full list of records including thumbnails

#### Step 4: View Full Record
- **Use**: `GET /api/records/{id}/` (Section 5.2)
- **Use**: `GET /api/records/{id}/image/` (Section 6.1) to display image
- Returns complete record metadata and serves full-resolution image

---

## UC04: Export and Sharing - API Requirements

**Status**: Not yet implemented. 

Future API endpoints will include:
- Bulk export of records in DICOM format
- Sharing records with external users/systems
- Generate export packages with metadata
- Query interface for DICOM nodes

Potential endpoints:
- `POST /api/exports/` - Create export job
- `GET /api/exports/{id}/` - Check export status
- `GET /api/exports/{id}/download/` - Download completed export package

---

## Design Notes and Conventions

### RESTful Resource Hierarchy
The API follows a clear resource hierarchy:
```
/api/subjects/{id}/
  ├── /encounters/
  │     └── /{id}/
  │           └── /records/
  │                 └── /{id}/
  └── /records/ (search across all encounters)
```

### ID Types
- All resource IDs are **integers** except where noted
- Consistent ID types simplify frontend type systems

### Pagination
- All list endpoints support pagination
- Query parameters: `page` (1-indexed), `page_size` (default: 20, max: 100)
- Response includes: `count`, `next`, `previous`, `results`

### Timestamps
- All timestamps in ISO 8601 format with timezone: `2025-11-29T14:30:00Z`
- Date-only fields in ISO 8601 date format: `2025-11-29`

### Image URLs
- `image_url`, `thumbnail_url`, `dicom_url` fields contain **relative paths**, not full URLs
- Example: `"/api/records/123/image/"` not `"http://server/api/records/123/image/"`
- Frontend constructs full URL using base API URL
- This approach maintains portability across environments

### Nested vs. Direct Access
- Resources can be accessed both through parent hierarchy and directly:
  - Nested: `POST /api/encounters/{id}/records/` (creates record in specific encounter)
  - Direct: `GET /api/records/{id}/` (access any record directly)
- This pattern balances REST semantics with practical access needs

### Status Enumerations
Standardized status values:

**Scan Status**: `initiated`, `scanning`, `complete`, `failed`

**DICOM Status**: `pending`, `processing`, `complete`, `failed`

**PACS Status**: `pending`, `uploading`, `complete`, `failed`

### Real-time Updates
For long-running operations (scans, DICOM conversion), clients can:
1. **Poll** the resource endpoint (simple, recommended for MVP)
2. **WebSocket** (future): Connect to `ws://server/api/{resource}/{id}/stream/`

Polling recommended interval: 1-2 seconds during active operations

---

## Error Handling and HTTP Status Codes

### Standard Status Codes

**Success**:
- `200 OK` - Successful GET, PATCH
- `201 Created` - Successful POST, includes `Location` header
- `204 No Content` - Successful DELETE

**Client Errors**:
- `400 Bad Request` - Invalid request body or parameters
- `401 Unauthorized` - Not authenticated (redirect to CAS login)
- `403 Forbidden` - Authenticated but not authorized for this resource
- `404 Not Found` - Resource doesn't exist
- `409 Conflict` - Resource conflict (e.g., duplicate record)
- `422 Unprocessable Entity` - Validation error

**Server Errors**:
- `500 Internal Server Error` - Unexpected server error
- `503 Service Unavailable` - External service (e.g., PACS) unavailable

### Error Response Format

All error responses follow this structure:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid record metadata",
    "details": {
      "record_type": ["This field is required"],
      "orientation": ["Must be one of: left, right"]
    }
  }
}
```

### Common Error Codes

- `AUTHENTICATION_REQUIRED` - 401
- `PERMISSION_DENIED` - 403
- `NOT_FOUND` - 404
- `VALIDATION_ERROR` - 422
- `DUPLICATE_RECORD` - 409
- `FILE_TOO_LARGE` - 413
- `UNSUPPORTED_FILE_TYPE` - 415
- `PROCESSING_FAILED` - 500

### Validation Rules

**Subject Creation**:
- `identifier` must be unique within collection
- `sex` must be one of: M, F, O
- `collection` must exist in metadata

**Encounter Creation**:
- `encounter_date` cannot be in the future
- If `age_at_encounter` not provided and subject has `date_of_birth`, calculate automatically
- Cannot create encounter with date before subject's `date_of_birth`

**Record Creation**:
- `file` must be provided and must be PNG or STL format
- Maximum file size: 100MB (configurable)
- `record_type`, `orientation`, `modality` must exist in metadata
- `acquisition_date` cannot be in the future
- File content must match file extension (validated via magic bytes)

---

---

## Authentication & Authorization

### 9. Authentication

#### 9.1 Get Current User
**User Action**: Frontend needs to know authenticated user info

**API Requirement**:
- **Endpoint**: `GET /api/auth/user/`
- **Authentication**: Django session-based auth with CAS SSO integration (case.edu)
- **Response**:
  - `id` (integer)
  - `username` (string)
  - `email` (string)
  - `full_name` (string)
  - `is_admin` (boolean)
  - `permissions` (array): e.g., ["can_delete_records", "can_edit_subjects"]

### Authorization Notes
- All endpoints require authentication via CAS SSO
- Image serving endpoints verify user has access to the subject's collection
- Admin-only operations: DELETE encounters, DELETE records (after PACS upload)
- Record creation and editing limited to authenticated operators

---

## Summary of Required Endpoints

### Subject Management
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/subjects/` | Search/browse subjects with pagination |
| POST | `/api/subjects/` | Create new subject |
| GET | `/api/subjects/{id}/` | Get subject details with encounter list |

### Encounter Management
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/subjects/{subject_id}/encounters/` | List encounters for subject |
| POST | `/api/subjects/{subject_id}/encounters/` | Create new encounter |
| GET | `/api/encounters/{id}/` | Get encounter with records |
| PATCH | `/api/encounters/{id}/` | Update encounter metadata |
| DELETE | `/api/encounters/{id}/` | Delete encounter (admin) |

### Metadata & Enumerations
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/metadata/` | Get all dropdown options and constraints |

### Record Management
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/encounters/{encounter_id}/records/` | List records in encounter |
| GET | `/api/subjects/{subject_id}/records/` | Search records across subject |
| POST | `/api/encounters/{encounter_id}/records/` | Create record from scan |
| GET | `/api/records/{id}/` | Get complete record details |
| PATCH | `/api/records/{id}/` | Update record metadata |
| DELETE | `/api/records/{id}/` | Delete record |
| POST | `/api/records/{id}/retry-processing/` | Retry failed DICOM/PACS |

### Image Serving
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/records/{id}/image/` | Serve full-resolution image |
| GET | `/api/records/{id}/thumbnail/` | Serve thumbnail image |
| GET | `/api/records/{id}/dicom/` | Download DICOM file |

### Authentication
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/auth/user/` | Get current authenticated user info |

### Total Endpoints: 21
All endpoints support proper REST semantics with appropriate HTTP verbs and status codes.

**Note**: Scanner integration is handled entirely on localhost via BFD9010 bridge. The frontend communicates directly with the bridge, and BFD9000 only receives the resulting PNG or STL file via the record creation endpoint.
