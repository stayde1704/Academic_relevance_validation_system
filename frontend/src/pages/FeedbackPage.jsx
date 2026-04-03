import React, { useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";

function FeedbackPage() {
  const location = useLocation();
  const navigate = useNavigate();
  
  // Paper data passed from FeedbackForm
  const [paperData, setPaperData] = useState(null);
  
  // Form state
  const [formData, setFormData] = useState({
    issueType: "",
    description: "",
    userName: "",
    userEmail: "",
    userAffiliation: "",
    userRole: ""
  });
  
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  // Load paper data from location state
  useEffect(() => {
    if (location.state?.paper) {
      setPaperData(location.state.paper);
    } else {
      // If no paper data, redirect back to dashboard
      setError("No paper data found. Redirecting...");
      setTimeout(() => navigate("/"), 2000);
    }
  }, [location.state, navigate]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.issueType || !formData.description || !formData.userName || !formData.userEmail) {
      setError("Please fill in all required fields");
      return;
    }

    setLoading(true);
    setError("");

    const feedbackPayload = {
      paper: paperData,
      issue: {
        type: formData.issueType,
        description: formData.description
      },
      user: {
        name: formData.userName,
        email: formData.userEmail,
        affiliation: formData.userAffiliation || null,
        role: formData.userRole || null
      },
      timestamp: new Date().toISOString()
    };

    try {
      const response = await fetch("http://localhost:5000/submit-feedback", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(feedbackPayload)
      });

      if (!response.ok) {
        throw new Error("Failed to submit feedback");
      }

      const result = await response.json();
      
      setSuccess(true);
      
      // Redirect back to dashboard after 3 seconds
      setTimeout(() => {
        navigate("/");
      }, 3000);

    } catch (err) {
      console.error("Submission error:", err);
      setError("Failed to submit feedback. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    navigate("/");
  };

  if (!paperData) {
    return (
      <div className="feedback-page-container">
        <div className="feedback-loading">
          <p>Loading paper information...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="feedback-page-container">
      <div className="feedback-page-content">
        
        {/* Header */}
        <div className="feedback-header">
          <h1>📝 Reference Feedback Form</h1>
          <p>Help us improve reference validation accuracy</p>
        </div>

        {/* Success Message */}
        {success && (
          <div className="success-message">
            Thank you! Your feedback has been submitted successfully. Redirecting to dashboard...
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="error-message">
            ⚠️ {error}
          </div>
        )}

        {!success && (
          <form onSubmit={handleSubmit} className="feedback-form-container">
            
            {/* Paper Information Section */}
            <div className="feedback-section">
              <h2 className="section-title">📄 Reference Information</h2>
              <div className="info-grid">
                <div className="info-item">
                  <span className="info-label">Title:</span>
                  <span className="info-value">{paperData.title || "N/A"}</span>
                </div>
                <div className="info-item">
                  <span className="info-label">Authors:</span>
                  <span className="info-value">
                    {paperData.authors ? paperData.authors.join(", ") : "N/A"}
                  </span>
                </div>
                <div className="info-item">
                  <span className="info-label">Year:</span>
                  <span className="info-value">{paperData.year || "N/A"}</span>
                </div>
                <div className="info-item">
                  <span className="info-label">Journal:</span>
                  <span className="info-value">{paperData.venue || "N/A"}</span>
                </div>
                <div className="info-item">
                  <span className="info-label">DOI:</span>
                  <span className="info-value">{paperData.doi || "N/A"}</span>
                </div>
              </div>
            </div>

            {/* Issue Details Section */}
            <div className="feedback-section">
              <h2 className="section-title">🔍 Issue Details</h2>
              
              <div className="form-group">
                <label htmlFor="issueType">
                  Issue Type <span className="required">*</span>
                </label>
                <select
                  id="issueType"
                  name="issueType"
                  value={formData.issueType}
                  onChange={handleInputChange}
                  required
                >
                  <option value="">-- Select Issue Type --</option>
                  <option value="irrelevant">Irrelevant to Query</option>
                  <option value="broken_link">Broken Link</option>
                  <option value="invalid_metadata">Invalid Metadata</option>
                  <option value="fabricated">Fabricated/Hallucinated</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="description">
                  Description <span className="required">*</span>
                </label>
                <textarea
                  id="description"
                  name="description"
                  value={formData.description}
                  onChange={handleInputChange}
                  placeholder="Please describe the issue you encountered..."
                  rows="5"
                  required
                />
              </div>
            </div>

            {/* User Information Section */}
            <div className="feedback-section">
              <h2 className="section-title">👤 Your Information</h2>
              
              <div className="form-group">
                <label htmlFor="userName">
                  Name <span className="required">*</span>
                </label>
                <input
                  type="text"
                  id="userName"
                  name="userName"
                  value={formData.userName}
                  onChange={handleInputChange}
                  placeholder="Enter your full name"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="userEmail">
                  Email <span className="required">*</span>
                </label>
                <input
                  type="email"
                  id="userEmail"
                  name="userEmail"
                  value={formData.userEmail}
                  onChange={handleInputChange}
                  placeholder="your.email@example.com"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="userAffiliation">
                  Affiliation (Optional)
                </label>
                <input
                  type="text"
                  id="userAffiliation"
                  name="userAffiliation"
                  value={formData.userAffiliation}
                  onChange={handleInputChange}
                  placeholder="University or Organization"
                />
              </div>

              <div className="form-group">
                <label htmlFor="userRole">
                  Role (Optional)
                </label>
                <select
                  id="userRole"
                  name="userRole"
                  value={formData.userRole}
                  onChange={handleInputChange}
                >
                  <option value="">-- Select Your Role --</option>
                  <option value="researcher">Researcher</option>
                  <option value="student">Student</option>
                  <option value="professor">Professor</option>
                  <option value="industry">Industry Professional</option>
                  <option value="other">Other</option>
                </select>
              </div>
            </div>

            {/* Submit Buttons */}
            <div className="button-group">
              <button
                type="button"
                className="cancel-btn"
                onClick={handleCancel}
                disabled={loading}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="submit-btn"
                disabled={loading}
              >
                {loading ? "Submitting..." : "Submit Feedback"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

export default FeedbackPage;