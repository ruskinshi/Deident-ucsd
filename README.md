
########################################################################################
UCSD DICOM de-identifier. 
This software is based on New Zealand/UCLA CAP de-identification
routines. It will read idendtified patient dicom files, copy the originals, and create a de-identififed DICOM
file set. It logs patient info in an excel file, which can be copied to other user files.
########################################################################################

De-ident 3.2.1
Last Update: January 2022
Version 3.2.1 has been updated to only write a CMR subfolder in the identified patient folder, 
and does not write the other subfolders (such as ECG, CATH) that were previously created during de-identification.
