const API_BASE = 'http://localhost:8000';

export async function getDefaultConfig() {
  const response = await fetch(`${API_BASE}/config/default`);
  if (!response.ok) {
    throw new Error('Failed to fetch default config');
  }
  return response.json();
}

export async function resolveEntities(file, config, columnMapping) {
  const formData = new FormData();
  formData.append('file', file);

  if (config) {
    formData.append('config_json', JSON.stringify(config));
  }

  if (columnMapping) {
    formData.append('column_mapping_json', JSON.stringify(columnMapping));
  }

  const response = await fetch(`${API_BASE}/resolve`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Resolution failed');
  }

  return response.json();
}

/**
 * One-click demo dataset
 */
export function getSampleData() {
  const sampleCSV = `id,title,artist
1,No Other Heart,Mac DeMarco
2,No Other Heart - Mac DeMarco,Mac DeMarco
3,NO OTHER HEART (Demo),Mac DeMarco
4,Look On Down From The Bridge,Mazzy Star
5,LOOK ON DOWN FROM THE BRIDGE (Edit),Mazzy Star
6,When the Sun Hits,Slowdive
7,When the Sun Hits (Live),Slowdive
8,Come As You Are,Nirvana
9,Come As You Are - Nirvana,Nirvana
10,Just Like Heaven,The Cure
11,Just Like Heaven (Remix),The Cure
12,Bitter Sweet Symphony,The Verve
13,Bitter Sweet Symphony (Remix),The Verve
14,Symphony,The Verve
15,Come Back,Five Stairsteps
16,Come Back Again,Five Stairsteps
17,Come Back Again,The Weeknd`;

  const blob = new Blob([sampleCSV], { type: 'text/csv' });
  return new File([blob], 'sample_music_data.csv', { type: 'text/csv' });
}
