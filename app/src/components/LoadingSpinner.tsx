export default function LoadingSpinner() {
  return (
    <div className="text-center py-16">
      <div className="inline-block w-12 h-12 border-4 border-gray-300 border-t-blue-800 
                    rounded-full animate-spin mb-5"></div>
      <p className="text-gray-600 text-lg">Searching legal database...</p>
    </div>
  );
}
