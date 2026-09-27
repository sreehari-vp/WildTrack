const withDelay = async (value, min = 300, max = 600) => {
  const delay = min + Math.round(Math.random() * (max - min));
  await new Promise((resolve) => window.setTimeout(resolve, delay));
  return structuredClone(value);
};
export {
  withDelay
};
