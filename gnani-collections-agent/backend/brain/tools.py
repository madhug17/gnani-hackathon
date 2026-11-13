import json
import logging
from typing import Dict, Any, Optional
from backend.config import settings

logger = logging.getLogger("bfsi_tools")

def _load_borrowers() -> list[dict]:
    if settings.BORROWER_PROFILES_PATH.exists():
        with open(settings.BORROWER_PROFILES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def _save_borrowers(data: list[dict]):
    with open(settings.BORROWER_PROFILES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def get_borrower_details(borrower_id: str) -> Dict[str, Any]:
    """
    Retrieves full BFSI credit account details, overdue EMIs, accrued late fees, 
    and payment history for a given borrower loan ID.
    
    Args:
        borrower_id: The unique loan identifier (e.g., 'LN-98231', 'LN-44102', 'LN-77319')
    """
    borrowers = _load_borrowers()
    for b in borrowers:
        if b.get("borrower_id") == borrower_id:
            return {
                "status": "success",
                "borrower_id": b["borrower_id"],
                "name": b["name"],
                "loan_type": b["loan_type"],
                "bank_name": b["bank_name"],
                "overdue_amount": b["overdue_amount"],
                "emi_amount": b["emi_amount"],
                "days_overdue": b["days_overdue"],
                "overdue_emis": b["overdue_emis"],
                "late_fee_accrued": b["late_fee_accrued"],
                "maximum_waivable_late_fee": b["maximum_waivable_late_fee"],
                "split_emi_allowed": b["split_emi_allowed"],
                "city": b["city"],
                "preferred_language": b["preferred_language"]
            }
    return {
        "status": "not_found",
        "message": f"Borrower loan account {borrower_id} was not found."
    }

def offer_split_emi_plan(borrower_id: str, split_installments: int = 2) -> Dict[str, Any]:
    """
    Restructures an overdue balance into multiple split installments (e.g. 50% today, 50% next payday)
    to alleviate cash-flow constraints and avoid default marking.
    
    Args:
        borrower_id: The unique loan identifier (e.g. 'LN-98231')
        split_installments: Number of parts to divide the overdue amount into (default: 2)
    """
    borrowers = _load_borrowers()
    for b in borrowers:
        if b.get("borrower_id") == borrower_id:
            if not b.get("split_emi_allowed", False):
                return {
                    "status": "ineligible",
                    "message": "Borrower account is not eligible for split EMI restructuring."
                }
            
            overdue = b["overdue_amount"]
            first_installment = round(overdue / split_installments, 2)
            remaining_installment = round(overdue - first_installment, 2)
            
            return {
                "status": "approved",
                "borrower_id": borrower_id,
                "borrower_name": b["name"],
                "total_overdue": overdue,
                "split_count": split_installments,
                "immediate_due_today": first_installment,
                "remaining_due_in_15_days": remaining_installment,
                "action": "Restructuring agreement drafted. SMS payment link generated."
            }

    return {"status": "not_found", "message": f"Borrower {borrower_id} not found."}

def apply_late_fee_waiver(borrower_id: str, waiver_percentage: int = 100) -> Dict[str, Any]:
    """
    Applies an instant relief waiver on accumulated late payment penalties and penal interest.
    
    Args:
        borrower_id: The unique loan identifier (e.g. 'LN-98231')
        waiver_percentage: Percentage of late fee to waive (up to 100%)
    """
    borrowers = _load_borrowers()
    for b in borrowers:
        if b.get("borrower_id") == borrower_id:
            accrued = b.get("late_fee_accrued", 0)
            if accrued <= 0:
                return {
                    "status": "no_fee",
                    "message": "No active late penalty exists on this account."
                }

            waiver_pct = min(100, max(0, waiver_percentage))
            amount_waived = round((accrued * waiver_pct) / 100.0, 2)
            new_overdue = b["overdue_amount"] - amount_waived
            
            # Update record
            b["late_fee_accrued"] = accrued - amount_waived
            b["overdue_amount"] = new_overdue
            _save_borrowers(borrowers)

            return {
                "status": "waiver_applied",
                "borrower_id": borrower_id,
                "borrower_name": b["name"],
                "original_late_fee": accrued,
                "amount_waived": amount_waived,
                "waiver_percentage": f"{waiver_pct}%",
                "updated_total_overdue": new_overdue,
                "message": f"Successfully waived ₹{amount_waived} late penalty fees."
            }

    return {"status": "not_found", "message": f"Borrower {borrower_id} not found."}

BFSI_TOOL_DEFINITIONS = [
    get_borrower_details,
    offer_split_emi_plan,
    apply_late_fee_waiver
]

