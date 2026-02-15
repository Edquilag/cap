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

type PropertyClassMixItem = {
  property_class: string;
  count: number;
};

type ZonalSummary = {
  total_records: number;
  min_value: string | number | null;
  max_value: string | number | null;
  median_value: string | number | null;
  catch_all_records: number;
  exact_street_records: number;
  class_mix: PropertyClassMixItem[];
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

type PageView = 'home' | 'province' | 'barangay' | 'zonal';
type PrecisionBadge = 'Exact' | 'Catch-all' | 'Special case';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ?? 'http://localhost:8000/api/v1';

function normalizeName(value: string): string {
  return value.replace(/[^a-zA-Z0-9]+/g, ' ').trim().toUpperCase();
}

function normalizeStreet(value: string | null | undefined): string {
  return (value ?? '')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
}

function isCatchAllStreet(street: string | null | undefined): boolean {
  return /all\s+other\s+street/i.test(street ?? '');
}

function isSpecialCaseRow(record: ZonalValue): boolean {
  const notes = `${record.street_subdivision ?? ''} ${record.remarks ?? ''}`.toUpperCase();
  return /\*{1,4}/.test(notes) || notes.includes('OCULAR') || notes.includes('NOT EXISTING');
}

function getPrecisionBadge(record: ZonalValue): PrecisionBadge {
  if (isCatchAllStreet(record.street_subdivision)) {
    return 'Catch-all';
  }
  if (isSpecialCaseRow(record)) {
    return 'Special case';
  }
  return 'Exact';
}

function getWhyThisAppears(record: ZonalValue, streetQuery: string): string {
  const normalizedQuery = normalizeStreet(streetQuery);
  const normalizedStreet = normalizeStreet(record.street_subdivision);
  const catchAll = isCatchAllStreet(record.street_subdivision);

  if (normalizedQuery) {
    if (normalizedStreet === normalizedQuery && !catchAll) {
      return 'This row is ranked first because the street/subdivision exactly matches your street query.';
    }
    if (normalizedStreet.includes(normalizedQuery) && !catchAll) {
      return 'This row is included because the street/subdivision contains your street query and is prioritized over catch-all rows.';
    }
    if (catchAll) {
      return 'This catch-all row appears only as fallback when no named street row matches your query in the same barangay, property class, and dataset version.';
    }
  }

  if (catchAll) {
    return 'This is an official catch-all entry from source files. Use it when no specific named street applies.';
  }

  if (isSpecialCaseRow(record)) {
    return 'This row includes source footnote markers or special remarks (for example ocular/placeholder notes).';
  }

  return 'This row matches your selected location and dataset filters.';
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

function toNumber(value: string | number | null): number | null {
  if (value === null || value === undefined || value === '') {
    return null;
  }
  const numeric = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(numeric) ? numeric : null;
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
  if (viewParam === 'barangay') {
    return 'barangay';
  }
  if (viewParam === 'zonal') {
    return 'zonal';
  }
  return 'home';
}

function navigateToPage(params: Record<string, string>) {
  const url = new URL(window.location.href);
  url.search = '';
  for (const [key, value] of Object.entries(params)) {
    if (value.trim()) {
      url.searchParams.set(key, value);
    }
  }
  window.location.assign(url.toString());
}

function buildZonalQuery(params: {
  province: string;
  city: string;
  barangay: string;
  page?: number;
  pageSize?: number;
  datasetVersion?: string;
  street?: string;
}): URLSearchParams {
  const query = new URLSearchParams({
    province: params.province,
    city: params.city,
    barangay: params.barangay,
  });
  if (params.page !== undefined) {
    query.set('page', String(params.page));
  }
  if (params.pageSize !== undefined) {
    query.set('page_size', String(params.pageSize));
  }
  const trimmedDataset = params.datasetVersion?.trim() ?? '';
  if (trimmedDataset) {
    query.set('dataset_version', trimmedDataset);
  }
  const trimmedStreet = params.street?.trim() ?? '';
  if (trimmedStreet) {
    query.set('street', trimmedStreet);
  }
  return query;
}

function getFilenameFromDisposition(disposition: string | null, fallback: string): string {
  if (!disposition) {
    return fallback;
  }
  const match = disposition.match(/filename="?([^"]+)"?/i);
  return match?.[1] ?? fallback;
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

  const [streetInput, setStreetInput] = useState(searchParams.get('street') ?? '');
  const [streetQuery, setStreetQuery] = useState(searchParams.get('street') ?? '');
  const [selectedDatasetVersion, setSelectedDatasetVersion] = useState(searchParams.get('dataset_version') ?? '');
  const [compareDatasetVersion, setCompareDatasetVersion] = useState(searchParams.get('compare_dataset_version') ?? '');

  const [summary, setSummary] = useState<ZonalSummary | null>(null);
  const [compareSummary, setCompareSummary] = useState<ZonalSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [exportingFormat, setExportingFormat] = useState<'csv' | 'xlsx' | null>(null);
  const [exportInfo, setExportInfo] = useState<string | null>(null);

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

  const datasetVersionOptions = useMemo(
    () => [...filterOptions.dataset_versions].sort((a, b) => b.localeCompare(a)),
    [filterOptions.dataset_versions]
  );

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
    if (pageView !== 'barangay' || !provinceFromUrl || !cityFromUrl) {
      setBarangays([]);
      return;
    }

    const controller = new AbortController();
    setBarangayLoading(true);
    setLocationError(null);

    const query = new URLSearchParams({
      province: provinceFromUrl,
      city: cityFromUrl,
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
  }, [cityFromUrl, pageView, provinceFromUrl]);

  useEffect(() => {
    if (pageView !== 'zonal' || !provinceFromUrl || !cityFromUrl || !barangayFromUrl) {
      return;
    }

    const controller = new AbortController();
    setRecordsLoading(true);
    setRecordsError(null);

    const query = buildZonalQuery({
      province: provinceFromUrl,
      city: cityFromUrl,
      barangay: barangayFromUrl,
      page,
      pageSize,
      datasetVersion: selectedDatasetVersion,
      street: streetQuery,
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
  }, [barangayFromUrl, cityFromUrl, page, pageSize, pageView, provinceFromUrl, selectedDatasetVersion, streetQuery]);

  useEffect(() => {
    if (pageView !== 'zonal' || !provinceFromUrl || !cityFromUrl || !barangayFromUrl) {
      setSummary(null);
      setCompareSummary(null);
      return;
    }

    const controller = new AbortController();
    setSummaryLoading(true);
    setSummaryError(null);

    const baseSummaryQuery = buildZonalQuery({
      province: provinceFromUrl,
      city: cityFromUrl,
      barangay: barangayFromUrl,
      datasetVersion: selectedDatasetVersion,
      street: streetQuery,
    });

    const activeSummaryRequest = fetch(`${API_BASE_URL}/zonal-values/summary?${baseSummaryQuery.toString()}`, {
      signal: controller.signal,
    }).then(async (response) => {
      if (!response.ok) {
        throw new Error(`Summary request failed (${response.status})`);
      }
      return (await response.json()) as ZonalSummary;
    });

    const compareRequest =
      compareDatasetVersion && compareDatasetVersion !== selectedDatasetVersion
        ? fetch(
            `${API_BASE_URL}/zonal-values/summary?${buildZonalQuery({
              province: provinceFromUrl,
              city: cityFromUrl,
              barangay: barangayFromUrl,
              datasetVersion: compareDatasetVersion,
              street: streetQuery,
            }).toString()}`,
            { signal: controller.signal }
          ).then(async (response) => {
            if (!response.ok) {
              throw new Error(`Comparison request failed (${response.status})`);
            }
            return (await response.json()) as ZonalSummary;
          })
        : Promise.resolve<ZonalSummary | null>(null);

    Promise.all([activeSummaryRequest, compareRequest])
      .then(([activeSummary, comparePayload]) => {
        setSummary(activeSummary);
        setCompareSummary(comparePayload);
      })
      .catch((fetchError: Error) => {
        if (fetchError.name !== 'AbortError') {
          setSummaryError(fetchError.message);
        }
      })
      .finally(() => setSummaryLoading(false));

    return () => controller.abort();
  }, [
    barangayFromUrl,
    cityFromUrl,
    compareDatasetVersion,
    pageView,
    provinceFromUrl,
    selectedDatasetVersion,
    streetQuery,
  ]);

  useEffect(() => {
    if (pageView !== 'zonal') {
      return;
    }
    const url = new URL(window.location.href);
    if (selectedDatasetVersion.trim()) {
      url.searchParams.set('dataset_version', selectedDatasetVersion.trim());
    } else {
      url.searchParams.delete('dataset_version');
    }
    if (streetQuery.trim()) {
      url.searchParams.set('street', streetQuery.trim());
    } else {
      url.searchParams.delete('street');
    }
    if (compareDatasetVersion.trim()) {
      url.searchParams.set('compare_dataset_version', compareDatasetVersion.trim());
    } else {
      url.searchParams.delete('compare_dataset_version');
    }
    window.history.replaceState({}, '', url.toString());
  }, [compareDatasetVersion, pageView, selectedDatasetVersion, streetQuery]);

  useEffect(() => {
    if (!selectedRecord) {
      return;
    }
    const onEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setSelectedRecord(null);
      }
    };
    window.addEventListener('keydown', onEscape);
    return () => window.removeEventListener('keydown', onEscape);
  }, [selectedRecord]);

  useEffect(() => {
    if (!selectedRecord) {
      return;
    }
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [selectedRecord]);

  const pageCount = useMemo(() => Math.max(1, Math.ceil(results.total / pageSize)), [results.total, pageSize]);

  const summaryMedianDelta = useMemo(() => {
    if (!summary || !compareSummary) {
      return null;
    }
    const currentMedian = toNumber(summary.median_value);
    const previousMedian = toNumber(compareSummary.median_value);
    if (currentMedian === null || previousMedian === null) {
      return null;
    }
    return currentMedian - previousMedian;
  }, [compareSummary, summary]);

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

  const openProvincePage = (regionLabel: string, province: ProvinceCard) => {
    navigateToPage({
      view: 'province',
      region: regionLabel,
      province: province.queryName,
      province_label: province.officialName,
    });
  };

  const openBarangayPage = (city: string) => {
    if (!provinceFromUrl) {
      return;
    }
    navigateToPage({
      view: 'barangay',
      region: regionFromUrl,
      province: provinceFromUrl,
      province_label: provinceLabelFromUrl,
      city,
    });
  };

  const openZonalPage = (barangay: string) => {
    if (!provinceFromUrl || !cityFromUrl) {
      return;
    }
    navigateToPage({
      view: 'zonal',
      region: regionFromUrl,
      province: provinceFromUrl,
      province_label: provinceLabelFromUrl,
      city: cityFromUrl,
      barangay,
    });
  };

  const applyStreetFilter = () => {
    setStreetQuery(streetInput.trim());
    setPage(1);
  };

  const clearStreetFilter = () => {
    setStreetInput('');
    setStreetQuery('');
    setPage(1);
  };

  const handleDatasetChange = (datasetVersion: string) => {
    setSelectedDatasetVersion(datasetVersion);
    if (compareDatasetVersion === datasetVersion) {
      setCompareDatasetVersion('');
    }
    setPage(1);
  };

  const handleCompareChange = (datasetVersion: string) => {
    if (datasetVersion === selectedDatasetVersion) {
      setCompareDatasetVersion('');
      return;
    }
    setCompareDatasetVersion(datasetVersion);
  };

  const exportRecords = async (format: 'csv' | 'xlsx') => {
    if (!provinceFromUrl || !cityFromUrl || !barangayFromUrl) {
      return;
    }
    try {
      setExportingFormat(format);
      setExportInfo(null);

      const query = buildZonalQuery({
        province: provinceFromUrl,
        city: cityFromUrl,
        barangay: barangayFromUrl,
        datasetVersion: selectedDatasetVersion,
        street: streetQuery,
      });
      query.set('format', format);

      const response = await fetch(`${API_BASE_URL}/zonal-values/export?${query.toString()}`);
      if (!response.ok) {
        throw new Error(`Export request failed (${response.status})`);
      }

      const blob = await response.blob();
      const fallbackName = `zonal_values_export.${format}`;
      const filename = getFilenameFromDisposition(response.headers.get('content-disposition'), fallbackName);
      const objectUrl = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = objectUrl;
      anchor.download = filename;
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(objectUrl);

      if (response.headers.get('x-export-truncated') === 'true') {
        const rowLimit = response.headers.get('x-export-row-limit') ?? '50000';
        const totalMatches = response.headers.get('x-export-total-matches') ?? 'unknown';
        setExportInfo(`Export completed with limit: ${rowLimit} rows downloaded out of ${totalMatches} matches.`);
      } else {
        setExportInfo(`Export completed: ${filename}`);
      }
    } catch (error) {
      if (error instanceof Error) {
        setExportInfo(error.message);
      } else {
        setExportInfo('Export failed.');
      }
    } finally {
      setExportingFormat(null);
    }
  };

  if (pageView === 'province') {
    return (
      <div className="app-shell">
        <header className="topbar">
          <div className="topbar__content">
            <p className="topbar__eyebrow">Province Explorer</p>
            <h1>{provinceLabelFromUrl || 'Province'}</h1>
            <p className="topbar__subtitle">{regionFromUrl ? `Region: ${regionFromUrl}` : 'Select a city/municipality.'}</p>
          </div>
        </header>

        <main className="workspace">
          {locationError && <p className="error-banner">{locationError}</p>}

          <section className="panel province-panel">
            <h2>City / Municipality</h2>
            <p>Click a city/municipality to move to its barangay page.</p>
            {cityLoading ? (
              <p className="hint">Loading cities...</p>
            ) : cities.length === 0 ? (
              <p className="hint">No city records found for this province.</p>
            ) : (
              <div className="card-grid">
                {cities.map((city) => (
                  <button key={city} type="button" className="entity-card" onClick={() => openBarangayPage(city)}>
                    {cleanLocationLabel(city)}
                    <small>Open barangay list</small>
                  </button>
                ))}
              </div>
            )}
          </section>
        </main>
      </div>
    );
  }

  if (pageView === 'barangay') {
    return (
      <div className="app-shell">
        <header className="topbar">
          <div className="topbar__content">
            <p className="topbar__eyebrow">Barangay Explorer</p>
            <h1>{cleanLocationLabel(cityFromUrl || 'City/Municipality')}</h1>
            <p className="topbar__subtitle">
              {cleanLocationLabel(provinceLabelFromUrl)} / {cleanLocationLabel(cityFromUrl)}
            </p>
          </div>
        </header>

        <main className="workspace">
          {locationError && <p className="error-banner">{locationError}</p>}
          <section className="panel province-panel">
            <h2>Barangay Cards</h2>
            <p>Click a barangay card to open its zonal values page.</p>
            {barangayLoading ? (
              <p className="hint">Loading barangays...</p>
            ) : barangays.length === 0 ? (
              <p className="hint">No barangay records found for {cleanLocationLabel(cityFromUrl)}.</p>
            ) : (
              <div className="card-grid">
                {barangays.map((barangay) => (
                  <button key={barangay} type="button" className="entity-card" onClick={() => openZonalPage(barangay)}>
                    {cleanLocationLabel(barangay)}
                    <small>Open zonal values</small>
                  </button>
                ))}
              </div>
            )}
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
          <section className="panel zonal-controls">
            <div className="zonal-controls__grid">
              <label className="field-group field-group--street">
                Street/Subdivision
                <div className="field-group__inline">
                  <input
                    value={streetInput}
                    onChange={(event) => setStreetInput(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') {
                        applyStreetFilter();
                      }
                    }}
                    placeholder="Type a street for exact or partial match"
                  />
                  <button type="button" className="button button--primary" onClick={applyStreetFilter}>
                    Apply
                  </button>
                  <button type="button" className="button button--secondary" onClick={clearStreetFilter}>
                    Clear
                  </button>
                </div>
              </label>

              <label className="field-group">
                Dataset Version (DO/Year)
                <select value={selectedDatasetVersion} onChange={(event) => handleDatasetChange(event.target.value)}>
                  <option value="">All dataset versions</option>
                  {datasetVersionOptions.map((datasetVersion) => (
                    <option key={datasetVersion} value={datasetVersion}>
                      {datasetVersion}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field-group">
                Compare Against
                <select value={compareDatasetVersion} onChange={(event) => handleCompareChange(event.target.value)}>
                  <option value="">No comparison</option>
                  {datasetVersionOptions
                    .filter((datasetVersion) => datasetVersion !== selectedDatasetVersion)
                    .map((datasetVersion) => (
                      <option key={datasetVersion} value={datasetVersion}>
                        {datasetVersion}
                      </option>
                    ))}
                </select>
              </label>
            </div>

            <p className="policy-banner">
              Policy: <strong>ALL OTHER STREETS</strong> rows are shown only as fallback when no named street row matches your
              street query within the same barangay, property class, and dataset version.
            </p>
          </section>

          <section className="panel summary-panel">
            <div className="summary-panel__header">
              <h2>Decision Summary</h2>
              <p>{summaryLoading ? 'Loading metrics...' : `Scope: ${selectedDatasetVersion || 'All dataset versions'}`}</p>
            </div>

            {summaryError && <p className="error-banner">{summaryError}</p>}

            <div className="summary-cards">
              <article className="metric-card">
                <span>Total Records</span>
                <strong>{summary?.total_records?.toLocaleString() ?? '-'}</strong>
              </article>
              <article className="metric-card">
                <span>Min Value</span>
                <strong>{formatAmount(summary?.min_value ?? null)}</strong>
              </article>
              <article className="metric-card">
                <span>Median Value</span>
                <strong>{formatAmount(summary?.median_value ?? null)}</strong>
              </article>
              <article className="metric-card">
                <span>Max Value</span>
                <strong>{formatAmount(summary?.max_value ?? null)}</strong>
              </article>
              <article className="metric-card">
                <span>Catch-all Rows</span>
                <strong>{summary?.catch_all_records?.toLocaleString() ?? '-'}</strong>
              </article>
            </div>

            {compareSummary && (
              <p className="comparison-text">
                Comparison ({compareDatasetVersion}): median delta is{' '}
                <strong>{summaryMedianDelta === null ? 'N/A' : formatAmount(summaryMedianDelta)}</strong>
              </p>
            )}

            <div className="class-mix">
              {(summary?.class_mix ?? []).map((entry) => (
                <span key={entry.property_class} className="class-chip">
                  {entry.property_class}: {entry.count.toLocaleString()}
                </span>
              ))}
              {(summary?.class_mix ?? []).length === 0 && !summaryLoading && <span className="hint">No class mix data.</span>}
            </div>
          </section>

          <section className="panel records-panel">
            <div className="records-header">
              <div>
                <h2>Zonal Value Records</h2>
                <p>
                  {recordsLoading ? 'Loading records...' : `${results.total.toLocaleString()} records`}
                  {streetQuery.trim() ? ` | Street query: "${streetQuery.trim()}"` : ''}
                </p>
              </div>
              <div className="records-header__actions">
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

                <button
                  type="button"
                  className="button button--secondary"
                  onClick={() => exportRecords('csv')}
                  disabled={Boolean(exportingFormat)}
                >
                  {exportingFormat === 'csv' ? 'Exporting...' : 'Export CSV'}
                </button>
                <button
                  type="button"
                  className="button button--secondary"
                  onClick={() => exportRecords('xlsx')}
                  disabled={Boolean(exportingFormat)}
                >
                  {exportingFormat === 'xlsx' ? 'Exporting...' : 'Export XLSX'}
                </button>
              </div>
            </div>

            {recordsError && <p className="error-banner">{recordsError}</p>}
            {exportInfo && <p className="hint export-hint">{exportInfo}</p>}

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Street/Subdivision</th>
                    <th>Precision</th>
                    <th>Class</th>
                    <th>Type</th>
                    <th>Zonal Value</th>
                    <th>DO/Version</th>
                    <th>RDO</th>
                  </tr>
                </thead>
                <tbody>
                  {results.items.length === 0 && !recordsLoading ? (
                    <tr>
                      <td colSpan={7} className="empty-cell">
                        No zonal values found.
                      </td>
                    </tr>
                  ) : (
                    results.items.map((row) => {
                      const badge = getPrecisionBadge(row);
                      return (
                        <tr key={row.id} className={selectedRecord?.id === row.id ? 'is-active' : ''}>
                          <td>
                            <button type="button" className="street-link" onClick={() => setSelectedRecord(row)}>
                              {row.street_subdivision ?? '-'}
                            </button>
                          </td>
                          <td>
                            <span
                              className={`precision-badge precision-badge--${badge
                                .toLowerCase()
                                .replace(/\s+/g, '-')}`}
                            >
                              {badge}
                            </span>
                          </td>
                          <td>{row.property_class ?? '-'}</td>
                          <td>{row.property_type ?? '-'}</td>
                          <td>{formatAmount(row.zonal_value)}</td>
                          <td>{row.dataset_version}</td>
                          <td>{row.rdo_code ?? '-'}</td>
                        </tr>
                      );
                    })
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
        </main>

        {selectedRecord && (
          <div className="modal-backdrop" role="presentation" onClick={() => setSelectedRecord(null)}>
            <section
              className="record-modal"
              role="dialog"
              aria-modal="true"
              aria-label="Zonal value details"
              onClick={(event) => event.stopPropagation()}
            >
              <div className="record-modal__header">
                <div>
                  <p className="topbar__eyebrow">Record Details</p>
                  <h2>{selectedRecord.street_subdivision ?? '-'}</h2>
                </div>
                <button type="button" className="button button--secondary" onClick={() => setSelectedRecord(null)}>
                  Close
                </button>
              </div>

              <section className="detail-section">
                <h3>Interpretation</h3>
                <p>{getWhyThisAppears(selectedRecord, streetQuery)}</p>
                <p>
                  Precision:{' '}
                  <span
                    className={`precision-badge precision-badge--${getPrecisionBadge(selectedRecord)
                      .toLowerCase()
                      .replace(/\s+/g, '-')}`}
                  >
                    {getPrecisionBadge(selectedRecord)}
                  </span>
                </p>
              </section>

              <section className="detail-section">
                <h3>Location and Value</h3>
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
                  <dt>Property Class</dt>
                  <dd>{selectedRecord.property_class ?? '-'}</dd>
                  <dt>Property Type</dt>
                  <dd>{selectedRecord.property_type ?? '-'}</dd>
                  <dt>Zonal Value</dt>
                  <dd>{formatAmount(selectedRecord.zonal_value)}</dd>
                  <dt>Unit</dt>
                  <dd>{selectedRecord.unit ?? '-'}</dd>
                  <dt>Remarks</dt>
                  <dd>{selectedRecord.remarks ?? '-'}</dd>
                </dl>
              </section>

              <section className="detail-section">
                <h3>Source Transparency</h3>
                <dl className="detail-grid">
                  <dt>Dataset Version</dt>
                  <dd>{selectedRecord.dataset_version}</dd>
                  <dt>RDO</dt>
                  <dd>{selectedRecord.rdo_code ?? '-'}</dd>
                  <dt>Effectivity Date</dt>
                  <dd>{selectedRecord.effectivity_date ?? '-'}</dd>
                  <dt>Source File</dt>
                  <dd>{selectedRecord.source_file}</dd>
                  <dt>Source Sheet</dt>
                  <dd>{selectedRecord.source_sheet}</dd>
                  <dt>Source Row</dt>
                  <dd>{selectedRecord.source_row ?? '-'}</dd>
                  <dt>Ingested At</dt>
                  <dd>{selectedRecord.created_at}</dd>
                </dl>
              </section>

              <div className="record-modal__actions">
                <button type="button" className="button button--secondary" onClick={() => setSelectedRecord(null)}>
                  Close
                </button>
              </div>
            </section>
          </div>
        )}
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
          <p>Click a province to open its city/municipality page.</p>

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
                  onClick={() => openProvincePage(selectedRegion.label, province)}
                >
                  <span>{province.officialName}</span>
                  <small>Open city/barangay page</small>
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
