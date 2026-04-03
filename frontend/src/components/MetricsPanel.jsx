function MetricsPanel({ metrics, streaming }) {
  if (!metrics) return null;

  const useML = metrics.ml_relevant > 0 || 
                metrics.ml_less_relevant > 0 || 
                metrics.ml_irrelevant > 0 ||
                metrics.pending > 0;

  return (
    <div className="metrics-panel">
      <h3>Verification Metrics</h3>

      <div className="metric-item">
        <strong>Total:</strong> {metrics.total} <span> papers</span>
      </div>

      <div className="metric-item" style={{ marginTop: "12px" }}>
        <strong>— Link Validation —</strong>
      </div>
      <div className="metric-item">
        <strong>Valid:</strong> {metrics.valid || 0}
      </div>
      <div className="metric-item">
        <strong>Broken:</strong> {metrics.broken || 0}
      </div>
      <div className="metric-item">
        <strong>Invalid Metadata:</strong> {metrics.invalid_metadata || 0}
      </div>

      {useML && (
        <>
          <div className="metric-item" style={{ marginTop: "12px" }}>
            <strong>— ML Relevance —</strong>
          </div>
          <div className="metric-item">
            <strong>Highly Relevant:</strong> {metrics.ml_relevant || 0}
          </div>
          <div className="metric-item">
            <strong>Moderately Relevant:</strong> {metrics.ml_less_relevant || 0}
          </div>
          <div className="metric-item">
            <strong>Low Relevance:</strong> {metrics.ml_irrelevant || 0}
          </div>
        </>
      )}
    </div>
  );
}
export default MetricsPanel;