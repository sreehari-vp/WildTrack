const movementPathsFromObservations = (observations) => {
  const grouped = observations.reduce((acc, observation) => {
    acc[observation.animalId] = [...acc[observation.animalId] ?? [], observation];
    return acc;
  }, {});
  return Object.entries(grouped).map(([animalId, points]) => ({
    id: `path-${animalId}`,
    animalId,
    coordinates: points.slice().sort((a, b) => new Date(a.recordedAt).getTime() - new Date(b.recordedAt).getTime()).map((point) => point.coordinates)
  }));
};
export {
  movementPathsFromObservations
};
