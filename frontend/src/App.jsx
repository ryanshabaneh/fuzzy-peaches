import { useEffect, useState } from 'react';
import { getDefaultConfig, resolveEntities, getSampleData } from './api/resolver';
import FileUpload from './components/FileUpload';
import ResultsTable from './components/ResultsTable';
import './App.css';

export default function App() {
  const [config, setConfig] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    getDefaultConfig()
      .then(setConfig)
      .catch(err => setError(err.message));
  }, []);

  const handleSubmit = async (file, config, columnMapping) => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await resolveEntities(file, config, columnMapping);
      setResult(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!config) return <div className="app">Loading...</div>;

  return (
    <div className="app">
      <main className="main-content">
        <FileUpload
          config={config}
          onConfigChange={setConfig}
          onSubmit={handleSubmit}
          onLoadSample={getSampleData}
          isLoading={loading}
          error={error}
        />

        {result && (
          <div className="card results-card">
            <ResultsTable result={result} />
          </div>
        )}
      </main>
    </div>
  );
}
