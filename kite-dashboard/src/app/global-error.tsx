"use client";

import { useEffect } from "react";

export default function GlobalError({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        console.error("Global error:", error);
    }, [error]);

    return (
        <html>
            <body
                style={{
                    margin: 0,
                    fontFamily:
                        '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                    backgroundColor: "#0a0a0a",
                    color: "#fafafa",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    minHeight: "100vh",
                }}
            >
                <div style={{ textAlign: "center", maxWidth: 400, padding: 24 }}>
                    <div
                        style={{
                            fontSize: 48,
                            marginBottom: 16,
                        }}
                    >
                        ⚠️
                    </div>
                    <h1
                        style={{
                            fontSize: 24,
                            fontWeight: 700,
                            marginBottom: 8,
                        }}
                    >
                        Application Error
                    </h1>
                    <p
                        style={{
                            fontSize: 14,
                            color: "#a1a1aa",
                            marginBottom: 24,
                            lineHeight: 1.5,
                        }}
                    >
                        A critical error occurred. Please try refreshing the page.
                    </p>
                    <button
                        onClick={reset}
                        style={{
                            backgroundColor: "#fafafa",
                            color: "#0a0a0a",
                            border: "none",
                            borderRadius: 8,
                            padding: "10px 24px",
                            fontSize: 14,
                            fontWeight: 600,
                            cursor: "pointer",
                        }}
                    >
                        Try Again
                    </button>
                </div>
            </body>
        </html>
    );
}
