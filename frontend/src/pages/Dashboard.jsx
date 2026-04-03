import React, { useState, useRef, useMemo } from "react";
import QueryInput from "../components/QueryInput";
import ResultsList from "../components/ResultsList";
import MetricsPanel from "../components/MetricsPanel";
import FiltersPanel from "../components/FiltersPanel";
import FeedbackForm from "../components/FeedbackForm";
import "../App.css";

const PAPERS_PER_PAGE = 40;

function applyFilters(references, filters) {
  return references.filter((ref) => {
    if (filters.openAccess && !ref.open_access?.is_oa) return false;
    if (filters.yearFrom && ref.year && ref.year < Number(filters.yearFrom))
      return false;
    if (filters.yearTo && ref.year && ref.year > Number(filters.yearTo))
      return false;
    if (filters.status === "relevant_only" && ref.status !== "valid")
      return false;
    if (
      filters.status === "hide_irrelevant" &&
      ref.status === "invalid_metadata"
    )
      return false;
    return true;
  });
}

function Dashboard() {
  const [query, setQuery] = useState("");
  const [instruction, setInstruction] = useState("");

  const allReferencesRef = useRef([]);
  const [allReferences, setAllReferences] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [currentBatch, setCurrentBatch] = useState(0);
  const [hasMore, setHasMore] = useState(false);

  const [filters, setFilters] = useState({
    status: "all",
    openAccess: false,
    yearFrom: "",
    yearTo: "",
  });

  const filteredReferences = useMemo(
    () => applyFilters(allReferences, filters),
    [allReferences, filters],
  );

  const totalPages = Math.ceil(filteredReferences.length / PAPERS_PER_PAGE);

  const displayedReferences = useMemo(() => {
    const start = (currentPage - 1) * PAPERS_PER_PAGE;
    return filteredReferences.slice(start, start + PAPERS_PER_PAGE);
  }, [filteredReferences, currentPage]);

  const handleSetFilters = (newFilters) => {
    setFilters(newFilters);
    setCurrentPage(1);
  };

  const handleLoadBatch = async (batchNumber) => {
    if (!query.trim()) return;

    setStreaming(true);
    setLoading(batchNumber === 1);

    if (batchNumber === 1) {
      allReferencesRef.current = [];
      setAllReferences([]);
      setCurrentPage(1);
      setHasMore(false);
      setMetrics({
        total: 0,
        pending: 0,
        valid: 0,
        broken: 0,
        invalid_metadata: 0,
        ml_relevant: 0,
        ml_less_relevant: 0,
        ml_irrelevant: 0,
      });
    }

    try {
      const response = await fetch("http://localhost:5000/evaluate-stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          instruction: instruction.trim(),
          batch: batchNumber,
        }),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        let value, done;
        try {
          ({ value, done } = await reader.read());
        } catch (e) {
          if (e.name === "AbortError") break;
          throw e;
        }
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;

          let event;
          try {
            event = JSON.parse(line.slice(6));
          } catch {
            continue;
          }
          console.log("SSE event:", event.type); //debug stmt

          if (event.type === "paper") {
            allReferencesRef.current = [
              ...allReferencesRef.current,
              event.data,
            ];
            setAllReferences([...allReferencesRef.current]);
            setLoading(false);
            setMetrics((prev) => ({
              ...prev,
              total: prev.total + 1,
              pending: prev.pending + 1,
            }));
          } else if (event.type === "status_update") {
            const updated = [...allReferencesRef.current];
            if (updated[event.index]) {
              updated[event.index] = {
                ...updated[event.index],
                status: event.status,
                ml_relevance: event.ml_relevance,
              };
            }
            allReferencesRef.current = updated;
            setAllReferences([...updated]);

            setMetrics((prev) => ({
              ...prev,
              pending: Math.max(0, prev.pending - 1),
              [event.status]: (prev[event.status] || 0) + 1,
              ...(event.ml_relevance !== "skipped" && {
                [event.ml_relevance]: (prev[event.ml_relevance] || 0) + 1,
              }),
            }));
          } else if (event.type === "complete") {
            setStreaming(false);
            setLoading(false);
            // show Load More only if this batch returned a full 1000 papers
            setHasMore(event.total === 1000);
            console.log(`✅ Batch ${event.batch} done: ${event.total} papers`);
          }
        }
      }
    } catch (error) {
      console.error("Stream error:", error);
    } finally {
      setStreaming(false);
      setLoading(false);
    }
  };

  const handlePageChange = (pageNumber) => {
    setCurrentPage(pageNumber);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const getPageNumbers = () => {
    if (totalPages <= 7)
      return Array.from({ length: totalPages }, (_, i) => i + 1);
    const pages = [];
    const left = Math.max(2, currentPage - 2);
    const right = Math.min(totalPages - 1, currentPage + 2);
    pages.push(1);
    if (left > 2) pages.push("ellipsis-left");
    for (let i = left; i <= right; i++) pages.push(i);
    if (right < totalPages - 1) pages.push("ellipsis-right");
    pages.push(totalPages);
    return pages;
  };

  return (
    <div className="app-container">
      <div className="top-container">
        <div className="header-text">
          <h1>Academic Reference Validation System</h1>
          <p className="header-subtitle">
            AI-powered validation with relevance scoring
          </p>
        </div>

        <QueryInput
          query={query}
          setQuery={setQuery}
          instruction={instruction}
          setInstruction={setInstruction}
          handleGenerate={() => {
            setCurrentBatch(1);
            handleLoadBatch(1);
          }}
          loading={loading}
        />
      </div>

      <div className="main-layout">
        <FiltersPanel filters={filters} setFilters={handleSetFilters} />

        <div className="center-panel">
          <ResultsList references={displayedReferences} />

          {streaming && (
            <div className="streaming-indicator">
              <div className="spinner"></div>
              <p>
                Fetching and analyzing...{" "}
                {/* <span style={{ color: "#2563eb", fontWeight: 600 }}>
                  {allReferences.length} loaded
                </span> */}
              </p>
            </div>
          )}

          {filteredReferences.length > PAPERS_PER_PAGE && (
            <div className="pagination">
              <button
                className="pagination-btn"
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
              >
                ←
              </button>

              <div className="pagination-numbers">
                {getPageNumbers().map((p) =>
                  p === "ellipsis-left" || p === "ellipsis-right" ? (
                    <span key={p} className="pagination-ellipsis">
                      …
                    </span>
                  ) : (
                    <button
                      key={p}
                      className={`pagination-num-btn ${p === currentPage ? "active" : ""}`}
                      onClick={() => handlePageChange(p)}
                    >
                      {p}
                    </button>
                  ),
                )}
              </div>

              <button
                className="pagination-btn"
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
              >
                →
              </button>

              <span className="pagination-info">
                {currentPage}/{totalPages}
              </span>
            </div>
          )}

          {/* Load More — only shows after streaming completes and there are more results */}
          {!streaming && hasMore && (
            <div style={{ textAlign: "center", padding: "16px 0" }}>
              <button
                className="pagination-btn"
                style={{ minWidth: "140px", padding: "8px 16px" }}
                onClick={() => {
                  const next = currentBatch + 1;
                  setCurrentBatch(next);
                  handleLoadBatch(next);
                }}
              >
                Load More Papers
              </button>
            </div>
          )}
        </div>

        <div className="right-panel">
          <MetricsPanel metrics={metrics} streaming={streaming} />
          <FeedbackForm />
        </div>
      </div>
    </div>
  );
}

export default Dashboard;