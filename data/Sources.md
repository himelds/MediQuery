# Data Sources

This corpus combines two sources, both with permissive licensing for reuse.

## Operational documents (`billing/`, `clinical/`, `equipment/`, `general/`, `nursing/`)

Curated from publicly available policy publications by **University Hospitals
Plymouth NHS Trust**, retrieved from <https://www.plymouthhospitals.nhs.uk/trust-policies>.

These documents are licensed under the **UK Open Government Licence v3.0**
(<https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/>),
which permits free reuse for commercial and non-commercial purposes subject to
attribution. The licence is compatible with Creative Commons Attribution 4.0.

Required attribution statement:

> Contains public sector information from University Hospitals Plymouth NHS
> Trust, licensed under the Open Government Licence v3.0.

### Document inventory

| Collection | Local file | Source document |
|---|---|---|
| `billing/` | `financial_governance_policy.pdf` | Financial Governance Policy |
| `billing/` | `cash_and_treasury_management_policy.pdf` | Cash and Treasury Management Policy |
| `billing/` | `overseas_visitors_policy.pdf` | Overseas Visitors Policy |
| `clinical/` | `resuscitation_policy.pdf` | Resuscitation Policy |
| `clinical/` | `hospital_transfusion_policy.pdf` | Hospital Transfusion Policy |
| `clinical/` | `consent_to_treatment_policy.pdf` | Consent to Examination or Treatment Policy |
| `equipment/` | `medical_gases_operational_policy.pdf` | Operational Policy for Medical Gases |
| `equipment/` | `medical_devices_management_policy.pdf` | The Management and Use of Medical Devices Policy |
| `equipment/` | `electrical_safety_policy.pdf` | Electrical Safety Policy |
| `general/` | `conduct_policy.pdf` | Conduct Policy |
| `general/` | `uniform_and_dress_code_policy.pdf` | Uniform and Dress Code Policy |
| `general/` | `leave_and_time_off_work_policy.pdf` | Leave and Time Off Work Policy |
| `nursing/` | `inpatient_observations_escalation_policy.pdf` | Essential Adult Inpatient Observations Reporting and Escalation Policy |
| `nursing/` | `pressure_ulcers_prevention_policy.pdf` | Prevention and Management of Pressure Ulcers Policy |
| `nursing/` | `moving_and_handling_policy.pdf` | Moving and Handling People and Objects Policy |

To re-download the corpus from source:

```bash
python scripts/download_corpus.py --output-dir data
```

## Medical QA corpus (`medical/corpus.json`)

Derived from the **MedQuAD** dataset, U.S. National Library of Medicine, which
is in the public domain. Source: <https://github.com/abachaa/MedQuAD>.

The raw archive is kept under `data/raw/MedQuAD/` and is gitignored. The
parsed JSON in `medical/corpus.json` is produced by
`backend/ingestion/parse_medquad.py`.

## Notice

This is a portfolio project. The corpus is used solely to demonstrate the
retrieval and access-control pipeline. The system is not affiliated with
University Hospitals Plymouth NHS Trust, the U.S. National Library of
Medicine, or any other organisation referenced in the source documents.
