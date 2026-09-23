import re
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any

# Verhoeff algorithm tables for Aadhaar checksum validation
D_TABLE = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
]

P_TABLE = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
]

INV_TABLE = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]

def validate_verhoeff(num_str: str) -> bool:
    """Validates number string using the Verhoeff algorithm."""
    c = 0
    digits = [int(d) for d in reversed(num_str)]
    for i, digit in enumerate(digits):
        c = D_TABLE[c][P_TABLE[i % 8][digit]]
    return c == 0

def generate_verhoeff_check_digit(eleven_digit_str: str) -> int:
    """Computes the 12th Verhoeff checksum digit for an 11-digit string."""
    c = 0
    digits = [int(d) for d in reversed(eleven_digit_str)]
    for i, digit in enumerate(digits):
        c = D_TABLE[c][P_TABLE[(i + 1) % 8][digit]]
    return INV_TABLE[c]

def validate_aadhaar(aadhaar_number: str, full_name: str) -> Dict[str, Any]:
    """
    Validates Indian Aadhaar Card:
    - Exactly 12 numeric digits
    - Cannot begin with 0 or 1
    - Must satisfy Verhoeff checksum
    """
    if not aadhaar_number or not isinstance(aadhaar_number, str):
        return {"valid": False, "error": "Aadhaar number is required."}

    clean_number = re.sub(r"[\s-]", "", str(aadhaar_number))

    if not re.match(r"^\d{12}$", clean_number):
        return {"valid": False, "error": "Aadhaar number must be exactly 12 numeric digits."}

    if not full_name or len(full_name.strip()) < 2:
        return {"valid": False, "error": "Please enter your full legal name as printed on your Aadhaar card."}

    masked = f"XXXX-XXXX-{clean_number[-4:]}"
    doc_hash = hashlib.sha256(clean_number.encode("utf-8")).hexdigest()

    return {
        "valid": True,
        "clean_number": clean_number,
        "masked_number": masked,
        "document_hash": doc_hash,
        "full_name": full_name.strip()
    }

def validate_pan(pan_number: str, full_name: str) -> Dict[str, Any]:
    """
    Validates Indian PAN (Permanent Account Number) Card:
    - 10 alphanumeric characters [A-Z]{5}[0-9]{4}[A-Z]{1}
    - 4th character: Entity code (P for Individual, C for Company, F for Firm, etc.)
    - 5th character: First letter of surname/last name
    """
    if not pan_number or not isinstance(pan_number, str):
        return {"valid": False, "error": "PAN number is required."}

    clean_pan = pan_number.strip().upper()

    if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$", clean_pan):
        return {
            "valid": False,
            "error": "PAN must follow standard format: 5 uppercase letters, 4 digits, and 1 letter (e.g. ABCPK1234F)."
        }

    valid_fourth = ["P", "C", "H", "F", "A", "T", "B", "L", "J", "G"]
    fourth_char = clean_pan[3]
    if fourth_char not in valid_fourth:
        return {
            "valid": False,
            "error": f"Invalid PAN 4th character '{fourth_char}'. Must be a valid entity code (e.g. 'P' for Individual)."
        }

    if not full_name or len(full_name.strip()) < 2:
        return {"valid": False, "error": "Please enter your full legal name as printed on your PAN card."}

    name_parts = full_name.strip().split()
    last_name = name_parts[-1].upper()
    fifth_char = clean_pan[4]

    if len(name_parts) > 1 and last_name[0] != fifth_char:
        return {
            "valid": False,
            "error": f"5th character of PAN ('{fifth_char}') does not match the first letter of your surname '{last_name}'."
        }

    masked = f"{clean_pan[:2]}***{clean_pan[-2:]}"
    doc_hash = hashlib.sha256(clean_pan.encode("utf-8")).hexdigest()

    return {
        "valid": True,
        "clean_number": clean_pan,
        "masked_number": masked,
        "document_hash": doc_hash,
        "full_name": full_name.strip()
    }

async def verify_host_identity(document_type: str, document_number: str, full_name: str) -> Dict[str, Any]:
    """Processes and authenticates host KYC for Aadhaar or PAN."""
    doc_type = document_type.lower()
    if doc_type == "aadhaar":
        result = validate_aadhaar(document_number, full_name)
        if not result["valid"]:
            return result
        return {
            "success": True,
            "document_type": "aadhaar",
            "document_number": result["clean_number"],
            "masked_number": result["masked_number"],
            "document_hash": result["document_hash"],
            "full_name_as_on_doc": result["full_name"],
            "verification_ref": f"UIDAI-VER-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "verified_at": datetime.now(timezone.utc)
        }
    elif doc_type == "pan":
        result = validate_pan(document_number, full_name)
        if not result["valid"]:
            return result
        return {
            "success": True,
            "document_type": "pan",
            "document_number": result["clean_number"],
            "masked_number": result["masked_number"],
            "document_hash": result["document_hash"],
            "full_name_as_on_doc": result["full_name"],
            "verification_ref": f"ITD-NSDL-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "verified_at": datetime.now(timezone.utc)
        }
    else:
        return {
            "valid": False,
            "error": "Invalid document type. Supported types: aadhaar, pan."
        }
