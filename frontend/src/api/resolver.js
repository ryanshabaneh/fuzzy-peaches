const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 120_000);

  let response;
  try {
    response = await fetch(`${API_BASE}/resolve`, {
      method: 'POST',
      body: formData,
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timeoutId);
  }

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Resolution failed');
  }

  return response.json();
}

/**
 * One-click demo datasets
 */
export function getSampleData(type = 'music') {
  if (type === 'companies') {
    const csv = `id,name,industry
1,Apple Inc.,Technology
2,APPLE INC,Technology
3,Apple Incorporated,Technology
4,Microsoft Corporation,Technology
5,MICROSOFT CORP,Technology
6,Microsoft Corp.,Technology
7,Amazon.com Inc,E-commerce
8,Amazon Inc.,E-commerce
9,AMAZON.COM INC.,E-commerce
10,Meta Platforms Inc,Technology
11,Meta Platforms,Technology
12,META PLATFORMS INC.,Technology
13,Alphabet Inc,Technology
14,ALPHABET INC.,Technology
15,Alphabet Incorporated,Technology
16,Tesla Inc,Automotive
17,TESLA INC.,Automotive
18,Tesla Motors Inc,Automotive
19,Meta Platforms Group Inc,Technology
20,Alphabet Corporation,Technology
21,Amazon.com Group Inc,E-commerce`;

    const blob = new Blob([csv], { type: 'text/csv' });
    return new File([blob], 'sample_company_data.csv', { type: 'text/csv' });
  }

  const csv = `id,title,artist
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

  const blob = new Blob([csv], { type: 'text/csv' });
  return new File([blob], 'sample_music_data.csv', { type: 'text/csv' });
}
