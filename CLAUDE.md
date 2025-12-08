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
		- Docs for the AI endpoint are stored at https://wingate.case.edu/bfd9020/docs#/

REFERENCE THE API IN bfd9000_web/docs/api_requirements.md