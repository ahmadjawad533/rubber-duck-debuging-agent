import React, { useEffect, useState } from 'react';
import { WifiOff } from 'lucide-react';
import { useDuckStore } from '../store/useDuckStore';

export const OfflineBanner: React.FC = () => {
  const [online, setOnlineState] = useState(navigator.onLine);
  const { setOnline } = useDuckStore();

  useEffect(() => {
    const handleOnline = () => {
      setOnlineState(true);
      setOnline(true);
    };
    const handleOffline = () => {
      setOnlineState(false);
      setOnline(false);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [setOnline]);

  if (online) return null;

  return (
    <div
      role="status"
      className="bg-amber-600 text-white px-4 py-2 text-center text-xs sm:text-sm font-medium flex items-center justify-center space-x-2 select-none shadow-xs"
    >
      <WifiOff className="w-4 h-4 flex-shrink-0" />
      <span>You appear to be offline. The duck is floating peacefully until your connection returns.</span>
    </div>
  );
};
