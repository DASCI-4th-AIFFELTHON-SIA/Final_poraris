import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import * as maplibregl from 'maplibre-gl';
import './maplibre-gl.css';
import * as turf from '@turf/turf';
import './PlanetsTab.css';

function PlanetsTab() {
  const mapContainer = useRef(null);
  const map = useRef(null);
  const popup = useRef(null);
  const [searchParams, setSearchParams] = useState({ year: '', quarter: '', month: '', week: '' });
  const [loading, setLoading] = useState(false);
  const [noResults, setNoResults] = useState(false);
  const [currentLevel, setCurrentLevel] = useState('si_do');
  const [filterStack, setFilterStack] = useState([]);
  const [geoData, setGeoData] = useState({ si_do: null, si_gun: null, articles: null, gazetteerPoints: null, filteredArticles: null });
  const [regionStats, setRegionStats] = useState([]);
  const [articlesByPoint, setArticlesByPoint] = useState({});
  const geoDataRef = useRef(geoData);
  const currentLevelRef = useRef(currentLevel);
  const regionStatsRef = useRef(regionStats);
  const articlesByPointRef = useRef(articlesByPoint);

  const esc = (s='') => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');

  const colorScale = useMemo(() => ['#addd8e','#78c679','#41ab5d','#238443','#005a32'], []);

  const layers = useMemo(() => [
    { id: 'fill-layer', type: 'fill', source: 'geojson-data', paint: { 'fill-color': '#4575b4', 'fill-opacity': 0.7 } },
    { id: 'outline-layer', type: 'line', source: 'geojson-data', paint: { 'line-color': 'rgba(255, 255, 255, 0.5)', 'line-width': 1 } },
    { id: 'point-layer', type: 'circle', source: 'geojson-data', paint: { 'circle-radius': 5, 'circle-color': '#2e0efcf2', 'circle-stroke-color': '#fff', 'circle-stroke-width': 1, 'circle-opacity': 0.8 } }
  ], []);

  const preLoadGeoJSONs = useCallback(async () => {
    setLoading(true);
    try {
      const [siDoRes, siGunRes, gazetteerRes] = await Promise.all([
        fetch('/main_geo_data/dprk_si_do.geojson'),
        fetch('/main_geo_data/dprk_si_gun.geojson'),
        fetch('/main_geo_data/gazetter_with_si_gun.geojson'),
      ]);
      const [siDoData, siGunData, gazetteerData] = await Promise.all([siDoRes.json(), siGunRes.json(), gazetteerRes.json()]);
      setGeoData(prev => ({ ...prev, si_do: siDoData, si_gun: siGunData, gazetteerPoints: gazetteerData }));
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  const calculateStats = useCallback((regions, articles, level) => {
    if (!regions || !articles || articles.length === 0) return [];
    const regionNameKey = level === 'si_do' ? 'NL_NAME_1' : 'NL_NAME_2';
    const stats = regions.map(region => {
      const regionName = (region.properties[regionNameKey] || '').trim().replace(/\s/g, '');
      const count = articles.filter(article =>
        (article.locations || []).some(location => {
          const t = (location || '').trim().replace(/\s/g, '');
          return regionName.includes(t) || t.includes(regionName);
        })
      ).length;
      return { name: regionName, count };
    });
    const total = stats.reduce((s, v) => s + v.count, 0);
    return stats.map(s => ({ ...s, percentage: total > 0 ? (s.count / total) * 100 : 0 })).sort((a, b) => b.count - a.count);
  }, []);

  const calculatePointStats = useCallback((articles, points) => {
    if (!articles || articles.length === 0 || !points || points.length === 0) return [];
    const pointCounts = new Map();
    const totalArticles = articles.length;
    articles.forEach(article => {
      (article.locations || []).forEach(location => {
        const trimmedLocation = (location || '').trim().replace(/\s/g, '');
        const matchingPoint = points.find(point => {
          const pointName = (point.properties.name || '').trim().replace(/\s/g, '');
          return pointName === trimmedLocation;
        });
        if (matchingPoint) {
          const pointName = matchingPoint.properties.name;
          pointCounts.set(pointName, (pointCounts.get(pointName) || 0) + 1);
        }
      });
    });
    const stats = Array.from(pointCounts.entries()).map(([name, count]) => ({ name, count, percentage: totalArticles > 0 ? (count / totalArticles) * 100 : 0 })).sort((a, b) => b.count - a.count);
    return stats;
  }, []);

  const renderGeoJSON = useCallback((geojson, newLevel, counts = {}, boundsFeature = null) => {
    if (!map.current || !map.current.isStyleLoaded() || !geojson) return;
    if (map.current.getSource('geojson-data')) {
      if (map.current.getLayer('fill-layer')) map.current.removeLayer('fill-layer');
      if (map.current.getLayer('outline-layer')) map.current.removeLayer('outline-layer');
      if (map.current.getLayer('point-layer')) map.current.removeLayer('point-layer');
      map.current.removeSource('geojson-data');
    }
    map.current.addSource('geojson-data', { type: 'geojson', data: geojson });

    let fillColorExpression;
    const maxCount = Math.max(...Object.values(counts));
    if (maxCount > 0) {
      fillColorExpression = ['interpolate', ['linear'], ['get', 'article_count'],
        0, colorScale[0],
        maxCount * 0.2, colorScale[1],
        maxCount * 0.4, colorScale[2],
        maxCount * 0.6, colorScale[3],
        maxCount, colorScale[4]
      ];
    } else {
      fillColorExpression = colorScale[0];
    }

    let pointRadiusExpression = ['case', ['<', ['get', 'article_count'], 1], 0, 5];
    if (newLevel === 'point' && geojson.features.length > 0) {
      const pointCounts = geojson.features.map(f => f.properties.article_count || 0);
      const maxPointCount = Math.max(...pointCounts);
      if (maxPointCount > 0) {
        pointRadiusExpression = ['interpolate', ['linear'], ['get', 'article_count'], 0, 5, maxPointCount, 20];
      }
    }

    const updatedLayers = layers.map(layer => {
      let visibility = 'none';
      let paint = { ...layer.paint };
      if ((layer.id === 'fill-layer' || layer.id === 'outline-layer') && newLevel !== 'point') {
        visibility = 'visible';
        if (layer.id === 'fill-layer') paint = { ...paint, 'fill-color': fillColorExpression };
      } else if (layer.id === 'point-layer' && newLevel === 'point') {
        visibility = 'visible';
        paint = { ...paint, 'circle-radius': pointRadiusExpression };
      }
      return { ...layer, layout: { visibility }, paint };
    });
    updatedLayers.forEach(layer => map.current.addLayer(layer));

    if (boundsFeature) {
      const bbox = turf.bbox(boundsFeature);
      map.current.fitBounds(bbox, { padding: 50, duration: 1000 });
    } else if (geojson.features.length > 0) {
      const bbox = turf.bbox(geojson);
      map.current.fitBounds(bbox, { padding: 50, duration: 1000 });
    }
  }, [layers, colorScale]);

  useEffect(() => { geoDataRef.current = geoData; }, [geoData]);
  useEffect(() => { currentLevelRef.current = currentLevel; }, [currentLevel]);
  useEffect(() => { regionStatsRef.current = regionStats; }, [regionStats]);
  useEffect(() => { articlesByPointRef.current = articlesByPoint; }, [articlesByPoint]);

  useEffect(() => {
    if (map.current) return;
    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: { version: 8, sources: { osm: { type: 'raster', tiles: ['https://a.tile.openstreetmap.org/{z}/{x}/{y}.png'], tileSize: 256, attribution: '&copy; OpenStreetMap Contributors' } }, layers: [{ id: 'osm-layer', type: 'raster', source: 'osm', minzoom: 0, maxzoom: 22 }] },
      center: [127.5, 39.0],
      zoom: 6
    });
    map.current.on('load', () => {});
    map.current.on('click', (e) => {
      const features = map.current.queryRenderedFeatures(e.point, { layers: ['fill-layer'] });
      if (features.length > 0) {
        const feature = features[0];
        const properties = feature.properties;
        let newFilter = {};
        if (currentLevelRef.current === 'si_do' && properties.NL_NAME_1) newFilter = { level: 'si_do', name: properties.NL_NAME_1, feature: feature };
        else if (currentLevelRef.current === 'si_gun' && properties.NL_NAME_2) newFilter = { level: 'si_gun', name: properties.NL_NAME_2, feature: feature };
        if (Object.keys(newFilter).length > 0) setFilterStack(prev => [...prev, newFilter]);
      }
    });
    map.current.on('mousemove', 'fill-layer', (e) => {
      if (!popup.current) popup.current = new maplibregl.Popup({ closeButton: false, closeOnClick: false, className: 'map-popup' });
      const properties = e.features[0].properties;
      let regionName = '알 수 없음';
      if (currentLevelRef.current === 'si_do') regionName = properties.NL_NAME_1 || regionName;
      else if (currentLevelRef.current === 'si_gun') regionName = properties.NL_NAME_2 || regionName;
      const stats = regionStatsRef.current.find(stat => stat.name === (regionName || '').trim().replace(/\s/g, ''));
      const count = stats ? stats.count : 0;
      const percentage = stats ? stats.percentage.toFixed(2) : 0;
      popup.current.setLngLat(e.lngLat).setHTML(`<h3>${esc(regionName)}</h3><p>기사 수: ${count} (${percentage}%)</p>`).addTo(map.current);
    });
    map.current.on('mouseleave', 'fill-layer', () => { if (popup.current) popup.current.remove(); });

    map.current.on('click', 'point-layer', (e) => {
      if (!popup.current) popup.current = new maplibregl.Popup({ closeButton: true, closeOnClick: true, className: 'map-popup' });
      const props = e.features[0].properties;
      const placeName = props.name || '알 수 없음';
      const list = articlesByPointRef.current[placeName] || [];
      const pageSize = 3;
      const totalPages = Math.max(1, Math.ceil(list.length / pageSize));
      const renderPage = (page) => {
        const p = Math.min(Math.max(page, 0), totalPages - 1);
        const start = p * pageSize;
        const items = list.slice(start, start + pageSize);
        const itemsHTML = items.map(it => `
          <li class="pp-item">
            ${it.url ? `<a href="${esc(it.url)}" target="_blank" rel="noopener noreferrer">${esc(it.title || '(제목 없음)')}</a>` : esc(it.title || '(제목 없음)')}
            <div class="pp-sub">${esc((it.pubDate || '').split(' ')[0])}</div>
          </li>
        `).join('') || '<li class="pp-item">관련 기사가 없습니다.</li>';
        const html = `
          <div class="pp-wrap" data-place="${esc(placeName)}" data-page="${p}">
            <h3 class="pp-title">${esc(placeName)}</h3>
            <ul class="pp-list">${itemsHTML}</ul>
            <div class="pp-pager">
              <button class="pp-prev" ${p===0?'disabled':''}>이전</button>
              <span class="pp-info">${p+1} / ${totalPages}</span>
              <button class="pp-next" ${p>=totalPages-1?'disabled':''}>다음</button>
            </div>
          </div>
        `;
        popup.current.setLngLat(e.lngLat).setHTML(html).addTo(map.current);
        const el = popup.current.getElement();
        el.querySelector('.pp-prev')?.addEventListener('click', (ev) => { ev.stopPropagation(); renderPage(p - 1); });
        el.querySelector('.pp-next')?.addEventListener('click', (ev) => { ev.stopPropagation(); renderPage(p + 1); });
      };
      renderPage(0);
    });
    map.current.on('mouseleave', 'point-layer', () => {});
    preLoadGeoJSONs();
  }, [preLoadGeoJSONs]);

  useEffect(() => {
    if (!map.current || !map.current.isStyleLoaded() || !geoData.si_do || !geoData.si_gun || !geoData.gazetteerPoints) return;
    setLoading(true);
    let finalGeoJSON;
    let newLevel;
    let regionsForStats = [];
    let stats = [];
    let boundsFeature = null;
    const hasFilteredArticles = geoData.filteredArticles && geoData.filteredArticles.length > 0;
    setNoResults(!hasFilteredArticles);
    if (filterStack.length > 0) {
      const lastFilter = filterStack[filterStack.length - 1];
      boundsFeature = lastFilter.feature;
      if (lastFilter.level === 'si_do') {
        newLevel = 'si_gun';
        const siGunFeatures = geoData.si_gun.features.filter(feature => {
          const featureName = (feature.properties.NL_NAME_1 || '').trim().replace(/\s/g, '');
          const filterName = (lastFilter.name || '').trim().replace(/\s/g, '');
          return featureName.includes(filterName) || filterName.includes(featureName);
        });
        finalGeoJSON = { ...geoData.si_gun, features: siGunFeatures };
        regionsForStats = siGunFeatures;
      } else {
        newLevel = 'point';
        const currentSiGunName = (lastFilter.name || '').trim().replace(/\s/g, '');
        const articlesInCurrentRegion = geoData.filteredArticles.filter(article =>
          (article.locations || []).some(location => {
            const t = (location || '').trim().replace(/\s/g, '');
            return currentSiGunName.includes(t) || t.includes(currentSiGunName);
          })
        );
        const pointFeaturesInCurrentSiGun = geoData.gazetteerPoints.features.filter(point => {
          const pointSiGunName = (point.properties.NL_NAME_2 || '').trim().replace(/\s/g, '');
          return pointSiGunName === currentSiGunName;
        });
        const pointStats = calculatePointStats(articlesInCurrentRegion, pointFeaturesInCurrentSiGun);
        setRegionStats(pointStats);
        const byPoint = {};
        articlesInCurrentRegion.forEach(article => {
          (article.locations || []).forEach(loc => {
            const nameKey = (loc || '').trim().replace(/\s/g,'');
            const matched = pointFeaturesInCurrentSiGun.find(p => ((p.properties.name || '').trim().replace(/\s/g,'')) === nameKey);
            if (matched) {
              const key = matched.properties.name;
              (byPoint[key] ||= []).push({ title: article.title || '(제목 없음)', url: article.url || '', pubDate: article.pubDate || '' });
            }
          });
        });
        setArticlesByPoint(byPoint);
        const pointsWithCounts = pointFeaturesInCurrentSiGun.map(point => {
          const stat = pointStats.find(s => s.name === point.properties.name);
          return { ...point, properties: { ...point.properties, article_count: stat ? stat.count : 0 } };
        }).filter(point => point.properties.article_count > 0);
        finalGeoJSON = { type: 'FeatureCollection', features: pointsWithCounts };
      }
    } else {
      newLevel = 'si_do';
      finalGeoJSON = geoData.si_do;
      regionsForStats = geoData.si_do.features;
    }
    if (newLevel !== 'point' && geoData.filteredArticles) {
      stats = calculateStats(regionsForStats, geoData.filteredArticles, newLevel);
      const geojsonWithCounts = {
        ...finalGeoJSON,
        features: finalGeoJSON.features.map(feature => {
          let regionName;
          if (newLevel === 'si_do') regionName = feature.properties.NL_NAME_1;
          else if (newLevel === 'si_gun') regionName = feature.properties.NL_NAME_2;
          const stat = stats.find(s => s.name === (regionName || '').trim().replace(/\s/g, ''));
          return { ...feature, properties: { ...feature.properties, article_count: stat ? stat.count : 0 } };
        })
      };
      renderGeoJSON(geojsonWithCounts, newLevel, stats.reduce((acc, curr) => { acc[curr.name] = curr.count; return acc; }, {}), boundsFeature);
    } else {
      renderGeoJSON(finalGeoJSON, newLevel, {}, boundsFeature);
    }
    if (newLevel !== 'point') setRegionStats(stats);
    setCurrentLevel(newLevel);
    setLoading(false);
  }, [filterStack, geoData.si_do, geoData.si_gun, geoData.filteredArticles, geoData.gazetteerPoints, renderGeoJSON, calculateStats, calculatePointStats]);

  const getCustomWeek = (day) => {
    if (day >= 1 && day <= 8) return 1;
    if (day >= 9 && day <= 15) return 2;
    if (day >= 16 && day <= 22) return 3;
    if (day >= 23) return 4;
    return -1;
  };

  const handleSearch = async () => {
    if (!searchParams.year) { alert('년도를 선택해주세요.'); return; }
    setLoading(true);
    setNoResults(false);
    try {
      const articlesRes = await fetch(`/article_geo_data/combined_data_${searchParams.year}_with_coordinates_extracted.json`);
      const articlesData = await articlesRes.json();
      let filteredData = articlesData;
      if (searchParams.quarter) {
        const q = parseInt(searchParams.quarter);
        filteredData = filteredData.filter(a => Math.ceil((new Date(a.pubDate).getMonth() + 1) / 3) === q);
      } else if (searchParams.month) {
        const m = parseInt(searchParams.month);
        filteredData = filteredData.filter(a => (new Date(a.pubDate).getMonth() + 1) === m);
      }
      if (searchParams.week) {
        const w = parseInt(searchParams.week);
        filteredData = filteredData.filter(a => getCustomWeek(new Date(a.pubDate).getDate()) === w);
      }
      setGeoData(prev => ({ ...prev, articles: articlesData, filteredArticles: filteredData }));
      setFilterStack([]);
      setArticlesByPoint({});
    } catch (e) {
      console.error(e);
      setGeoData(prev => ({ ...prev, articles: null, filteredArticles: [] }));
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setFilterStack([]);
    setSearchParams({ year: '', quarter: '', month: '', week: '' });
    setGeoData(prev => ({ ...prev, articles: null, filteredArticles: [] }));
    setArticlesByPoint({});
  };

  const handleBack = () => { setFilterStack(prev => prev.slice(0, -1)); };

  const handleSearchParams = (e) => {
    const { name, value } = e.target;
    setSearchParams(prev => ({ ...prev, [name]: value, ...(name === 'quarter' && { month: '', week: '' }), ...(name === 'month' && { week: '' }) }));
  };

  const years = []; for (let i = 2016; i <= 2025; i++) years.push(i);

  return (
    <div className="planets-tab">
      <div className="search-panel">
        <h2>북한 GeoJSON 지도</h2>
        <div className="search-form">
          <div className="form-group">
            <label htmlFor="year-select">기간</label>
            <div className="select-group">
              <select id="year-select" name="year" value={searchParams.year} onChange={handleSearchParams}>
                <option value="">년도</option>
                {years.map(year => (<option key={year} value={year}>{year}년</option>))}
              </select>
              <select id="quarter-select" name="quarter" value={searchParams.quarter} onChange={handleSearchParams}>
                <option value="">분기</option>
                <option value="1">1분기</option>
                <option value="2">2분기</option>
                <option value="3">3분기</option>
                <option value="4">4분기</option>
              </select>
              <select id="month-select" name="month" value={searchParams.month} onChange={handleSearchParams} disabled={searchParams.quarter !== ''}>
                <option value="">월</option>
                {[...Array(12)].map((_, i) => { const m = i + 1; return (<option key={m} value={m}>{m}월</option>); })}
              </select>
              <select id="week-select" name="week" value={searchParams.week} onChange={handleSearchParams} disabled={searchParams.quarter !== '' || searchParams.month === ''}>
                <option value="">주차</option>
                {[...Array(4)].map((_, i) => { const w = i + 1; return (<option key={w} value={w}>{w}주차</option>); })}
              </select>
            </div>
          </div>
        </div>

        {filterStack.length > 0 && (
          <div className="search-results">
            <button className="back-button" onClick={handleBack}><span className="button-icon">⬅️</span> 뒤로가기</button>
            <div className="breadcrumb">
              {filterStack.map((filter, index) => (<span key={index}>{filter.name}{index < filterStack.length - 1 && ' > '}</span>))}
            </div>
          </div>
        )}

        <div className="button-group">
          <button className="search-button" onClick={handleSearch}><span className="button-icon">🔍</span> 검색</button>
          <button className="reset-button" onClick={handleReset}><span className="button-icon">🔄</span> 초기화</button>
        </div>

        <div className="stats-panel">
          <h3>기사 빈도 및 비율</h3>
          <ul className="stats-list">
            {regionStats.length > 0 ? (
              regionStats.map(stat => (
                <li key={stat.name} className="stat-item">
                  <h4>{stat.name}</h4>
                  <div className="stat-details">
                    <span className="stat-count">{stat.count}개 ({stat.percentage.toFixed(2)}%)</span>
                    <div className="stat-bar-container"><div className="stat-bar" style={{ width: `${stat.percentage}%` }} /></div>
                  </div>
                </li>
              ))
            ) : (<p>표시할 데이터가 없습니다.</p>)}
          </ul>
        </div>

        <div className="legend">
          <h4>범례</h4>
          <div className="legend-item"><div className="legend-color" style={{background: colorScale[0]}}></div><span>매우 낮음</span></div>
          <div className="legend-item"><div className="legend-color" style={{background: colorScale[1]}}></div><span>낮음</span></div>
          <div className="legend-item"><div className="legend-color" style={{background: colorScale[2]}}></div><span>보통</span></div>
          <div className="legend-item"><div className="legend-color" style={{background: colorScale[3]}}></div><span>높음</span></div>
          <div className="legend-item"><div className="legend-color" style={{background: colorScale[4]}}></div><span>매우 높음</span></div>
        </div>
      </div>

      <div className="map-container">
        <div ref={mapContainer} className="map" />
        {loading && (<div className="loading-overlay"><div className="loading-spinner"></div><p>데이터를 불러오는 중...</p></div>)}
        {noResults && !loading && (<div className="no-results-overlay"><p>검색 결과가 없습니다.</p></div>)}
      </div>
    </div>
  );
}

export default PlanetsTab;
