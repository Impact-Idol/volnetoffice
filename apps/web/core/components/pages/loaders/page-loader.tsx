import { range } from "lodash-es";
import { Loader } from "@plane/ui";

// Deterministic widths to avoid hydration mismatch from Math.random()
const LOADER_WIDTHS = [280, 310, 260, 290, 270, 300, 250, 320, 275, 295];

export function PageLoader() {
  return (
    <div className="relative w-full h-full flex flex-col">
      <div className="px-3 border-b border-subtle py-3">
        <Loader className="relative flex items-center gap-2">
          <Loader.Item width="200px" height="30px" />
          <div className="relative flex items-center gap-2 ml-auto">
            <Loader.Item width="100px" height="30px" />
            <Loader.Item width="100px" height="30px" />
          </div>
        </Loader>
      </div>
      <div>
        {range(10).map((i) => (
          <Loader key={i} className="relative flex items-center gap-2 p-3 py-4 border-b border-subtle">
            <Loader.Item width={`${LOADER_WIDTHS[i]}px`} height="22px" />
            <div className="ml-auto relative flex items-center gap-2">
              <Loader.Item width="60px" height="22px" />
              <Loader.Item width="22px" height="22px" />
              <Loader.Item width="22px" height="22px" />
              <Loader.Item width="22px" height="22px" />
            </div>
          </Loader>
        ))}
      </div>
    </div>
  );
}
