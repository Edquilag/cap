import { useEffect, useMemo, useState } from 'react';
import './App.css';
import { PH_REGION_PROVINCES } from './data/phRegionProvinces';

type ZonalValue = {
  id: number;
  rdo_code: string | null;
  region: string | null;
  province: string | null;
  city_municipality: string | null;
  barangay: string | null;
  street_subdivision: string | null;
  property_class: string | null;
  property_type: string | null;
  zonal_value: string | number | null;
  unit: string | null;
  effectivity_date: string | null;
  remarks: string | null;
  source_file: string;
  source_sheet: string;
  source_row: number | null;
  dataset_version: string;
  created_at: string;
};

type PaginatedResult = {
  items: ZonalValue[];
  total: number;
  page: number;
  page_size: number;
};

type FilterOptions = {
  regions: string[];
  provinces: string[];
  cities: string[];
  barangays: string[];
  property_classes: string[];
  property_types: string[];
  dataset_versions: string[];
};

type LocationChildren = {
  cities: string[];
  barangays: string[];
};

type RegionOption = {
  sourceCode: string;
  regionName: string;
  displayName: string;
  label: string;
  provinces: string[];
};

type ProvinceCard = {
  officialName: string;
  queryName: string;
};

type PageView = 'home' | 'province' | 'zonal';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ?? 'http://localhost:8000/api/v1';

function normalizeName(value: string): string {
  return value.replace(/[^a-zA-Z0-9]+/g, ' ').trim().toUpperCase();
}

function formatAmount(value: string | number | null): string {
  if (value === null || value === undefined || value === '') {
    return '-';
  }
  const numericValue = typeof value === 'number' ? value : Number(value);
  if (Number.isNaN(numericValue)) {
    return String(value);
  }
  return `PHP ${numericValue.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function cleanLocationLabel(value: string): string {
  return value.replace(/^[^a-zA-Z0-9]+/, '').replace(/\s+/g, ' ').trim() || value;
}

function formatRegionLabel(regionName: string, displayName: string): string {
  const trimmedRegion = regionName.trim();
  const trimmedDisplay = displayName.trim();
  if (!trimmedDisplay || trimmedDisplay.toUpperCase() === trimmedRegion.toUpperCase()) {
    return trimmedRegion;
  }
  return `${trimmedRegion} - ${trimmedDisplay}`;
}

function getPageViewFromUrl(): PageView {
  const params = new URLSearchParams(window.location.search);
  const viewParam = params.get('view');
  if (viewParam === 'province') {
    return 'province';
  }
  if (viewParam === 'zonal') {
    return 'zonal';
  }
  return 'home';
}

function openNewTab(params: Record<string, string>) {
  const url = new URL(window.location.href);
  url.search = '';
  for (const [key, value] of Object.entries(params)) {
    if (value.trim()) {
      url.searchParams.set(key, value);
    }
  }
  window.open(url.toString(), '_blank', 'noopener,noreferrer');
}

function App() {
  const pageView = useMemo(() => getPageViewFromUrl(), []);
  const searchParams = useMemo(() => new URLSearchParams(window.location.search), []);

  const [filterOptions, setFilterOptions] = useState<FilterOptions>({
    regions: [],
    provinces: [],
    cities: [],
    barangays: [],
    property_classes: [],
    property_types: [],
    dataset_versions: [],
  });

  const [filtersLoading, setFiltersLoading] = useState(true);
  const [filtersError, setFiltersError] = useState<string | null>(null);

  const [regionInput, setRegionInput] = useState(searchParams.get('region') ?? '');
  const [activeRegionCode, setActiveRegionCode] = useState<string | null>(null);

  const [cities, setCities] = useState<string[]>([]);
  const [barangays, setBarangays] = useState<string[]>([]);
  const [cityLoading, setCityLoading] = useState(false);
  const [barangayLoading, setBarangayLoading] = useState(false);
  const [locationError, setLocationError] = useState<string | null>(null);
  const [selectedCity, setSelectedCity] = useState('');

  const [results, setResults] = useState<PaginatedResult>({
    items: [],
    total: 0,
    page: 1,
    page_size: 25,
  });
  const [recordsLoading, setRecordsLoading] = useState(false);
  const [recordsError, setRecordsError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [selectedRecord, setSelectedRecord] = useState<ZonalValue | null>(null);

  const provinceFromUrl = searchParams.get('province') ?? '';
  const regionFromUrl = searchParams.get('region') ?? '';
  const provinceLabelFromUrl = searchParams.get('province_label') ?? provinceFromUrl;
  const cityFromUrl = searchParams.get('city') ?? '';
  const barangayFromUrl = searchParams.get('barangay') ?? '';

  const regionOptions = useMemo<RegionOption[]>(
    () =>
      PH_REGION_PROVINCES.map((entry) => ({
        ...entry,
        label: formatRegionLabel(entry.regionName, entry.displayName),
      })).sort((a, b) => a.label.localeCompare(b.label)),
    []
  );

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_BASE_URL}/zonal-values/filters`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Filter request failed (${response.status})`);
        }
        return (await response.json()) as FilterOptions;
      })
      .then((payload) => {
        setFilterOptions(payload);
        setFiltersError(null);
      })
      .catch((fetchError: Error) => {
        if (fetchError.name !== 'AbortError') {
          setFiltersError(fetchError.message);
        }
      })
      .finally(() => setFiltersLoading(false));

    return () => controller.abort();
  }, []);

  const normalizedDatasetProvinces = useMemo(
    () =>
      filterOptions.provinces.map((province) => ({
        raw: province,
        norm: normalizeName(province),
      })),
    [filterOptions.provinces]
  );

  const resolveProvinceForQuery = (officialProvince: string): string | null => {
    const target = normalizeName(officialProvince);
    if (!target) {
      return null;
    }

    const exact = normalizedDatasetProvinces.find((item) => item.norm === target);
    if (exact) {
      return exact.raw;
    }

    const fuzzy = normalizedDatasetProvinces.find((item) => item.norm.includes(target) || target.includes(item.norm));
    if (fuzzy) {
      return fuzzy.raw;
    }

    return null;
  };

  const selectedRegion = useMemo(() => {
    const exactInput = regionInput.trim().toLowerCase();
    if (exactInput) {
      const match = regionOptions.find((option) => option.label.toLowerCase() === exactInput);
      if (match) {
        return match;
      }
    }
    if (activeRegionCode) {
      return regionOptions.find((option) => option.sourceCode === activeRegionCode) ?? null;
    }
    return null;
  }, [activeRegionCode, regionInput, regionOptions]);

  const provinceCards = useMemo<ProvinceCard[]>(() => {
    if (!selectedRegion) {
      return [];
    }

    const cards: ProvinceCard[] = selectedRegion.provinces
      .map((officialName) => {
        const queryName = resolveProvinceForQuery(officialName);
        if (!queryName) {
          return null;
        }
        return {
          officialName,
          queryName,
        };
      })
      .filter((card): card is ProvinceCard => Boolean(card));

    if (cards.length > 0) {
      return cards;
    }

    if (selectedRegion.regionName.toUpperCase().includes('NATIONAL CAPITAL REGION')) {
      const ncrLike = normalizedDatasetProvinces
        .filter((item) => item.norm.includes('NCR') || item.norm.includes('MANILA'))
        .map((item) => item.raw);
      return Array.from(new Set(ncrLike)).map((province) => ({
        officialName: province,
        queryName: province,
      }));
    }

    return [];
  }, [selectedRegion, normalizedDatasetProvinces]);

  useEffect(() => {
    if (pageView !== 'province' || !provinceFromUrl) {
      return;
    }

    const controller = new AbortController();
    setCityLoading(true);
    setLocationError(null);

    fetch(`${API_BASE_URL}/zonal-values/location-children?province=${encodeURIComponent(provinceFromUrl)}`, {
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Location request failed (${response.status})`);
        }
        return (await response.json()) as LocationChildren;
      })
      .then((payload) => {
        setCities(payload.cities);
      })
      .catch((fetchError: Error) => {
        if (fetchError.name !== 'AbortError') {
          setLocationError(fetchError.message);
        }
      })
      .finally(() => setCityLoading(false));

    return () => controller.abort();
  }, [pageView, provinceFromUrl]);

  useEffect(() => {
    if (pageView !== 'province' || !provinceFromUrl || !selectedCity) {
      setBarangays([]);
      return;
    }

    const controller = new AbortController();
    setBarangayLoading(true);
    setLocationError(null);

    const query = new URLSearchParams({
      province: provinceFromUrl,
      city: selectedCity,
      limit: '5000',
    });
    fetch(`${API_BASE_URL}/zonal-values/location-children?${query.toString()}`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Barangay request failed (${response.status})`);
        }
        return (await response.json()) as LocationChildren;
      })
      .then((payload) => {
        setBarangays(payload.barangays);
      })
      .catch((fetchError: Error) => {
        if (fetchError.name !== 'AbortError') {
          setLocationError(fetchError.message);
        }
      })
      .finally(() => setBarangayLoading(false));

    return () => controller.abort();
  }, [pageView, provinceFromUrl, selectedCity]);

  useEffect(() => {
    if (pageView !== 'zonal' || !provinceFromUrl || !cityFromUrl || !barangayFromUrl) {
      return;
    }

    const controller = new AbortController();
    setRecordsLoading(true);
    setRecordsError(null);

    const query = new URLSearchParams({
      province: provinceFromUrl,
      city: cityFromUrl,
      barangay: barangayFromUrl,
      page: String(page),
      page_size: String(pageSize),
    });

    fetch(`${API_BASE_URL}/zonal-values?${query.toString()}`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Record request failed (${response.status})`);
        }
        return (await response.json()) as PaginatedResult;
      })
      .then((payload) => {
        setResults(payload);
        setSelectedRecord((current) => {
          if (!current) {
            return current;
          }
          return payload.items.find((item) => item.id === current.id) ?? null;
        });
      })
      .catch((fetchError: Error) => {
        if (fetchError.name !== 'AbortError') {
          setRecordsError(fetchError.message);
        }
      })
      .finally(() => setRecordsLoading(false));

    return () => controller.abort();
  }, [barangayFromUrl, cityFromUrl, page, pageSize, pageView, provinceFromUrl]);

  const pageCount = useMemo(() => Math.max(1, Math.ceil(results.total / pageSize)), [results.total, pageSize]);

  const confirmRegion = () => {
    const normalizedInput = regionInput.trim().toLowerCase();
    const match = regionOptions.find((option) => option.label.toLowerCase() === normalizedInput);
    if (!match) {
      setFiltersError('Choose a region from the dropdown list.');
      return;
    }
    setActiveRegionCode(match.sourceCode);
    setFiltersError(null);
  };

  const clearRegion = () => {
    setActiveRegionCode(null);
    setRegionInput('');
    setFiltersError(null);
  };

  const openProvinceTab = (regionLabel: string, province: ProvinceCard) => {
    openNewTab({
      view: 'province',
      region: regionLabel,
      province: province.queryName,
      province_label: province.officialName,
    });
  };

  const openZonalTab = (barangay: string) => {
    if (!provinceFromUrl || !selectedCity) {
      return;
    }
    openNewTab({
      view: 'zonal',
      region: regionFromUrl,
      province: provinceFromUrl,
      province_label: provinceLabelFromUrl,
      city: selectedCity,
      barangay,
    });
  };

  if (pageView === 'province') {
    return (
      <div className="app-shell">
        <header className="topbar">
          <div className="topbar__content">
            <p className="topbar__eyebrow">Province Explorer</p>
            <h1>{provinceLabelFromUrl || 'Province'}</h1>
            <p className="topbar__subtitle">{regionFromUrl ? `Region: ${regionFromUrl}` : 'Select city then barangay.'}</p>
          </div>
        </header>

        <main className="workspace">
          {locationError && <p className="error-banner">{locationError}</p>}

          <section className="panel split-panel">
            <div className="split-panel__column">
              <h2>City / Municipality</h2>
              <p>Click a city to load barangay cards.</p>
              {cityLoading ? (
                <p className="hint">Loading cities...</p>
              ) : cities.length === 0 ? (
                <p className="hint">No city records found for this province.</p>
              ) : (
                <div className="card-grid">
                  {cities.map((city) => (
                    <button
                      key={city}
                      type="button"
                      className={`entity-card ${selectedCity === city ? 'entity-card--active' : ''}`}
                      onClick={() => setSelectedCity(city)}
                    >
                      {cleanLocationLabel(city)}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="split-panel__column">
              <h2>Barangay Cards</h2>
              <p>Click a barangay card to open the zonal value page in a new tab.</p>
              {!selectedCity ? (
                <p className="hint">Select a city first.</p>
              ) : barangayLoading ? (
                <p className="hint">Loading barangays...</p>
              ) : barangays.length === 0 ? (
                <p className="hint">No barangay records found for {cleanLocationLabel(selectedCity)}.</p>
              ) : (
                <div className="card-grid">
                  {barangays.map((barangay) => (
                    <button key={barangay} type="button" className="entity-card" onClick={() => openZonalTab(barangay)}>
                      {cleanLocationLabel(barangay)}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </section>
        </main>
      </div>
    );
  }

  if (pageView === 'zonal') {
    return (
      <div className="app-shell">
        <header className="topbar">
          <div className="topbar__content">
            <p className="topbar__eyebrow">Zonal Values</p>
            <h1>{cleanLocationLabel(barangayFromUrl || 'Barangay')}</h1>
            <p className="topbar__subtitle">
              {cleanLocationLabel(provinceLabelFromUrl)} / {cleanLocationLabel(cityFromUrl)} / {cleanLocationLabel(barangayFromUrl)}
            </p>
          </div>
        </header>

        <main className="workspace">
          {recordsError && <p className="error-banner">{recordsError}</p>}

          <section className="panel records-panel">
            <div className="records-header">
              <div>
                <h2>Zonal Value Records</h2>
                <p>{recordsLoading ? 'Loading...' : `${results.total.toLocaleString()} records`}</p>
              </div>
              <label className="compact-input">
                Rows
                <select
                  value={pageSize}
                  onChange={(event) => {
                    setPageSize(Number(event.target.value));
                    setPage(1);
                  }}
                >
                  <option value={25}>25</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                </select>
              </label>
            </div>

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Street/Subdivision</th>
                    <th>Class</th>
                    <th>Type</th>
                    <th>Zonal Value</th>
                    <th>RDO</th>
                  </tr>
                </thead>
                <tbody>
                  {results.items.length === 0 && !recordsLoading ? (
                    <tr>
                      <td colSpan={5} className="empty-cell">
                        No zonal values found.
                      </td>
                    </tr>
                  ) : (
                    results.items.map((row) => (
                      <tr
                        key={row.id}
                        onClick={() => setSelectedRecord(row)}
                        className={selectedRecord?.id === row.id ? 'is-active' : ''}
                      >
                        <td>{row.street_subdivision ?? '-'}</td>
                        <td>{row.property_class ?? '-'}</td>
                        <td>{row.property_type ?? '-'}</td>
                        <td>{formatAmount(row.zonal_value)}</td>
                        <td>{row.rdo_code ?? '-'}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div className="pagination">
              <button
                className="button button--secondary"
                disabled={page <= 1}
                onClick={() => setPage((currentPage) => Math.max(1, currentPage - 1))}
              >
                Previous
              </button>
              <span>
                Page {page} of {pageCount}
              </span>
              <button
                className="button button--secondary"
                disabled={page >= pageCount}
                onClick={() => setPage((currentPage) => Math.min(pageCount, currentPage + 1))}
              >
                Next
              </button>
            </div>
          </section>

          <section className="panel details-panel">
            <h2>Details</h2>
            {selectedRecord ? (
              <dl className="detail-grid">
                <dt>Region</dt>
                <dd>{selectedRecord.region ?? '-'}</dd>
                <dt>Province</dt>
                <dd>{selectedRecord.province ?? '-'}</dd>
                <dt>City/Municipality</dt>
                <dd>{selectedRecord.city_municipality ?? '-'}</dd>
                <dt>Barangay</dt>
                <dd>{selectedRecord.barangay ?? '-'}</dd>
                <dt>Street/Subdivision</dt>
                <dd>{selectedRecord.street_subdivision ?? '-'}</dd>
                <dt>Zonal Value</dt>
                <dd>{formatAmount(selectedRecord.zonal_value)}</dd>
                <dt>Unit</dt>
                <dd>{selectedRecord.unit ?? '-'}</dd>
                <dt>Source</dt>
                <dd>
                  {selectedRecord.source_file} | {selectedRecord.source_sheet} | row {selectedRecord.source_row ?? '-'}
                </dd>
                <dt>Remarks</dt>
                <dd>{selectedRecord.remarks ?? '-'}</dd>
              </dl>
            ) : (
              <p className="hint">Select a row to inspect full record details.</p>
            )}
          </section>
        </main>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar__content">
          <p className="topbar__eyebrow">Region Selector</p>
          <h1>ZonalHub</h1>
          <p className="topbar__subtitle">
            Select a Philippine region from the dropdown, then click a province card to open the city and barangay explorer.
          </p>
        </div>
      </header>

      <main className="workspace">
        <section className="panel region-panel">
          <h2>1. Region Dropdown</h2>
          <p>Search the official region list, then confirm.</p>

          <label>
            Region (searchable dropdown)
            <input
              list="region-options"
              value={regionInput}
              onChange={(event) => setRegionInput(event.target.value)}
              placeholder="e.g. Region IV-A - CALABARZON"
              disabled={filtersLoading}
            />
            <datalist id="region-options">
              {regionOptions.map((option) => (
                <option key={option.sourceCode} value={option.label} />
              ))}
            </datalist>
          </label>

          <div className="region-actions">
            <button type="button" className="button button--primary" onClick={confirmRegion} disabled={filtersLoading}>
              Confirm Region
            </button>
            <button type="button" className="button button--secondary" onClick={clearRegion}>
              Clear
            </button>
          </div>

          {filtersError && <p className="error-banner">{filtersError}</p>}
        </section>

        <section className="panel province-panel">
          <h2>2. Province Cards</h2>
          <p>Click a province to open the next page in a new tab.</p>

          {!selectedRegion ? (
            <p className="hint">No region confirmed yet.</p>
          ) : provinceCards.length === 0 ? (
            <p className="hint">No province records matched this region in the current dataset.</p>
          ) : (
            <div className="card-grid">
              {provinceCards.map((province) => (
                <button
                  key={`${province.officialName}|${province.queryName}`}
                  type="button"
                  className="entity-card"
                  onClick={() => openProvinceTab(selectedRegion.label, province)}
                >
                  <span>{province.officialName}</span>
                  <small>Open city/barangay view</small>
                </button>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
