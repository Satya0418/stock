import React from 'react';

function RetryState({ message, onRetry }) {
  return (
    <div className="bg-gray-800/70 border border-gray-700 rounded-xl p-6 text-center">
      <p className="text-gray-300">{message}</p>
      <button
        type="button"
        className="mt-4 px-4 py-2 bg-bullish text-white rounded-lg hover:bg-bullish/80"
        onClick={onRetry}
      >
        Retry
      </button>
    </div>
  );
}

export default RetryState;
