import React, { useState, useEffect } from "react";

function FiltersPanel({ filters, setFilters }) {

  const [localFilters, setLocalFilters] = useState(filters);

  useEffect(() => {
    setLocalFilters(filters);
  }, [filters]);

  const updateLocalFilter = (key, value) => {
    setLocalFilters((prev) => ({
      ...prev,
      [key]: value
    }));
  };

  const applyFilters = () => {
    setFilters(localFilters);
  };

  const resetFilters = () => {
    const defaultFilters = {
      status: "all",
      openAccess: false,
      yearFrom: "",
      yearTo: ""
    };

    setLocalFilters(defaultFilters);
    setFilters(defaultFilters);
  };

  return (
    <div className="left-panel">

      <h3>Filters</h3>


      <div className="filter-section">
        <strong>Status</strong>

        <label className="filter-item">
          <input
            type="radio"
            name="status"
            checked={localFilters.status === "all"}
            onChange={() => updateLocalFilter("status", "all")}
          />
          Show All
        </label>

        <label className="filter-item">
          <input
            type="radio"
            name="status"
            checked={localFilters.status === "relevant_only"}
            onChange={() => updateLocalFilter("status", "relevant_only")}
          />
          Show Only Relevant
        </label>

        <label className="filter-item">
          <input
            type="radio"
            name="status"
            checked={localFilters.status === "hide_irrelevant"}
            onChange={() => updateLocalFilter("status", "hide_irrelevant")}
          />
          Hide Irrelevant
        </label>
      </div>


      {/* ACCESS FILTER */}

      <div className="filter-section">
        <strong>Access</strong>

        <label className="filter-item">
          <input
            type="checkbox"
            checked={localFilters.openAccess}
            onChange={(e) =>
              updateLocalFilter("openAccess", e.target.checked)
            }
          />
          Open Access Only
        </label>
      </div>


      {/* YEAR RANGE */}

      <div className="filter-section">
        <strong>Year Range</strong>

        <input
          type="number"
          placeholder="From"
          value={localFilters.yearFrom}
          onChange={(e) =>
            updateLocalFilter("yearFrom", e.target.value)
          }
        />

        <input
          type="number"
          placeholder="To"
          value={localFilters.yearTo}
          onChange={(e) =>
            updateLocalFilter("yearTo", e.target.value)
          }
        />
      </div>


      {/* ACTION BUTTONS */}

      <div className="filter-actions">

        <button className="apply-btn" onClick={applyFilters}>
          Apply Filters
        </button>

        <button className="reset-btn" onClick={resetFilters}>
          Reset
        </button>

      </div>

    </div>
  );
}

export default FiltersPanel;