"""Clinical safety validation rules."""

import logging
import re
from datetime import datetime, timezone
from typing import List, Optional, Callable

from models.prescription import PrescriptionData

logger = logging.getLogger(__name__)

# Drug Catalogs

CONTROLLED_SUBSTANCES = [
    "oxycodone", "hydrocodone", "fentanyl", "morphine", "codeine",
    "alprazolam", "lorazepam", "diazepam", "temazepam",
    "methylphenidate", "amphetamine", "modafinil",
    "tramadol", "zolpidem", "gabapentin",
]

THERAPEUTIC_RANGES = {
    "lisinopril": (2.5, 80.0, "mg"),
    "metformin": (500.0, 2550.0, "mg"),
    "oxycodone": (5.0, 60.0, "mg"),
}

SPECIALTY_DRUGS = {
    "adalimumab": "Biologic — TNF Inhibitor",
    "etanercept": "Biologic — TNF Inhibitor",
    "infliximab": "Biologic — TNF Inhibitor",
    "rituximab": "Biologic — Anti-CD20",
    "trastuzumab": "Biologic — HER2 Antagonist",
    "bevacizumab": "Biologic — Anti-VEGF",
    "semaglutide": "GLP-1 Agonist",
    "dupilumab": "Biologic — IL-4/IL-13 Inhibitor",
    "secukinumab": "Biologic — IL-17A Inhibitor",
    "ustekinumab": "Biologic — IL-12/23 Inhibitor",
    "apixaban": "Specialty Anticoagulant",
    "rivaroxaban": "Specialty Anticoagulant",
    "lenalidomide": "Specialty Oncology — REMS Required",
    "thalidomide": "Specialty Oncology — REMS Required",
}

BEERS_CRITERIA_DRUGS = [
    "diphenhydramine", "zolpidem", "diazepam", "carisoprodol",
    "dicyclomine", "hydroxyzine", "meperidine", "methocarbamol",
]


# Date Parsing

def _parse_date(value: str) -> Optional[datetime]:
    """Try common date formats."""
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        pass
    try:
        dt = datetime.strptime(value, "%m/%d/%Y")
        if dt.day <= 12:
            logger.warning(
                f"Ambiguous date '{value}' parsed as %m/%d/%Y. "
                "Consider using YYYY-MM-DD for clarity."
            )
        return dt
    except ValueError:
        pass
    return None


# Validation Rules

def _check_mandatory_fields(data: PrescriptionData) -> List[str]:
    """Check for mandatory clinical fields."""
    return [
        f"BLOCKING: Missing {label}"
        for label, field in [
            ("Patient Name", data.patient_name),
            ("Medication Name", data.drug_name),
            ("Prescribed Quantity", data.quantity),
        ]
        if not field.value or str(field.value).strip() == ""
    ]


def _check_advisory_fields(data: PrescriptionData) -> List[str]:
    """Check for optional clinical fields."""
    return [
        f"ADVISORY: Missing {label}"
        for label, field in [
            ("Strength/Dosage", data.strength_dosage),
            ("Route", data.route),
            ("Frequency", data.frequency),
            ("Refills", data.refills),
        ]
        if not field.value or str(field.value).strip() == ""
    ]


def _check_confidence(data: PrescriptionData) -> List[str]:
    """Check AI confidence with critical field weighting."""
    critical_fields = [
        ("Patient Name", data.patient_name),
        ("Medication Name", data.drug_name),
    ]
    other_fields = [
        data.quantity, data.strength_dosage, data.route, data.frequency, data.refills,
    ]
    
    flags = []

    # 1. Critical Field Weighting (Target: 75%)
    for label, field in critical_fields:
        if field.value and field.confidence < 75:
            flags.append(f"BLOCKING: Low Confidence on Critical Field '{label}' ({field.confidence}%)")

    # 2. Overall Average Check (Target: 60%)
    all_populated = [f for _, f in critical_fields if f.value] + [f for f in other_fields if f.value]
    if all_populated:
        avg_confidence = sum(f.confidence for f in all_populated) / len(all_populated)
        if avg_confidence < 60:
            flags.append(f"BLOCKING: Low Overall Confidence ({avg_confidence:.1f}%)")
            
    return flags


def _check_controlled_and_expiry(data: PrescriptionData) -> List[str]:
    """Check controlled substances and expiry."""
    flags: List[str] = []
    drug_val = str(data.drug_name.value).lower() if data.drug_name.value else ""
    is_controlled = False

    for cs in CONTROLLED_SUBSTANCES:
        if re.search(rf"\b{re.escape(cs)}\b", drug_val):
            flags.append(f"ADVISORY: Controlled Substance Detected ({cs.capitalize()})")
            is_controlled = True
            break

    if data.date_written.value:
        written_dt = _parse_date(data.date_written.value)
        if written_dt:
            delta_days = (
                datetime.now(timezone.utc) - written_dt.replace(tzinfo=timezone.utc)
            ).days
            limit_days = 180 if is_controlled else 365
            if delta_days > limit_days:
                type_str = "Controlled" if is_controlled else "Standard"
                flags.append(
                    f"ADVISORY: Prescription Expired ({type_str} limit: {limit_days} days)"
                )

    return flags


def _check_dosage_range(data: PrescriptionData) -> List[str]:
    """Check dosage ranges."""
    if not data.strength_dosage.value or not data.drug_name.value:
        return []
    drug_val = str(data.drug_name.value).lower()
    match = re.search(r"(\d+\.?\d*)\s*mg", data.strength_dosage.value)
    if not match:
        return []
    dose_val = float(match.group(1))
    for drug_key, (min_d, max_d, unit) in THERAPEUTIC_RANGES.items():
        if drug_key in drug_val:
            if dose_val < min_d or dose_val > max_d:
                return [
                    f"ADVISORY: Unusual Dosage ({dose_val}{unit}) "
                    f"for {drug_key.capitalize()}"
                ]
            break
    return []


def _check_specialty_drugs(data: PrescriptionData) -> List[str]:
    """Check specialty drugs."""
    if not data.drug_name.value:
        return []
    drug_val = str(data.drug_name.value).lower()
    for specialty_drug, drug_class in SPECIALTY_DRUGS.items():
        if specialty_drug in drug_val:
            return [
                f"ADVISORY: Specialty Drug Detected ({drug_class}) "
                "— Prior Authorization Required"
            ]
    return []


def _check_bulk_dispensing(data: PrescriptionData) -> List[str]:
    """Check for bulk dispensing."""
    if not data.quantity.value:
        return []
    qty_match = re.search(r"(\d+\.?\d*)", str(data.quantity.value))
    if qty_match and float(qty_match.group(1)) >= 90:
        qty_val = int(float(qty_match.group(1)))
        return [
            f"ADVISORY: LTC Bulk Dispensing Detected (Qty: {qty_val}) "
            "— Facility-Level Authorization Required"
        ]
    return []


def _check_beers_criteria(data: PrescriptionData) -> List[str]:
    """Check Beers Criteria."""
    if not data.drug_name.value:
        return []
    drug_val = str(data.drug_name.value).lower()
    for beers_drug in BEERS_CRITERIA_DRUGS:
        if beers_drug in drug_val:
            return [
                f"ADVISORY: Beers Criteria — High-Risk Drug in Elderly "
                f"({beers_drug.capitalize()}). "
                "Consider therapeutic alternative per AGS guidelines."
            ]
    return []


def _check_dea_format(data: PrescriptionData) -> List[str]:
    """Check DEA Format (Compliance Rules)."""
    dea = data.prescriber_dea.value
    if dea and not dea.strip() == "":
        import re
        if not re.match(r"^[A-Z]{2}[0-9]{7}$", dea.strip().upper()):
            return [f"BLOCKING: Invalid Prescriber DEA Format ({dea.strip()})"]
    return []



# Rule Registry

_RULES: List[Callable[[PrescriptionData], List[str]]] = [
    _check_mandatory_fields,
    _check_advisory_fields,
    _check_confidence,
    _check_controlled_and_expiry,
    _check_dosage_range,
    _check_specialty_drugs,
    _check_bulk_dispensing,
    _check_beers_criteria,
    _check_dea_format,
]


def check_guardrails(data: PrescriptionData) -> List[str]:
    """Run all safety checks."""
    return [flag for rule in _RULES for flag in rule(data)]
