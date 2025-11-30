## Plan: Implementazione API DRF Completa (Definitiva)

Questo piano copre l'implementazione completa delle specifiche API, inclusa gestione file, errori e routing complesso.

### Phase 1: Core Configuration & Dependencies
1.  **Environment & Settings**
    *   Aggiornare `requirements.txt`: aggiungere `drf-nested-routers`, `Pillow` (per immagini), `python-magic` (per validazione file).
    *   Configurare `settings.py`:
        *   `PAGE_SIZE = 20`.
        *   `MEDIA_ROOT` e `MEDIA_URL` per lo storage locale dei file.
        *   Configurare `EXCEPTION_HANDLER` custom in DRF.
2.  **Error Handling**
    *   Creare `bfd9000_web/BFD9000/exceptions.py`.
    *   Implementare handler che intercetta le eccezioni DRF e le riformatta nel JSON standard: `{"error": {"code": "...", "details": ...}}`.

### Phase 2: Data Models & Valuesets
3.  **Model Updates (Storage)**
    *   Modificare `ImagingStudy` in `archive/models.py`:
        *   Aggiungere `source_file = models.FileField(upload_to='uploads/%Y/%m/%d/', null=True, blank=True)` per il file grezzo (PNG/STL).
        *   Mantenere il campo `endpoint` (URLField) per il link esterno al PACS.
        *   Aggiungere property `image_url` che restituisce `source_file.url` se presente, altrimenti `endpoint`.
4.  **Valuesets Endpoint**
    *   Implementare `ValuesetView` in `archive/views.py` (`/api/valuesets/?type=...`).
    *   Logica di mapping:
        *   `sex_options` -> `Subject.GENDER_CHOICES`
        *   `record_types`, `modalities`, `orientations` -> Query su `Coding` model filtrati per system/type.
5.  **Initial Data (Fixtures)**
    *   Creare script `archive/management/commands/init_codings.py` per popolare la tabella `Coding` con i valori obbligatori (RG, M3D, Lateral, PA, ecc.) definiti nei requisiti.

### Phase 3: Subject & Encounter Logic
6.  **Serializers Refactoring**
    *   `SubjectSerializer`: Aggiungere campi `read_only`: `encounter_count`, `record_count`.
    *   `EncounterSerializer`: Aggiungere `age_at_encounter` (calcolato da `subject.birth_date` e `encounter_date`).
7.  **ViewSets & Filters**
    *   `SubjectViewSet`: Aggiungere `filterset_class` per ricerca su `identifier` e `collection__name`.
    *   `EncounterViewSet`: Override `perform_create` per calcolare `age_at_encounter` se mancante.

### Phase 4: Record Management & Uploads
8.  **Record Upload Logic**
    *   Creare `RecordUploadSerializer` (separato da quello di lettura) che accetta `multipart/form-data`.
    *   Validazione: Implementare `validate_file` per controllare estensione e magic bytes (se possibile).
    *   Salvataggio Atomico: Override `create()` per:
        1.  Salvare il file fisico in un nuovo `ImagingStudy`.
        2.  Creare il `Record` collegato all'`ImagingStudy`.
        3.  Collegare all'`Encounter`.
9.  **Routing Gerarchico**
    *   Configurare `archive/urls.py` con `drf-nested-routers`:
        *   `/api/subjects/{id}/encounters/`
        *   `/api/subjects/{id}/records/`
        *   `/api/encounters/{id}/records/`
    *   Mantenere anche le rotte flat `/api/records/` e `/api/encounters/`.

### Phase 5: Image Serving & Downloads
10. **Custom File Views**
    *   Implementare azioni custom in `RecordViewSet` (o view dedicate):
        *   `@action(detail=True) image`: Restituisce `FileResponse(record.imaging_study.source_file)`.
        *   `@action(detail=True) thumbnail`:
            *   Se immagine 2D: Genera thumb con Pillow on-the-fly (e la cachea).
            *   Se STL: Restituisce icona placeholder statica (per ora).
        *   `@action(detail=True) dicom`: Restituisce 404 (Not Implemented) o file se presente campo `dicom_file`.

### Phase 6: Verification
11. **Test Suite**
    *   Creare test `tests/test_api_flows.py`:
        *   Flow completo: Crea Soggetto -> Crea Incontro -> Upload File -> Verifica esistenza Record e File.
        *   Verifica formato errori custom.
