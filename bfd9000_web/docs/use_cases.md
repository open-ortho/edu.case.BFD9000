# Use Cases

The BFD9000 shall be able to accomodate the following use cases.

## Add new records

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
