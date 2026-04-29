from sqlalchemy.exc import IntegrityError


CONSTRAINT_MESSAGES: dict[str, tuple[int, str]] = {
    "uq_event_user": (409, "User is already a participant of this event"),
    "uq_venue_sport": (409, "Sport is already assigned to this venue"),
    "events_no_active_overlap_per_venue": (409, "Venue already has an active event in this time"),
    "ck_wallet_accounts_balance_non_negative": (400, "Wallet balance cannot be negative"),
}


def map_integrity_error(exc: IntegrityError) -> tuple[int, str]:
    diag = getattr(getattr(exc, "orig", None), "diag", None)
    constraint_name = getattr(diag, "constraint_name", None)
    if constraint_name in CONSTRAINT_MESSAGES:
        return CONSTRAINT_MESSAGES[constraint_name]

    msg = str(getattr(exc, "orig", exc)).lower()
    if "foreign key constraint" in msg:
        return 409, "Operation violates data relation constraints"
    if "unique constraint" in msg:
        return 409, "Duplicate value violates uniqueness constraints"
    return 409, "Data integrity error"
