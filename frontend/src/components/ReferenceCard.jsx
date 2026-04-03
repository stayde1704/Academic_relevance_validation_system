import React from "react";

function ReferenceCard({ reference }) {
  const { title, year, doi, url, venue, status, ml_relevance, open_access } =
    reference;

  const validationLabel = {
    pending: "Validating...",
    broken: "Broken Link",
    invalid_metadata: "Invalid Metadata",
    valid: "Verified",
  };
  const mlLabel = {
    pending: "Analyzing...",
    skipped: "—",
    ml_relevant: "Highly Relevant",
    ml_less_relevant: "Moderately Relevant",
    ml_irrelevant: "Low Relevance"
  };

  const isOA = open_access?.is_oa;

  function generateBibTex(ref) {
    const key = (ref.title || "citation")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .slice(0, 40);

    const authorField = ref.authors ? ref.authors.join(" and ") : "";

    const bibtex = `@article{${key},
  title={${ref.title || ""}},
  author={${authorField}},
  journal={${ref.venue || ""}},
  year={${ref.year || ""}},
  doi={${ref.doi || ""}},
  url={${ref.url || ""}}
}`;

    return { key, bibtex };
  }

  function downloadBib() {
    const { key, bibtex } = generateBibTex(reference);

    const blob = new Blob([bibtex], { type: "text/plain" });
    const urlObj = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = urlObj;
    link.download = `${key}.bib`;

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    URL.revokeObjectURL(urlObj);
  }

  return (
    <div className={`reference-card ml-${ml_relevance}`}>
      <div className="oa-indicator">{isOA ? "🔓" : "🔒"}</div>

      <div className="card-content">
        <h3>{title || "Title Not Available"}</h3>

        {venue && (
          <div>
            <strong>Venue:</strong> {venue}
          </div>
        )}

        {year && (
          <div>
            <strong>Year:</strong> {year}
          </div>
        )}

        {doi && (
          <div>
            <strong>DOI:</strong> {doi}
          </div>
        )}

        {url && (
          <div>
            <strong>URL:</strong>{" "}
            <a href={url} target="_blank" rel="noopener noreferrer">
              {url.length > 50 ? url.slice(0, 50) + "..." : url}
            </a>
          </div>
        )}

        <div className="status-row">
          <div className="validation-status">
            <strong>Status:</strong> {validationLabel[status] || status}
          </div>
          {ml_relevance !== "skipped" && (
            <div className={`ml-status ml-${ml_relevance}`}>
              <strong>Relevance:</strong>{" "}
              {mlLabel[ml_relevance] || ml_relevance}
            </div>
          )}
        </div>

        <div className="card-footer">
          <button className="bib-download" onClick={downloadBib}>
            Download Citation
          </button>
        </div>
      </div>
    </div>
  );
}

export default ReferenceCard;
