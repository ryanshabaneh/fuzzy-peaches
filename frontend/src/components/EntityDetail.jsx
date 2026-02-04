import React from 'react';

export default function EntityDetail({ entity }) {
  const formatExplanation = (text = '') =>
    text
      .replace(/Possible match/gi, 'Low-confidence edge')
      .replace(/Transitive closure warning/gi, 'Some records were linked indirectly')
      .replace(/Selected as canonical representative/gi, 'Chosen as the main name')
      .replace(/Flagged for manual review/gi, 'Worth a second look');

  const rationale = entity.selection_rationale || {};
  const rationaleOptions = [
    {
      key: 'centrality',
      label: 'Highest centrality score among grouped records',
      value: rationale.centrality ?? 0
    },
    {
      key: 'completeness',
      label: 'Most complete metadata across matches',
      value: rationale.completeness ?? 0
    },
    {
      key: 'cleanliness',
      label: 'Cleanest metadata across matches',
      value: rationale.cleanliness ?? 0
    }
  ];
  const topRationale = rationaleOptions.reduce((best, current) =>
    current.value > best.value ? current : best
  );

  return (
    <div className="entity-detail">
      <div className="detail-section">
        <h4>Grouped records ({entity.matched_record_ids.length})</h4>
        <ul className="record-list">
          {entity.matched_record_ids.map(id => (
            <li key={id}>
              <span className="record-id">{id}</span>
              <p className="explanation">{formatExplanation(entity.match_explanations[id])}</p>
            </li>
          ))}
        </ul>
      </div>

      <div className="detail-section">
        <h4>Why this name?</h4>
        <div className="rationale-card">
          <p className="rationale-summary">
            {topRationale.label}.
          </p>
          <ul className="rationale-metrics">
            <li>Completeness: {Math.round((rationale.completeness ?? 0) * 100)}%</li>
            <li>Cleanliness: {Math.round((rationale.cleanliness ?? 0) * 100)}%</li>
            <li>Centrality: {Math.round((rationale.centrality ?? 0) * 100)}%</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
