# BFD9000 Web Scratchpad (internal)

Personal notes to keep the Django UI effort scoped and sequenced. Focused solely on `bfd9000_web` (project) and the `archive` app.

## Mission Snapshot
- Deliver a staff-only Django 5.2.8 UI that lets operators authenticate, browse Subjects, inspect linked Records, and begin capturing new physical records as we build out digital ingestion.
- Constraints for v1 (per spec): vanilla Django stack (generic CBVs, template inheritance, no JS frameworks, no extra third-party apps), SQLite dev DB; models/admin are seeded already but can (and likely will) evolve as UX needs surface—expect to add migrations when reality demands it.

## Tech Baseline (today)
- Project structure: `bfd9000_web/` with project package `BFD9000` and single app `archive`.
- Settings: default Django 5.2 skeleton; SQLite DB committed (`db.sqlite3`). No `LOGIN_URL`/`LOGIN_REDIRECT_URL` overrides yet.
- URLs: root `bfd9000_web/BFD9000/urls.py` only exposes `/admin/`. No include for `archive`.
- App status:
  - Models: rich FHIR-ish schema (Subjects, Encounters, ImagingStudies, Records, Codings, etc.) + admin configs already wired; schema is adjustable (not sacred) so long as migrations/documentation keep pace.
  - Views/templates/tests: completely empty (`archive/views.py` and `tests.py` are placeholders).
  - Forms folder nonexistent.
- Auth: default Django auth enabled but no login/logout views exposed.

## Phase-1 Deliverables (spec reminder)
1. **Authentication shell**
  - `/login/` → `LoginView` using `registration/login.html`.
  - `/logout/` → `LogoutView`, redirecting back to `/login/`.
  - Enforce staff-only access via `LoginRequiredMixin + UserPassesTestMixin` or decorators; set `LOGIN_URL = "login"`, `LOGIN_REDIRECT_URL = "archive:home"`.
2. **URL map (`archive/urls.py`) + root include**
  - Routes: `/`, `/subjects/`, `/subjects/<pk>/`, `/subjects/<pk>/records/add/`, plus login/logout.
  - Namespaces: `archive:` for internal views, bare names for auth.
3. **Layout & templates**
  - Base template `archive/base.html` with header (project name, user info, logout) and sidebar (Subjects active; Reports placeholder).
  - `archive/home.html` (subjects list), `archive/subject_detail.html`, `archive/record_form.html`, `archive/reports_todo.html` (or similar), and `registration/login.html`.
  - Minimal CSS inline or via static file; goal is clarity, not polish.
4. **Views**
  - `SubjectListView` (CBV ListView) w/ search (`q` GET param) and optional pagination (target 25/page). Table columns: identifier, collection, demographics. Rows link to detail view.
  - `SubjectDetailView` (DetailView) showing subject summary, records table, and “Add record” CTA.
  - `RecordCreateView` (CreateView) bound to `RecordForm`; restrict `encounter` queryset to encounters for the target subject; handle file upload placeholder + stub sections for scanning/import.
  - Reports placeholder: simplest `TemplateView` telling “Reports – TODO”. Sidebar should link/indicate planned area.
5. **Forms**
  - `RecordForm` (ModelForm) capturing key metadata fields (encounter, record_type, physical location, identifiers). Include a non-model `upload` FileField for now; in `form_valid` stash file path/handle later with a TODO comment.
6. **Access control & UX details**
  - All `archive` views require authenticated staff. Non-staff redirect (403 or login).
  - “Cancel” actions on forms return to subject detail. Use `SuccessMessageMixin` or inline messages later.

## Current Gaps vs Spec
- No `archive/urls.py`, templates, or forms exist yet.
- `archive/views.py` empty ⇒ need to author CBVs + mixins.
- Root URLconf lacks login/logout + archive includes.
- No static assets pipeline; will rely on inline styles until spec revises.
- Tests nonexistent; at minimum need smoke tests for each view once templates land.

## Implementation Plan (my sequencing)
1. **Settings + URLs**
  - Add `LOGIN_URL`, `LOGIN_REDIRECT_URL` to `BFD9000/settings.py`.
  - Create `archive/urls.py` per spec; update project `urls.py` to include it and auth routes.
2. **Auth Templates**
  - Build `registration/login.html`; ensure context integrates Django’s auth form + `next` handling.
3. **Base Layout + Sidebar**
  - Create `archive/base.html` with header + sidebar; add block placeholders for `sidebar_subjects_active` etc. to highlight current tab.
  - Provide placeholder/disabled “Reports” link (optionally pointing to TODO view).
4. **Subjects List View**
  - Implement `SubjectListView` with `StaffAccessMixin` (custom mixin verifying `is_staff`). Support `q` filtering on `humanname_family`, `humanname_given`, and first identifier.
  - Template `archive/home.html` w/ search form + table.
5. **Subject Detail View**
  - Implement `SubjectDetailView`; gather records via `Record.objects.filter(encounter__subject=self.object).select_related(...)` for efficiency.
  - Template includes subject summary card, records table/action button, message when no records.
6. **Record Creation Flow**
  - Add `forms.py` with `RecordForm` + `upload` FileField + radio for ingestion mode (HTML only for now).
  - Create `RecordCreateView` overriding `dispatch` to fetch subject, `get_form_kwargs` to inject subject, and `form_valid` to tie `subject`/encounter.
  - Template `archive/record_form.html` with subject summary, standard form layout, digital ingestion section with TODO placeholders for BFD9001/external import.
  - Ensure file upload handled (store in temp + TODO comment).
7. **Reports Placeholder**
  - Add `ReportsTodoView (TemplateView)` and `archive/reports_todo.html` message.
8. **Access mixins + tests**
  - Create reusable `StaffOnlyMixin` for CBVs.
  - Add smoke tests for each view verifying login redirect and staff access.

## TODO Board
| Priority | Task |
| --- | --- |
| P0 | Define `archive/urls.py` + include in project root. |
| P0 | Implement staff-only access mixin + wire into all CBVs. |
| P0 | Deliver templates (`base`, `home`, `subject_detail`, `record_form`, `reports_todo`, `registration/login`). |
| P0 | Build `SubjectListView` with search + optional pagination. |
| P0 | Build `SubjectDetailView` with records table + add-record CTA. |
| P0 | Ship `RecordForm` + `RecordCreateView` with encounter scoping + file upload placeholder. |
| P1 | Add `ReportsTodoView` + sidebar wiring. |
| P1 | Add smoke tests covering login requirement + basic render for each view. |
| P2 | Polish styling (extract CSS, responsive tweaks). |
| P2 | Add flash messaging + breadcrumbs beyond basics. |

## Risks & Notes
- **Data sparsity**: Without fixtures, templates may render empty states; need factory or admin-created data for testing.
- **File handling**: Upload placeholder can clutter repo if we start writing to disk—decide interim temp dir + cleanup strategy soon.
- **Authorization leaks**: Ensure `LoginView` inherits `RedirectAuthenticatedUserMixin` to avoid loops; double-check `is_staff` gating everywhere (mixins + tests).
- **DB migrations vs. fixtures**: Models already heavy; future UI iterations will need curated fixture to keep dev DB out of git.
- **Reports nav**: Placeholder should not 404; simplest TemplateView keeps layout consistent while spec for reporting matures.

## Quick Commands
```bash
# Spin up dev server for manual view checks
python bfd9000_web/manage.py runserver 0.0.0.0:8000

# Run Django checks before committing UI work
python bfd9000_web/manage.py check
```

## Parking Lot
- Evaluate switching to `django-crispy-forms` later if design requirements grow (out of scope for current constraint).
- Future milestone: integrate DRF API + HTMX or React once internal operators validate UX; until then, keep templates lean.
- Need plan for background ingestion hooks (Celery/Channels) once BFD9001 scanner API comes online.
