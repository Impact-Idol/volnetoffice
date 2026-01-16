/**
 * Impact Idol SSO Handler
 *
 * This page handles the SSO authentication flow from Impact Idol.
 * It receives a JWT token via URL query parameter, exchanges it with the backend,
 * and redirects the user to their workspace.
 */

import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router";
import { Loader2 } from "lucide-react";
// helpers
import { API_BASE_URL } from "@plane/constants";
// layouts
import DefaultLayout from "@/layouts/default-layout";

function SSOPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(true);

  useEffect(() => {
    async function processSSO() {
      try {
        // Get token from URL query parameter
        const params = new URLSearchParams(location.search);
        const token = params.get("token");

        if (!token) {
          setError("No authentication token provided");
          setIsProcessing(false);
          return;
        }

        // Call the Impact Idol SSO endpoint
        const response = await fetch(`${API_BASE_URL}/auth/impactidol-sso/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ token }),
          credentials: "include", // Important: include cookies for session auth
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.error || "Authentication failed");
        }

        const data = await response.json();

        // Django session authentication is now active via sessionid cookie
        // No need to store tokens - the session cookie handles everything

        // Redirect to the default workspace
        const workspaceSlug = "staff"; // Default workspace for SSO users

        // Small delay to ensure session is fully established
        setTimeout(() => {
          window.location.href = `/${workspaceSlug}`;
        }, 100);
      } catch (err) {
        console.error("SSO authentication error:", err);
        setError(err instanceof Error ? err.message : "Authentication failed");
        setIsProcessing(false);
      }
    }

    processSSO();
  }, [location.search]);

  if (error) {
    const isTokenExpired = error.toLowerCase().includes("expired");
    const friendlyMessage = isTokenExpired
      ? "Your login link has expired. This can happen if the page took too long to load or you refreshed the page."
      : error;

    return (
      <DefaultLayout>
        <div className="flex min-h-screen items-center justify-center px-4">
          <div className="text-center max-w-md w-full">
            <div className="mb-6">
              <div className="mx-auto w-16 h-16 bg-yellow-100 dark:bg-yellow-900/30 rounded-full flex items-center justify-center mb-4">
                <svg
                  className="w-8 h-8 text-yellow-600 dark:text-yellow-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
              </div>
              <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100 mb-2">
                Unable to Sign In Automatically
              </h1>
              <p className="text-neutral-600 dark:text-neutral-400 mb-6">{friendlyMessage}</p>
            </div>

            <div className="space-y-3">
              <a
                href="/"
                className="block w-full px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
              >
                Sign In with Password
              </a>
              <p className="text-sm text-neutral-500 dark:text-neutral-400">
                Or{" "}
                <a
                  href="javascript:window.close()"
                  className="text-blue-600 dark:text-blue-400 hover:underline font-medium"
                >
                  go back to Impact Idol
                </a>{" "}
                and try again
              </p>
            </div>

            <div className="mt-8 pt-6 border-t border-neutral-200 dark:border-neutral-700">
              <p className="text-sm text-neutral-500 dark:text-neutral-400">
                <strong>Tip:</strong> Login links expire after 5 minutes for security. If you need help, contact your administrator.
              </p>
            </div>
          </div>
        </div>
      </DefaultLayout>
    );
  }

  return (
    <DefaultLayout>
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin mx-auto mb-6 text-blue-600" />
          <h1 className="text-2xl font-bold mb-2">Authenticating...</h1>
          <p className="text-neutral-600 dark:text-neutral-400">
            {isProcessing
              ? "Please wait while we log you in via Impact Idol SSO"
              : "Redirecting to your workspace..."}
          </p>
        </div>
      </div>
    </DefaultLayout>
  );
}

export default SSOPage;
