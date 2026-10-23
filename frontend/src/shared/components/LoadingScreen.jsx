import React from 'react';

function LoadingScreen({ message = 'Loading...' }) {
  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center">
      <div className="text-center">
        <div className="h-10 w-10 border-4 border-gray-700 border-t-bullish rounded-full animate-spin mx-auto" />
        <p className="text-gray-400 mt-4">{message}</p>
      </div>
    </div>
  );
}

export default LoadingScreen;
