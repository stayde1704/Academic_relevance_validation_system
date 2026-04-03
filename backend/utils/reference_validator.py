import requests

def check_link(url, doi=None):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/html"
    }

    try:
        if doi:
            url = f"https://doi.org/{doi}"

        r = requests.get(
            url,
            headers=headers,
            allow_redirects=True,
            timeout=8
        )

        if r.status_code < 500:
            return True

        return False

    except requests.exceptions.RequestException:
        return False


def verify_metadata(doi):
    if not doi:
        return False

    try:
        url = f"https://api.crossref.org/works/{doi}"
        r = requests.get(url, timeout=5)

        return r.status_code == 200

    except:
        return False


def evaluate_reference(paper_url, paper_doi):
    """
    Sequential evaluation pipeline
    """
    link_ok = check_link(paper_url)

    if not link_ok:
        return "broken"

    metadata_ok = verify_metadata(paper_doi)

    if not metadata_ok:
        return "invalid_metadata"

    return "valid"