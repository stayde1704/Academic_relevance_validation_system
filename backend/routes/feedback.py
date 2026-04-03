from flask import Blueprint, request, jsonify
from datetime import datetime
import requests
import json
from utils.doi_handler import clean_doi

feedback_bp = Blueprint('feedback', __name__)


@feedback_bp.route("/fetch-paper-info", methods=["POST"])
def fetch_paper_info():
    data = request.get_json()
    
    if not data or "doi" not in data:
        return jsonify({"error": "DOI required"}), 400
    
    doi = clean_doi(data["doi"])
    
    if not doi:
        return jsonify({"error": "Invalid DOI format"}), 400
    
    try:
        crossref_url = f"https://api.crossref.org/works/{doi}"
        response = requests.get(crossref_url, timeout=10)
        
        if response.status_code == 200:
            crossref_data = response.json()
            message = crossref_data.get("message", {})
            
            authors = []
            for author in message.get("author", []):
                given = author.get("given", "")
                family = author.get("family", "")
                full_name = f"{given} {family}".strip()
                if full_name:
                    authors.append(full_name)
            
            venue = None
            container_title = message.get("container-title", [])
            if container_title:
                venue = container_title[0]
            
            year = None
            published = message.get("published-print") or message.get("published-online")
            if published and "date-parts" in published:
                year = published["date-parts"][0][0]
            
            paper_info = {
                "title": message.get("title", [""])[0],
                "authors": authors,
                "year": year,
                "venue": venue,
                "doi": doi
            }
            
            return jsonify({"paper": paper_info})
    
    except Exception as e:
        print(f"CrossRef API error: {e}")
    
    try:
        openalex_url = f"https://api.openalex.org/works/doi:{doi}"
        response = requests.get(openalex_url, timeout=10)
        
        if response.status_code == 200:
            openalex_data = response.json()
            
            authors = [
                auth.get("author", {}).get("display_name")
                for auth in openalex_data.get("authorships", [])
            ]
            
            primary_location = openalex_data.get("primary_location") or {}
            source = primary_location.get("source") or {}
            venue = source.get("display_name")
            
            paper_info = {
                "title": openalex_data.get("display_name"),
                "authors": authors,
                "year": openalex_data.get("publication_year"),
                "venue": venue,
                "doi": doi
            }
            
            return jsonify({"paper": paper_info})
    
    except Exception as e:
        print(f"OpenAlex API error: {e}")
    
    return jsonify({"error": "Paper not found"}), 404


@feedback_bp.route("/submit-feedback", methods=["POST"])
def submit_feedback():
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    required_fields = ["paper", "issue", "user"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": "Missing required field: {field}"}), 400
    
    data["server_timestamp"] = datetime.utcnow().isoformat()
    
    try:
        try:
            with open("feedback_data.json", "r") as f:
                feedback_list = json.load(f)
        except FileNotFoundError:
            feedback_list = []
        
        feedback_list.append(data)
        
        with open("feedback_data.json", "w") as f:
            json.dump(feedback_list, f, indent=2)
        
        return jsonify({
            "message": "Feedback submitted successfully",
            "feedback_id": len(feedback_list)
        })
    
    except Exception as e:
        print(f"Error saving feedback: {e}")
        return jsonify({"error": "Failed to save feedback"}), 500