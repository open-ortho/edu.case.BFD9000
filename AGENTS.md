Currently, the primary development focus is on the Django server in `bfd9000_web`. If dependencies are missing, this project does use a nix flake at its root, so try running `nix develop` to set up the development environment properly.

The github action uses the nix flake as well. Any time you add another dependency or python package, make sure to update the flake.nix file.

## Reference

- **Main API spec**: [api_requirements.md](./bfd9000_web/docs/api_requirements.md)
- **Data model spec**: [data_model.md](./bfd9000_web/docs/data_model.md)

## Data Model

- Follow the archive hierarchy documented in `bfd9000_web/docs/data_model.md`:
  - `Encounter -> ImagingStudy -> Series -> Record`
- Keep field ownership strict:
  - `record_type` belongs to `Series`
  - upload/acquisition fields belong to `Record`
- Critical warning:
  - `record_type` (SNOMED clinical study type) is **not** the same as `image_type` (legacy identifier code like `L`, `SM`)
  - never substitute one for the other in API, filtering, or UI logic

## Typing

- All code should be explicitly typed.
- Prefer direct variable type annotations (for example `typed_instance: Record = instance`) over `cast()` whenever possible.
- Use `cast()` only when direct annotations and normal control-flow typing cannot express the type clearly.
- Avoid "type-like" protocol/shim objects or other typing-only abstractions that add complexity without improving readability.
- The goal of typing is clearer code and fewer errors, not extra boilerplate.

Whenever a large change is made, documenting it in `./bfd9000_web/docs` is good practice.

- Include the collection in the subjects view
- Subject:
 	- Name / DoB etc. are unused for now: DO NOT EXPOSE
- Age field needs to be able to handle specific day
 	- Just show age in years-month maybe year-month-day? ^^(is month optional?)^^ for now yes
- APP FLOW:
 	- Subject view -> Encounter view (filter for subject)
  		- Add a new subject: subject ID, sex, dental class, etc.
 	- Encounters view -> Records view (filter for encounter)
  		- Add a new encounter `age_at_encounter`
 	- Records view -> Add new record / SCAN
  		- Scanning: image comes back, verify details and enter age, click magic AI button -> AI Endpoint (9020)
  		- AI Endpoint (9020) -> data from AI, fills out the fields in the form, human can verify, click submit -> POST new record
  		- Docs for the AI endpoint are stored at <https://wingate.case.edu/bfd9020/docs#/>

REFERENCE THE API IN bfd9000_web/docs/api_requirements.md
