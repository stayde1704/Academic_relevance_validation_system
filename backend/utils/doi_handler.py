def clean_doi(raw_doi):
    if not raw_doi:
        return None
    return raw_doi.replace("https://doi.org/", "").strip()