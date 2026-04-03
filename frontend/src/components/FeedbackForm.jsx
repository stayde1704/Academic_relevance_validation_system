import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

function FeedbackForm() {
  const navigate = useNavigate();
  const [doi, setDoi] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleNext = async () => {
    if (!doi.trim()) {
      setError("Please enter a DOI");
      return;
    }

    setLoading(true);
    setError("");

    try {
      // Fetch paper info from backend
      const response = await fetch("http://localhost:5000/fetch-paper-info", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ doi: doi.trim() })
      });

      if (!response.ok) {
        throw new Error("Failed to fetch paper information");
      }

      const data = await response.json();

      // Navigate to feedback page with paper data
      navigate("/feedback", { state: { paper: data.paper } });

      // Clear the input after successful navigation
      setDoi("");
    } catch (err) {
      setError(err.message || "Error fetching paper information");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") {
      handleNext();
    }
  };

  return (
    <div className="feedback-form">
      <h3>Report Reference Issue</h3>
      <p className="feedback-description">
        Found a problem with a reference? Enter the DOI to submit feedback.
      </p>

      <div className="feedback-input-group">
        <input
          type="text"
          className="doi-input"
          value={doi}
          onChange={(e) => setDoi(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Enter DOI (e.g., 10.1234/example)"
          disabled={loading}
        />

        <button
          className="next-button"
          onClick={handleNext}
          disabled={loading || !doi.trim()}
        >
          {loading ? "Loading..." : "Next →"}
        </button>
      </div>

      {error && <div className="feedback-error">{error}</div>}
    </div>
  );
}

export default FeedbackForm;