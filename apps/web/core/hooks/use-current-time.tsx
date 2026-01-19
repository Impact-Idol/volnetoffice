import { useEffect, useState } from "react";

export const useCurrentTime = () => {
  const [currentTime, setCurrentTime] = useState<Date | null>(null);
  // update the current time every minute (60000ms)
  useEffect(() => {
    // Set initial time on client only to avoid hydration mismatch
    setCurrentTime(new Date());

    const intervalId = setInterval(() => {
      setCurrentTime(new Date());
    }, 60000);

    return () => clearInterval(intervalId);
  }, []);

  return {
    currentTime,
  };
};
