import requests
from .doi_handler import clean_doi
from .reference_validator import evaluate_reference


def fetch_papers(query, page=1, per_page=15):
    """
    Fetch papers from OpenAlex with pagination
    """
    url = "https://api.openalex.org/works"
    
    params = {
        "search": query.strip(),
        "per_page": per_page,
        "page": page
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])

        collected = []

        for item in results:
            primary_location = item.get("primary_location") or {}
            source = primary_location.get("source") or {}

            paper_url = primary_location.get("landing_page_url")
            raw_doi = item.get("doi")
            paper_doi = clean_doi(raw_doi)

            status = evaluate_reference(paper_url, paper_doi)

            open_access_info = item.get("open_access") or {}

            collected.append({
                "title": item.get("display_name"),
                "year": item.get("publication_year"),
                "doi": paper_doi,
                "citations": item.get("cited_by_count"),
                "venue": source.get("display_name"),
                "url": paper_url,
                "authors": [
                    auth.get("author", {}).get("display_name")
                    for auth in item.get("authorships", [])
                ],
                "status": status,
                "open_access": {
                    "is_oa": open_access_info.get("is_oa", False),
                    "oa_status": open_access_info.get("oa_status"),
                    "oa_url": open_access_info.get("oa_url")
                },
                "source": {
                    "name": source.get("display_name"),
                    "publisher": source.get("publisher"),
                    "type": source.get("type"),
                    "issn_l": source.get("issn_l")
                }
            })

        meta = data.get("meta", {})
        total_count = meta.get("count", 0)
        has_more = (page * per_page) < total_count

        return collected, has_more

    except Exception as e:
        print(f"OpenAlex API error: {e}")
        return [], False