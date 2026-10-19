import test from "node:test";
import assert from "node:assert/strict";
import { apiAnimalToAnimal, apiZoneToZone, getApiJson, apiUrl } from "../services/apiClient.js";
import { analyticsService } from "../services/analyticsService.js";
import { findZoneForPoint } from "../utils/geo.js";
import { formatCoordinate, formatRelative } from "../utils/format.js";

test("missing GPS and timestamps remain unknown rather than fabricated", () => {
  const animal = apiAnimalToAnimal({ animal_id: "A", species: "elephant" });
  assert.deepEqual(animal.coordinates, [null, null]);
  assert.equal(animal.lastSeen, null);
  assert.equal(animal.direction, null);
  assert.equal(formatRelative(animal.lastSeen), "Unknown");
  assert.equal(formatCoordinate(null), "Unknown");
});

test("animal adapter preserves scientific species and provenance", () => {
  const animal = apiAnimalToAnimal({
    animal_id: "SIM-001",
    species: "Parus cinereus",
    data_origin: "simulated_from_regional_species_list",
    source_reference_type: "regional_species_checklist",
    source_reference_name: "Mukurthi mammal checklist",
    source_reference_url: "https://example.org/checklist",
  });
  assert.equal(animal.species, "Parus cinereus");
  assert.equal(animal.dataOrigin, "simulated_from_regional_species_list");
  assert.equal(animal.sourceReferenceType, "regional_species_checklist");
  assert.equal(animal.sourceReferenceName, "Mukurthi mammal checklist");
  assert.equal(animal.sourceReferenceUrl, "https://example.org/checklist");
});

test("API mapping preserves multipolygons and their area", () => {
  const geometry = { type: "MultiPolygon", coordinates: [
    [[[0,0],[2,0],[2,2],[0,2],[0,0]]],
    [[[10,10],[12,10],[12,12],[10,12],[10,10]]]
  ] };
  const zone = apiZoneToZone({ zone_id: "Z", geometry, area_km2: 2.4 });
  assert.deepEqual(zone.geometry, geometry);
  assert.equal(zone.areaKm2, 2.4);
  assert.equal(findZoneForPoint([11,11], [zone]).id, "Z");
});

test("Ooty land-cover classes and region names survive API mapping", () => {
  const zone = apiZoneToZone({ zone_id: "OTY-001", zone_type: "surface_water", study_region_code: "kundah", study_region_name: "Kundah", geometry: { type: "MultiPolygon", coordinates: [] } });
  assert.equal(zone.type, "surface_water");
  assert.equal(zone.regionCode, "kundah");
  assert.equal(zone.regionName, "Kundah");
});

test("polygon holes are excluded", () => {
  const zone = { id: "Z", geometry: { type: "Polygon", coordinates: [
    [[0,0],[10,0],[10,10],[0,10],[0,0]],
    [[3,3],[7,3],[7,7],[3,7],[3,3]]
  ] } };
  assert.equal(findZoneForPoint([1,1], [zone]), zone);
  assert.equal(findZoneForPoint([5,5], [zone]), undefined);
});

test("API failures are surfaced and receive a timeout signal", async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async (_url, options) => {
    assert.ok(options.signal instanceof AbortSignal);
    return new Response(JSON.stringify({ detail: "Database unavailable" }), { status: 503 });
  };
  try { await assert.rejects(getApiJson("/animals"), /Database unavailable/); }
  finally { globalThis.fetch = original; }
});

test("versioned paths do not duplicate the API prefix", () => {
  assert.equal(apiUrl("/api/v1/animals"), apiUrl("/animals"));
});
test("analytics filters include species and an inclusive end date", async () => {
  const original = globalThis.fetch;
  let requestedUrl;
  globalThis.fetch = async (url) => {
    requestedUrl = new URL(url);
    return new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } });
  };
  try {
    await analyticsService.getAnalytics({ start: "2026-10-01", end: "2026-10-02", species: "elephant" });
    assert.equal(requestedUrl.searchParams.get("species"), "elephant");
    assert.equal(requestedUrl.searchParams.get("start_time"), "2026-10-01T00:00:00.000Z");
    assert.equal(requestedUrl.searchParams.get("end_time"), "2026-10-03T00:00:00.000Z");
  } finally { globalThis.fetch = original; }
});
