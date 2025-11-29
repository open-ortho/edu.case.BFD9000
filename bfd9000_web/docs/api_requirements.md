# API Requirements for Frontend

Based on the use cases defined in `use_cases.md`, the following API endpoints are required to support the frontend workflow.

**Note**: UC03 (Record maintenance and administration) will use Django's built-in admin interface and does not require custom API endpoints.

---

## UC01: Add New Records - API Requirements

### 1. Subject Management

#### 1.1 Search for Subject
**User Action**: Operator searches for subject by identifier

**API Requirement**:
- **Endpoint**: `GET /api/subjects/?search={query}`
- **Query Parameters**: 
  - `search`: subject identifier (string)
  - `collection`: optional filter by collection name
- **Response**: List of matching subjects with fields:
  - `id`, `identifier`, `collection`, `sex`, `date_of_birth` (optional), `created_date`

#### 1.2 Create New Subject
**User Action**: Operator creates new subject if not found

**API Requirement**:
- **Endpoint**: `POST /api/subjects/`
- **Request Body** (required fields):
  - `identifier` (string)
  - `collection` (string/enum)
  - `sex` (string/enum: M/F/O)
- **Response**: Created subject object with generated `id`

#### 1.3 Get Subject Details
**User Action**: View full subject information

**API Requirement**:
- **Endpoint**: `GET /api/subjects/{id}/`
- **Response**: Complete subject object including related records

---

### 2. Record Management

#### 2.1 Search for Existing Records
**User Action**: Operator searches for records by age and type to avoid duplicates

**API Requirement**:
- **Endpoint**: `GET /api/records/?subject_id={id}&age_at_encounter={age}&record_type={type}`
- **Query Parameters**:
  - `subject_id` (integer, required)
  - `age_at_encounter` (float, optional)
  - `record_type` (string/enum, optional): "Lateral", "PA", "Hand", etc.
- **Response**: List of matching records with fields:
  - `id`, `record_type`, `orientation`, `age_at_encounter`, `acquisition_date`, `encounter_date`, `operator`, `dicom_status`

#### 2.2 Get Record Types (Enumeration)
**User Action**: Frontend needs to populate record type dropdown

**API Requirement**:
- **Endpoint**: `GET /api/record-types/`
- **Response**: Array of available record types with display names

#### 2.3 Get Orientations (Enumeration)
**User Action**: Frontend needs to populate orientation dropdown

**API Requirement**:
- **Endpoint**: `GET /api/orientations/`
- **Response**: Array of available orientations

#### 2.4 Get Collections (Enumeration)
**User Action**: Frontend needs to populate collection dropdown

**API Requirement**:
- **Endpoint**: `GET /api/collections/`
- **Response**: Array of available collections

---

### 3. Scanner Integration

#### 3.1 Detect Available Scanners
**User Action**: System detects connected scanners via BFD9010 bridge

**API Requirement**:
- **Endpoint**: `GET /api/scanners/`
- **Response**: List of detected scanners with:
  - `id`, `name`, `status` (online/offline), `type`, `bridge_connection_id`, `instructions` (usage instructions text)

#### 3.2 Initiate Scan
**User Action**: Operator clicks scan button

**API Requirement**:
- **Endpoint**: `POST /api/scans/`
- **Request Body**:
  - `scanner_id` (integer)
  - `subject_id` (integer)
- **Response**: 
  - `scan_id` (string/UUID)
  - `status` ("initiated", "scanning", "complete", "failed")
  - WebSocket/SSE connection URL for progress updates

#### 3.3 Get Scan Status/Progress
**User Action**: Frontend polls or receives updates on scan progress

**API Requirement**:
- **Endpoint**: `GET /api/scans/{scan_id}/status/`
- **Response**:
  - `status` (enum)
  - `progress_percentage` (0-100)
  - `preview_url` (when available)
  - `error_message` (if failed)

#### 3.4 Get Scanned Image Preview
**User Action**: Display scanned image for operator verification

**API Requirement**:
- **Endpoint**: `GET /api/scans/{scan_id}/preview/`
- **Response**: Image file (JPEG/PNG) or URL to image resource

---

### 4. Record Creation & Metadata Validation

#### 4.1 Create Record with Scanned Image
**User Action**: Operator confirms metadata and creates record

**API Requirement**:
- **Endpoint**: `POST /api/records/`
- **Request Body**:
  - `subject_id` (integer, required)
  - `scan_id` (string, required)
  - `record_type` (string/enum, required)
  - `orientation` (string/enum, required)
  - `operator_name` (string, required - may be pre-filled from auth)
  - `acquisition_date` (date, required - may be pre-filled as today)
  - `encounter_date` (date, required)
  - `age_at_encounter` (float, calculated or manual)
  - `collection` (string/enum, required)
- **Response**: Created record object with:
  - `id`
  - `dicom_conversion_status` ("pending", "processing", "complete", "failed")
  - `pacs_upload_status` ("pending", "uploading", "complete", "failed")

#### 4.2 Update Record Metadata
**User Action**: Operator corrects metadata before final confirmation

**API Requirement**:
- **Endpoint**: `PATCH /api/records/{id}/`
- **Request Body**: Partial update of any editable fields
- **Response**: Updated record object

---

### 5. Background Processing Status

#### 5.1 Check DICOM Conversion Status
**User Action**: System monitors DICOM conversion progress

**API Requirement**:
- **Endpoint**: `GET /api/records/{id}/dicom-status/`
- **Response**:
  - `dicom_conversion_status` (enum)
  - `pacs_upload_status` (enum)
  - `dicom_file_url` (when available)
  - `error_message` (if failed)

---

## UC02: Browse for Records - API Requirements

### 6. Browse and Search Interface

#### 6.1 Browse/Search Subjects
**User Action**: Operator searches for or browses subjects (UC02 Step 1)

**API Requirement**:
- **Endpoint**: `GET /api/subjects/`
- **Query Parameters**:
  - `search`: optional text search across subject identifiers
  - `collection`: optional filter by collection
  - `sex`: optional filter by sex
  - `page`: pagination parameter
  - `page_size`: items per page
- **Response**: Paginated list of subjects with:
  - `id`, `identifier`, `sex`, `collection`
  - `encounter_count`: number of encounters for this subject
  - `record_count`: total number of records across all encounters
  - `dental_classification`: dental classification (if available)
  - Clinical information fields as available

#### 6.2 Get Subject Detail with Encounters
**User Action**: Operator clicks on a subject to view details (UC02 Step 2)

**API Requirement**:
- **Endpoint**: `GET /api/subjects/{id}/`
- **Response**: Complete subject object with:
  - All subject fields
  - `encounters`: array of encounter objects with:
    - `id`, `encounter_date`, `age_at_encounter`
    - `record_count`: number of records in this encounter
    - `modalities`: array of record modalities present (RG, M3D, PX, DX, etc.)
    - `record_types_summary`: breakdown by type

#### 6.3 Get Encounter Details with Records
**User Action**: Operator selects an encounter to view records (UC02 Step 3)

**API Requirement**:
- **Endpoint**: `GET /api/encounters/{id}/`
- **Response**: Encounter object with:
  - `id`, `subject_id`, `encounter_date`, `age_at_encounter`
  - `records`: array of record objects with:
    - `id`, `record_type`, `orientation`, `modality`
    - `thumbnail_url`: URL to thumbnail image
    - `file_size`: size in bytes
    - `image_type`: image format/type
    - `acquisition_date`, `operator`
    - Other relevant metadata

#### 6.4 View Record Detail
**User Action**: Operator views a specific record (UC02 Step 4)

**API Requirement**:
- **Endpoint**: `GET /api/records/{id}/`
- **Response**: Complete record object with:
  - All metadata fields
  - `image_url`: URL to full-resolution image
  - `thumbnail_url`: URL to thumbnail
  - `dicom_url`: URL to DICOM file (if available)
  - `file_size`, `dimensions`, `bit_depth`
  - Related subject and encounter information

#### 6.5 Get Record Image
**User Action**: Display full record image

**API Requirement**:
- **Endpoint**: `GET /api/records/{id}/image/`
- **Response**: Image file (JPEG/PNG/TIFF) with appropriate content-type headers

#### 6.6 Get Record Thumbnail
**User Action**: Display record thumbnail in list views

**API Requirement**:
- **Endpoint**: `GET /api/records/{id}/thumbnail/`
- **Response**: Thumbnail image file (JPEG/PNG) with appropriate content-type headers

---

## UC04: Export and Sharing - API Requirements

**Status**: Not yet implemented. Future API endpoints will include:
- Export records in DICOM format
- Share records with other users/systems
- Generate export packages

---

## Authentication & Authorization

### Auth Requirements
- **Endpoint**: `GET /api/auth/user/` or use Django session-based auth
- **SSO Integration**: CAS authentication at case.edu
- **Response**: Current user info including:
  - `username`, `email`, `full_name`, `role`, `permissions`

---

## Summary of Required Endpoints

### UC01: Add New Records
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/subjects/` | Search/browse subjects |
| POST | `/api/subjects/` | Create subject |
| GET | `/api/subjects/{id}/` | Get subject details with encounters |
| GET | `/api/records/` | Search/filter records |
| POST | `/api/records/` | Create record |
| PATCH | `/api/records/{id}/` | Update record metadata |
| GET | `/api/records/{id}/dicom-status/` | Check processing status |
| GET | `/api/record-types/` | Get record type options |
| GET | `/api/orientations/` | Get orientation options |
| GET | `/api/collections/` | Get collection options |
| GET | `/api/scanners/` | List available scanners |
| POST | `/api/scans/` | Initiate scan |
| GET | `/api/scans/{scan_id}/status/` | Get scan progress |
| GET | `/api/scans/{scan_id}/preview/` | Get scanned image |

### UC02: Browse for Records
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/subjects/` | Browse/search subjects with stats |
| GET | `/api/subjects/{id}/` | Get subject with encounters list |
| GET | `/api/encounters/{id}/` | Get encounter with records list |
| GET | `/api/records/{id}/` | Get complete record details |
| GET | `/api/records/{id}/image/` | Get full-resolution image |
| GET | `/api/records/{id}/thumbnail/` | Get thumbnail image |

### Authentication (All Use Cases)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/auth/user/` | Get current user info |

### Total Unique Endpoints
20 endpoints across UC01 and UC02 (some endpoints serve both use cases)
