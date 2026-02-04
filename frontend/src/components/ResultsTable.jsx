import React, { useState } from 'react';
import EntityDetail from './EntityDetail';
import MatchGraphPreview from './MatchGraphPreview';

export default function ResultsTable({ result }) {
  const [expandedId, setExpandedId] = useState(null);
  const [notesOpen, setNotesOpen] = useState(false);
  const [viewMode, setViewMode] = useState('attention');

  if (!result) return null;

  const flaggedIds = new Set(result.flagged_entity_ids ?? []);
  const formatNote = (text) =>
    text
      .replace(/Transitive closure warning/gi, 'Some records were linked indirectly')
      .replace(/Selected as canonical representative/gi, 'Chosen as the main name')
      .replace(/Flagged for manual review/gi, 'Worth a second look')
      .replace(/Manual review recommended/gi, 'Review suggested');

  const entitiesWithMeta = result.entities.map((entity, index) => {
    const isSingleton = entity.matched_record_ids.length === 1;
    const isFlagged = flaggedIds.has(entity.id);
    const matchExplanations = Object.values(entity.match_explanations ?? {});
    const hasBorderlineMatch = matchExplanations.some((text) => /possible match/i.test(text));
    const priority = isFlagged ? 0 : (!isSingleton && hasBorderlineMatch ? 1 : (!isSingleton ? 2 : 3));

    return {
      entity,
      index,
      isSingleton,
      isFlagged,
      hasBorderlineMatch,
      priority
    };
  });

  const sortedEntities = [...entitiesWithMeta].sort((a, b) => {
    if (a.priority !== b.priority) return a.priority - b.priority;
    return a.index - b.index;
  });

  const visibleEntities = sortedEntities.filter((item) => {
    if (viewMode === 'attention') {
      return !item.isSingleton && (item.isFlagged || item.hasBorderlineMatch);
    }
    if (viewMode === 'groups') {
      return !item.isSingleton;
    }
    return item.isSingleton;
  });

  const getAttentionHint = (isFlagged, hasBorderlineMatch) => {
    if (isFlagged) return 'Low transitive consistency';
    if (hasBorderlineMatch) return 'Borderline similarity across records';
    return null;
  };

  const totalRecords = result.entities.reduce(
    (sum, e) => sum + e.matched_record_ids.length,
    0
  );
  const totalEntities = result.entities.length;
  const needsReviewCount = entitiesWithMeta.filter(
    (item) => !item.isSingleton && (item.isFlagged || item.hasBorderlineMatch)
  ).length;
  const autoGroupedCount = entitiesWithMeta.filter(
    (item) => !item.isSingleton && !item.isFlagged && !item.hasBorderlineMatch
  ).length;

  return (
    <div className="results">
      <MatchGraphPreview />
      <div className="stats-summary">
        <span className="stats-flow">
          <strong>{totalRecords}</strong> records → <strong>{totalEntities}</strong> entities
        </span>
        <span className="stats-divider">|</span>
        <span className="stats-detail">
          <strong>{autoGroupedCount}</strong> auto-grouped
        </span>
        <span className="stats-divider">|</span>
        <span className="stats-detail stats-review">
          <strong>{needsReviewCount}</strong> need review
        </span>
      </div>

      {result.warnings.length > 0 && (
        <div className="notes">
          <div className="notes-header">
            <span className="notes-title">⚠ Grouping notes</span>
            <span className="notes-summary">({result.warnings.length} detected)</span>
            <button
              type="button"
              className="notes-toggle"
              onClick={() => setNotesOpen((open) => !open)}
            >
              {notesOpen ? 'Hide details' : 'Show details'}
            </button>
          </div>
          {notesOpen && (
            <ul className="notes-list">
              {result.warnings.map((w, i) => <li key={i}>{formatNote(w)}</li>)}
            </ul>
          )}
        </div>
      )}

      <div className="results-toolbar">
        <span className="results-label">View</span>
        <label className="filter-option">
          <input
            type="radio"
            name="results-view"
            checked={viewMode === 'attention'}
            onChange={() => setViewMode('attention')}
          />
          <span>Groups needing attention</span>
        </label>
        <label className="filter-option">
          <input
            type="radio"
            name="results-view"
            checked={viewMode === 'groups'}
            onChange={() => setViewMode('groups')}
          />
          <span>All groups</span>
        </label>
        <label className="filter-option">
          <input
            type="radio"
            name="results-view"
            checked={viewMode === 'single'}
            onChange={() => setViewMode('single')}
          />
          <span>Single records</span>
        </label>
      </div>

      {viewMode === 'single' && (
        <div className="singleton-note">These records did not strongly match any others.</div>
      )}

      <table className="entities-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Items</th>
            <th>Confidence</th>
            <th>Needs review</th>
          </tr>
        </thead>
        <tbody>
          {visibleEntities.map(({ entity, isFlagged, hasBorderlineMatch }, index) => {
            const needsReview = isFlagged || hasBorderlineMatch;
            const attentionHint = getAttentionHint(isFlagged, hasBorderlineMatch);
            const isAlt = index % 2 === 1;
            return (
              <React.Fragment key={entity.id}>
                <tr
                  onClick={() => setExpandedId(expandedId === entity.id ? null : entity.id)}
                  className={`entity-row ${isFlagged ? 'flagged' : ''} ${isAlt ? 'row-alt' : ''}`}
                >
                  <td>
                    <div className="entity-name">{entity.canonical_name}</div>
                    {needsReview && attentionHint && (
                      <div className="entity-hint">{attentionHint}</div>
                    )}
                  </td>
                  <td>{entity.matched_record_ids.length}</td>
                  <td>
                    <div className="confidence-cell">
                      <span>{Math.round(entity.confidence * 100)}%</span>
                      <div className="confidence-bar">
                        <span
                          className="confidence-fill"
                          style={{ width: `${Math.round(entity.confidence * 100)}%` }}
                        />
                      </div>
                    </div>
                  </td>
                  <td>
                    {needsReview ? (
                      <span className={`flag ${isFlagged ? 'flagged' : 'review'}`}>
                        {isFlagged ? '⚠ Inconsistent group' : 'Borderline match'}
                      </span>
                    ) : (
                      <span className="empty-status">—</span>
                    )}
                  </td>
                </tr>
                {expandedId === entity.id && (
                  <tr>
                    <td colSpan="4">
                      <EntityDetail entity={entity} />
                    </td>
                  </tr>
                )}
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
