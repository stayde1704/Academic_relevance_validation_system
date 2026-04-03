import React from "react";

function ToggleView({ showFiltered, setShowFiltered }) {
  return (
    <div className="toggle-section">
      <label>
        <input
          type="checkbox"
          checked={showFiltered}
          onChange={() => setShowFiltered(!showFiltered)}
        />
        Show Only Relevant References
      </label>
    </div>
  );
}

export default ToggleView;