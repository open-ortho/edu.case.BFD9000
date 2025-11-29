# Use Cases

The BFD9000 shall be able to accommodate the following use cases.


## UC01: Add new records

### Actors

- Operator: a human individual who needs to digitize a physical record into a digital record.
- System: BFD9000 web application
- BFD9010: the bridge used to connect the scanner with the system
- Scanner: The acquisition modality used to convert the physical record into the digital record.

### Prerequisites

- Operator has turned on scanner
- Operator has logged into a workstation connected to a Scanner and then into the system using CAS SSO case.edu credentials.
- Operator has launched BFD9010 bridge on the workstation with the scanner connected.
- Operator has located and identified the physical record to be digitized and archived.


### Steps

1. Operator searches for the subject related to the physical record. If the subject doesn't exist, the operator shall create a new subject with a minimum of subject identifier, collection name, sex.
2. Operator searches for the record by age at encounter (to make sure it hasn't been digitized already) and record type (Lateral, Hand, etc)
3. If record doesn't exist, operator proceeds to Add a new Record.
4. The system shows a new view, which shows the user the scanner that has been detected and instructs the user how to use it, i.e. how to place the physical record into the scanner.
5. Operator then clicks the scan button, and waits for the scan to be complete.
6. The operator is then presented with a view of the scanned record, and is able to verify all the metadata is appropriately selected (record type, orientation, operator name, date of acquisition, encounter date, collection)
7. The operator makes any correction to the data, using the appropriate fields and drop down menus: the user should not type anything, if possible, but make selections. 
8. Once the user confirms, the digitized record is added to the database. The system proceeds to convert it to DICOM and uploads it to a PACS or other DICOM Node.

## UC02: Browse for records

Operators need to be able to search for and view specific records

### Actors

- Operator: a human individual who needs to digitize a physical record into a digital record.
- System: BFD9000 web application

### Prerequisites

- Operator has logged into a workstation and then into the system using CAS SSO case.edu credentials.

### Steps

1. Operator searches for subjects or browses for subjects. The view shows the operator a list of subjects with number of encounters per subject, number of total records, sex of subject, dental classification (and/or other clinical information) and collection.
2. Operator can click on a subject. Doing so will pull up subject detail view with more clinical details and a list of all encounters for the patient. The encounter list will show: age of patient at encounter, number of records acquired during encounter, type of records in encounter by modality (e.g. RG, M3D, PX, DX, etc)
3. Once an Encounter is selected, the operator will then be able to see each record for the encounter. This view will show thumbnails for each record and record details like file size, image type, orientation, and any other relevant information.
4. Operator can then view the record.

## UC03: Record maintenance and administration

### Actors

- Operator: a human individual with administration privileges.
- System: BFD9000 web application

### Prerequisites

- Operator has logged into a workstation and then into the system using CAS SSO case.edu credentials.

### Steps

1. Operator opens the backoffice/admin interface
2. Operator selects record or subject or encounter and deletes or modifies its records.


## UC04: Export and sharing

Not Implemented yet.

The operator should be able to export and share records with other members in the DICOM format.

### Prerequisites

- Operator has logged into a workstation and then into the system using CAS SSO case.edu credentials.
