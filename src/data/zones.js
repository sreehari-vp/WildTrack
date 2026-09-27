const poly = (points) => ({
  type: "Polygon",
  coordinates: [[...points, points[0]]]
});
const reserveBoundary = poly([
  [76.612, 11.354],
  [76.735, 11.362],
  [76.762, 11.424],
  [76.726, 11.486],
  [76.62, 11.47],
  [76.584, 11.409]
]);
const zones = [
  {
    id: "zone-north-bamboo",
    name: "North bamboo flats",
    type: "safe",
    risk: "safe",
    areaKm2: 8.4,
    description: "Open bamboo and grazing flats used by elephant herds.",
    geometry: poly([
      [76.626, 11.432],
      [76.673, 11.433],
      [76.67, 11.468],
      [76.621, 11.462]
    ])
  },
  {
    id: "zone-theppakadu-buffer",
    name: "Theppakadu buffer",
    type: "buffer",
    risk: "medium",
    areaKm2: 7.1,
    description: "Patrolled buffer near camp roads and grazing routes.",
    geometry: poly([
      [76.671, 11.431],
      [76.715, 11.43],
      [76.727, 11.462],
      [76.67, 11.468]
    ])
  },
  {
    id: "zone-kargudi-restricted",
    name: "Kargudi restricted corridor",
    type: "restricted",
    risk: "high",
    areaKm2: 6.2,
    description: "Narrow movement corridor under watch for road crossings.",
    geometry: poly([
      [76.624, 11.398],
      [76.674, 11.399],
      [76.673, 11.432],
      [76.626, 11.432]
    ])
  },
  {
    id: "zone-moyar-high-risk",
    name: "Moyar ridge high-risk",
    type: "high-risk",
    risk: "critical",
    areaKm2: 5.8,
    description: "Steep terrain and repeated conflict reports.",
    geometry: poly([
      [76.674, 11.398],
      [76.733, 11.397],
      [76.715, 11.43],
      [76.673, 11.432]
    ])
  },
  {
    id: "zone-avarahalla-water",
    name: "Avarahalla water line",
    type: "water-source",
    risk: "info",
    areaKm2: 3.9,
    description: "Seasonal water line used by deer and elephants.",
    geometry: poly([
      [76.612, 11.372],
      [76.652, 11.371],
      [76.674, 11.399],
      [76.624, 11.398]
    ])
  },
  {
    id: "zone-sand-road-protected",
    name: "Sand road protected forest",
    type: "protected",
    risk: "high",
    areaKm2: 8.9,
    description: "Protected habitat with tiger denning activity.",
    geometry: poly([
      [76.652, 11.371],
      [76.725, 11.368],
      [76.733, 11.397],
      [76.674, 11.398]
    ])
  },
  {
    id: "zone-masinagudi-buffer",
    name: "Masinagudi buffer edge",
    type: "buffer",
    risk: "medium",
    areaKm2: 5.4,
    description: "Edge habitat near settlement patrol beats.",
    geometry: poly([
      [76.586, 11.405],
      [76.624, 11.398],
      [76.626, 11.432],
      [76.605, 11.438]
    ])
  },
  {
    id: "zone-south-teak-safe",
    name: "South teak safe block",
    type: "safe",
    risk: "safe",
    areaKm2: 6.7,
    description: "Quiet teak block with consistent low-risk movement.",
    geometry: poly([
      [76.586, 11.374],
      [76.612, 11.372],
      [76.624, 11.398],
      [76.586, 11.405]
    ])
  },
  {
    id: "zone-glenmorgan-restricted",
    name: "Glenmorgan restricted slope",
    type: "restricted",
    risk: "high",
    areaKm2: 4.8,
    description: "Restricted slope with limited vehicle access.",
    geometry: poly([
      [76.725, 11.368],
      [76.755, 11.387],
      [76.742, 11.42],
      [76.733, 11.397]
    ])
  },
  {
    id: "zone-karadibetta-protected",
    name: "Karadibetta protected patch",
    type: "protected",
    risk: "high",
    areaKm2: 6.1,
    description: "Protected patch with fresh predator signs.",
    geometry: poly([
      [76.715, 11.43],
      [76.742, 11.42],
      [76.727, 11.462],
      [76.705, 11.474]
    ])
  }
];
export {
  reserveBoundary,
  zones
};
