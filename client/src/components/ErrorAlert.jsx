const ErrorAlert = ({ errors }) => {
  if (!errors || errors.length === 0) return null;

  return (
    <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
      <strong className="font-bold">Error!</strong>
      <span className="block sm:inline">
        <ul>
          {errors.map((error, index) => (
            <li key={index}>{error}</li>
          ))}
        </ul>
      </span>
    </div>
  );
};

export default ErrorAlert;
