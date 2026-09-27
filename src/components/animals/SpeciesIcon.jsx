const SpeciesIcon = ({ species, className = "h-5 w-5" }) => {
  if (species === "elephant") {
    return <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
        <path fill="currentColor" d="M7 14.5C7 10.4 10.6 7 16.2 7C22 7 26 10.7 26 16.2v6.1c0 1.5-.9 2.7-2.2 2.7s-2.1-1.1-2.1-2.5v-3.2h-2.4v3.1c0 1.5-.9 2.6-2.2 2.6S15 23.9 15 22.4v-3.1h-3.3c-.7 0-1.3-.2-1.9-.5v3.8c0 1.2-.8 2.1-1.9 2.1S6 23.8 6 22.6v-7.2c0-.3.4-.6 1-.9Zm18.7-2.5c1.9.4 3.3 2 3.3 4.1 0 1.6-.7 2.9-1.9 3.7V16c0-1.5-.5-2.8-1.4-4Z" />
      </svg>;
  }
  if (species === "tiger") {
    return <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
        <path fill="currentColor" d="M5 17.8c0-4.5 3.8-8.1 9.1-8.1h6.2c3.8 0 6.7 2.9 6.7 6.6 0 1.6-.6 3.1-1.6 4.2l1.6 3.8h-3.5l-1-2.2a8 8 0 0 1-2.2.3h-8.1l-1 1.9H7.8l1.4-2.8C6.8 20.9 5 19.6 5 17.8Zm4.2-3.3 2.2 1.6-.9-3.1c-.5.4-.9.9-1.3 1.5Zm5.3-2.2 1.6 3 .8-3h-2.4Zm5.3.2.9 2.9 1.5-2.3c-.7-.3-1.5-.5-2.4-.6Z" />
      </svg>;
  }
  return <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <path fill="currentColor" d="M9.8 8.2 6.2 5.5 5 7.1l3.2 2.4c-1.1.9-1.8 2.3-1.8 4.1 0 3.6 2.7 6.2 6.5 6.7l-1.7 4h3.4l1.4-3.6h3.1l1.4 3.6h3.4l-1.8-4.2c2.4-.9 4-2.9 4-5.7 0-3.6-2.7-6.5-6.8-6.5h-3.7l2.9-3.5-1.6-1.3-3.9 4.8h-.8L8.5 3.1 6.9 4.4l2.9 3.8Z" />
    </svg>;
};
export {
  SpeciesIcon
};
