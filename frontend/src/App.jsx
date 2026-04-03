import React from "react";
import { Routes, Route } from "react-router-dom";

import Dashboard from "./pages/Dashboard";
import FeedbackPage from "./pages/FeedbackPage";  // ← CHANGED: Import FeedbackPage instead

function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/feedback" element={<FeedbackPage />} />  {/* ← CHANGED */}
    </Routes>
  );
}

export default App;