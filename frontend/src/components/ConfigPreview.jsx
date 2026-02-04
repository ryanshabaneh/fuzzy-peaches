
export default function ConfigPreview({
  config,
  title = "Matching Behavior",
  subtitle = "Adjust how strictly records must match to be grouped together.",
  onConfigChange = null
}) {
  if (!config) return null;

  return (
    <div className="config-preview">
      <h3>{title}</h3>
      {subtitle && <p className="config-subtitle">{subtitle}</p>}
      <div className="config-section">
        <h4>How records are compared</h4>
        <ul>
          <li>
            Shared words (titles with the same terms)
          </li>
          <li>
            Spelling similarity (handles typos & formatting)
          </li>
          <li>
            Exact matches (same artist, ID, or field)
          </li>
          <li>
            Name length balance
          </li>
        </ul>
      </div>
      <div className="config-section">
        <h4>Confidence Rules</h4>
        <ul>
          <li>
            Auto-group when confidence ≥{" "}
            <span className="config-value">{config.thresholds.high_confidence.toFixed(2)}</span>
          </li>
          <li>
            Flag for review when confidence ≥{" "}
            <span className="config-value">{config.thresholds.low_confidence.toFixed(2)}</span>
          </li>
        </ul>
      </div>
      <div className="config-section">
        <h4>Advanced Optimization</h4>
        <p className="config-subtitle">Speeds up processing on large datasets by limiting comparisons to likely matches.</p>
        {onConfigChange ? (
          <label className="toggle">
            <input
              type="checkbox"
              checked={config.blocking.enabled}
              onChange={() =>
                onConfigChange({
                  ...config,
                  blocking: {
                    ...config.blocking,
                    enabled: !config.blocking.enabled
                  }
                })
              }
            />
            <span>Enable advanced optimization for large datasets</span>
          </label>
        ) : (
          <p className="config-note">Optimized automatically for performance.</p>
        )}
      </div>
    </div>
  );
}
