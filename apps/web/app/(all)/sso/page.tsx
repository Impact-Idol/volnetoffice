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
    return (
      <DefaultLayout>
        <div className="flex min-h-screen items-center justify-center">
          <div className="text-center max-w-md">
            <h1 className="text-2xl font-bold text-red-500 mb-4">Authentication Failed</h1>
            <p className="text-neutral-600 dark:text-neutral-400 mb-6">{error}</p>
            <div className="space-y-2">
              <a
                href="/"
                className="inline-block px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
              >
                Back to Sign In
              </a>
              <p className="text-sm text-neutral-500 mt-4">
                If you continue to experience issues, please contact your administrator.
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
