import React from "react";
import ReferenceCard from "./ReferenceCard";

function ResultsList({ references }) {
  if (!references || !references.length) return null;

  return (
    <div className="results-list">
      {references.map((ref, index) => (
        <ReferenceCard
          key={ref.doi || index}
          reference={ref}
        />
      ))}
    </div>
  );
}

export default ResultsList;