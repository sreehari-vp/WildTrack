const reserveCenter = [76.69, 11.41];
const pointInPolygon = (point, polygon) => {
  const [x, y] = point;
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [xi, yi] = polygon[i];
    const [xj, yj] = polygon[j];
    const intersects = yi > y !== yj > y && x < (xj - xi) * (y - yi) / (yj - yi) + xi;
    if (intersects) inside = !inside;
  }
  return inside;
};
const findZoneForPoint = (point, zones) => zones.find((zone) => {
  const polygons = zone.geometry.type === "MultiPolygon" ? zone.geometry.coordinates : [zone.geometry.coordinates];
  return polygons.some(([outer, ...holes]) => pointInPolygon(point, outer) && !holes.some((hole) => pointInPolygon(point, hole)));
});
const mapLocationFromPoint = (point, zones) => {
  const zone = findZoneForPoint(point, zones);
  return {
    coordinates: point,
    zoneId: zone?.id,
    zoneName: zone?.name,
    zoneType: zone?.type,
    risk: zone?.risk ?? "info"
  };
};
const circlePolygon = (center, radiusMeters, steps = 72) => {
  const [lng, lat] = center;
  const earthRadius = 6371e3;
  const latRad = lat * Math.PI / 180;
  const coords = [];
  for (let i = 0; i <= steps; i += 1) {
    const angle = i / steps * Math.PI * 2;
    const dx = radiusMeters * Math.cos(angle);
    const dy = radiusMeters * Math.sin(angle);
    const pointLat = lat + dy / earthRadius * (180 / Math.PI);
    const pointLng = lng + dx / (earthRadius * Math.cos(latRad)) * (180 / Math.PI);
    coords.push([pointLng, pointLat]);
  }
  return coords;
};
const zoneFeatureCollection = (zones) => ({
  type: "FeatureCollection",
  features: zones.map((zone) => ({
    type: "Feature",
    id: zone.id,
    properties: {
      id: zone.id,
      name: zone.name,
      type: zone.type,
      risk: zone.risk,
      color: ({
        safe: "#4f8c65", buffer: "#d1ae50", restricted: "#b85c52",
        "high-risk": "#d9691f", "water-source": "#4d91b4", protected: "#327a52",
        tree_cover: "#327a52", shrubland: "#91a954", grassland: "#d5b75d",
        cultivated_land: "#c58b53", built_up: "#b96055", bare_or_sparse_cover: "#b8a990",
        surface_water: "#4d91b4"
      })[zone.type] ?? "#788b7b",
      statusColor: ({
        safe: "#3f8f5b", low: "#6d9b5f", medium: "#c99a2e", high: "#d9691f",
        critical: "#c2362f", info: "#4b7f9e"
      })[zone.risk] ?? "#4b7f9e",
      regionName: zone.regionName,
      areaKm2: zone.areaKm2,
      description: zone.description
    },
    geometry: zone.geometry
  }))
});
const boundaryFeature = (geometry) => ({
  type: "Feature",
  properties: {},
  geometry
});
export {
  boundaryFeature,
  circlePolygon,
  findZoneForPoint,
  mapLocationFromPoint,
  pointInPolygon,
  reserveCenter,
  zoneFeatureCollection
};
