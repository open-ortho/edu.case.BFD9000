## Plan: Implementazione OpenAPI (drf-spectacular)

Questo piano descrive i passaggi per integrare la documentazione OpenAPI 3.0 nel progetto BFD9000 utilizzando `drf-spectacular`, lo standard attuale per Django REST Framework.

### Phase 1: Installazione e Configurazione

1.  **Aggiornamento Dipendenze**
    *   Modificare `bfd9000_web/requirements.txt` aggiungendo:
        ```text
        drf-spectacular
        ```

2.  **Configurazione Django (`settings.py`)**
    *   Aggiungere `'drf_spectacular'` a `INSTALLED_APPS`.
    *   Configurare DRF per usare lo schema generator di Spectacular:
        ```python
        REST_FRAMEWORK = {
            # ... existing settings ...
            'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
        }
        ```
    *   Aggiungere la configurazione specifica `SPECTACULAR_SETTINGS`:
        ```python
        SPECTACULAR_SETTINGS = {
            'TITLE': 'BFD9000 API',
            'DESCRIPTION': 'API for BFD9000 Medical Imaging System',
            'VERSION': '1.0.0',
            'SERVE_INCLUDE_SCHEMA': False,
            'COMPONENT_SPLIT_REQUEST': True
        }
        ```

### Phase 2: Routing e Esposizione

3.  **Aggiornamento URL (`urls.py`)**
    *   Importare le view di Spectacular.
    *   Aggiungere le rotte per lo schema JSON e le interfacce UI:
        ```python
        from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

        urlpatterns = [
            # ... existing urls ...
            path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
            path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
            path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
        ]
        ```

### Phase 3: Annotazioni Specifiche (`views.py`)

4.  **Gestione Risposte Binarie**
    *   Le action `image` e `thumbnail` restituiscono file binari, non JSON.
    *   Utilizzare `@extend_schema` con `OpenApiTypes.BINARY` per documentare correttamente il content-type.
    *   Modificare `bfd9000_web/archive/views.py`:
        ```python
        from drf_spectacular.utils import extend_schema
        from drf_spectacular.types import OpenApiTypes
        
        # Sulle action 'image' e 'thumbnail'
        @extend_schema(
            responses={
                (200, 'application/octet-stream'): OpenApiTypes.BINARY
            }
        )
        def image(self, request, pk=None): ...
        ```

### Phase 4: Verifica

4.  **Test Manuale**
    *   Avviare il server.
    *   Verificare `/api/schema/` (download JSON/YAML).
    *   Verificare `/api/schema/swagger-ui/` (interfaccia interattiva).
    *   Controllare che i serializer complessi (es. `RecordUploadSerializer` vs `RecordSerializer`) siano documentati correttamente.
