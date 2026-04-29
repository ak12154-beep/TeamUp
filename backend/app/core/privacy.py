def mask_email(email: str | None) -> str | None:
    if email is None:
        return None

    local, sep, domain = email.partition("@")
    if not sep:
        return (local[:1] or "*") + "***"

    masked_local = (local[:1] or "*") + "***"
    domain_name, dot, tld = domain.partition(".")
    masked_domain = (domain_name[:1] or "*") + "***"
    if dot:
        masked_domain = f"{masked_domain}.{tld}"

    return f"{masked_local}@{masked_domain}"
