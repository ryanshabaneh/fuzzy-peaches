import { useRef, useState } from 'react';

export default function FileUpload({
  config,
  onConfigChange,
  onSubmit,
  onLoadSample,
  isLoading,
  error = null
}) {
  const [file, setFile] = useState(null);
  const [textColumn, setTextColumn] = useState('title');
  const [isDragOver, setIsDragOver] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [sampleType, setSampleType] = useState('music');
  const fileInputRef = useRef(null);

  const highThreshold = config?.thresholds?.high_confidence ?? 0.85;
  const lowThreshold = config?.thresholds?.low_confidence ?? 0.7;

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) setFile(droppedFile);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!file) return;

    const columnMapping = { id: 'id', text: textColumn };
    if (sampleType === 'music') {
      columnMapping.artist = 'artist';
    }

    onSubmit(file, config, columnMapping);
  };

  const updateHighThreshold = (value) => {
    const high = parseFloat(value);
    if (config.thresholds.low_confidence > high) return;

    onConfigChange({
      ...config,
      thresholds: {
        ...config.thresholds,
        high_confidence: high
      }
    });
  };

  const updateLowThreshold = (value) => {
    const low = parseFloat(value);
    if (low > config.thresholds.high_confidence) return;

    onConfigChange({
      ...config,
      thresholds: {
        ...config.thresholds,
        low_confidence: low
      }
    });
  };

  return (
    <div className="card upload-section">
      <div className="card-header">
        <h1 className="app-title">Fuzzy Peaches</h1>
        <p className="app-tagline">Automatically group messy records into clean entities.</p>
      </div>

      {error && <div className="error-message">{error}</div>}

      <h2 className="section-title">Upload data</h2>

      <form onSubmit={handleSubmit}>
        <div
          className={`dropzone ${isDragOver ? 'drag-over' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.json"
            className="hidden-input"
            onChange={(e) => setFile(e.target.files[0])}
            disabled={isLoading}
          />
          <div className="dropzone-icon">
            <svg
              className="dropzone-illustration"
              width="40"
              height="44"
              viewBox="0 0 20 22"
              fill="none"
              aria-hidden="true"
            >
              {/* Stem */}
              <rect x="10" y="0" width="2" height="3" fill="#6b5d54" />
              <rect x="12" y="1" width="2" height="2" fill="#7bc9a4" />
              <rect x="14" y="2" width="2" height="2" fill="#7bc9a4" />
              {/* Peach body */}
              <rect x="6" y="4" width="8" height="2" fill="#f5a88a" />
              <rect x="4" y="6" width="12" height="2" fill="#f5a88a" />
              <rect x="2" y="8" width="16" height="2" fill="#f5a88a" />
              <rect x="2" y="10" width="16" height="2" fill="#f08b6d" />
              <rect x="2" y="12" width="16" height="2" fill="#f08b6d" />
              <rect x="2" y="14" width="16" height="2" fill="#e87a5a" />
              <rect x="4" y="16" width="12" height="2" fill="#e87a5a" />
              <rect x="6" y="18" width="8" height="2" fill="#d96a4a" />
              {/* Highlight */}
              <rect x="6" y="6" width="2" height="2" fill="#fcd5c5" />
              <rect x="6" y="8" width="2" height="2" fill="#fcd5c5" />
            </svg>
          </div>
          <div className="dropzone-text">
            {file ? file.name : 'Upload a CSV or JSON to begin'}
          </div>
          {!file && <div className="dropzone-hint">or click to browse</div>}
        </div>

        <div className="sample-row">
          <select
            className="form-input sample-select"
            value={sampleType}
            onChange={(e) => setSampleType(e.target.value)}
            disabled={isLoading}
          >
            <option value="music">Music</option>
            <option value="companies">Companies</option>
          </select>
          <button
            type="button"
            className="btn btn-secondary sample-btn"
            onClick={() => {
              setFile(onLoadSample(sampleType));
              setTextColumn(sampleType === 'companies' ? 'name' : 'title');
            }}
            disabled={isLoading}
          >
            Load sample dataset
          </button>
        </div>
        <button
          type="submit"
          className="btn btn-primary btn-full"
          disabled={!file || isLoading}
        >
          {isLoading ? (
            <>
              Processing <span className="dots" aria-hidden="true">...</span>
            </>
          ) : (
            'Find Matches'
          )}
        </button>

        <button
          type="button"
          className="advanced-toggle"
          onClick={() => setShowAdvanced((current) => !current)}
        >
          Advanced options <span className={`chevron ${showAdvanced ? 'open' : ''}`}>▾</span>
        </button>

        {showAdvanced && (
          <div className="advanced-panel">
            <div className="form-group">
              <label className="form-label">Field to compare</label>
              <input
                className="form-input"
                value={textColumn}
                onChange={(e) => setTextColumn(e.target.value)}
              />
              <p className="helper-text">e.g. title, name, description</p>
            </div>

            <div className="form-group">
              <label className="form-label">
                Auto-group if score ≥ {highThreshold.toFixed(2)}
              </label>
              <input
                type="range"
                min="0.5"
                max="1.0"
                step="0.05"
                value={highThreshold}
                onChange={(e) => updateHighThreshold(e.target.value)}
              />
              <p className="slider-help">Automatically grouped as the same entity</p>
            </div>

            <div className="form-group">
              <label className="form-label">
                Flag for review if {lowThreshold.toFixed(2)}–{highThreshold.toFixed(2)}
              </label>
              <input
                type="range"
                min="0.3"
                max={highThreshold}
                step="0.05"
                value={lowThreshold}
                onChange={(e) => updateLowThreshold(e.target.value)}
              />
              <p className="slider-help">Worth a second look</p>
            </div>

            <div className="form-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={config?.blocking?.enabled || false}
                  onChange={(e) => onConfigChange({
                    ...config,
                    blocking: {
                      ...config?.blocking,
                      enabled: e.target.checked
                    }
                  })}
                  disabled={isLoading}
                />
                Enable blocking (faster for large datasets)
              </label>
              <p className="form-hint">
                Reduces comparisons by only matching records that share common attributes.
                Recommended for datasets over 1,000 records.
              </p>
            </div>
          </div>
        )}
      </form>
    </div>
  );
}
