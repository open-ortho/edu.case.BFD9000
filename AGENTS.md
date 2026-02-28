Currently, the primary development focus is on the Django server in `bfd9000_web`. If dependencies are missing, this project does use a nix flake at its root, so try running `nix develop` to set up the development environment properly.

The github action uses the nix flake as well. Any time you add another dependency or python package, make sure to update the flake.nix file.

## Reference

- **Main API spec**: [api_requirements.md](./bfd9000_web/docs/api_requirements.md)

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
