const movementPathsFromObservations = (observations) => {
  const grouped = observations.reduce((acc, observation) => {
    acc[observation.animalId] = [...acc[observation.animalId] ?? [], observation];
    return acc;
  }, {});
  return Object.entries(grouped).map(([animalId, points]) => ({
    id: `path-${animalId}`,
    animalId,
    coordinates: points.slice().sort((a, b) => {
      const timeDelta = new Date(a.recordedAt).getTime() - new Date(b.recordedAt).getTime();
      if (timeDelta) return timeDelta;
      if (Number.isFinite(a.sequence) && Number.isFinite(b.sequence)) return a.sequence - b.sequence;
      return String(a.id).localeCompare(String(b.id));
    }).map((point) => point.coordinates)
  }));
};
export {
  movementPathsFromObservations
};
