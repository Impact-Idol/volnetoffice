import { useEffect, useState } from "react";

const useSize = () => {
  const [windowSize, setWindowSize] = useState<[number, number]>([0, 0]);

  useEffect(() => {
    // Set initial size on client only to avoid hydration mismatch
    setWindowSize([window.innerWidth, window.innerHeight]);

    const windowSizeHandler = () => {
      setWindowSize([window.innerWidth, window.innerHeight]);
    };
    window.addEventListener("resize", windowSizeHandler);
    return () => {
      window.removeEventListener("resize", windowSizeHandler);
    };
  }, []);

  return windowSize;
};

export default useSize;
