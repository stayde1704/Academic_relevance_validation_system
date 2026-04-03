import React from "react";

function QueryInput({ query, setQuery, instruction, setInstruction, handleGenerate, loading }) {
  return (
    <div className="query-input">
      <textarea
        className="query-textarea"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Enter your research query..."
      />

      <textarea
        className="query-textarea instruction-textarea"
        value={instruction}
        onChange={(e) => setInstruction(e.target.value)}
        placeholder="Instructions for relevance (Optional)"
      />

      <button
        className="generate-button"
        onClick={handleGenerate}
        disabled={loading}
      >
        {loading ? "Processing..." : "Generate"}
      </button>
    </div>
  );
}

export default QueryInput;