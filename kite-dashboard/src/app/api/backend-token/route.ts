import { auth } from "@/lib/auth";
import { NextResponse } from "next/server";

/**
 * API route to get a backend JWT token.
 *
 * This verifies the NextAuth session server-side, then requests
 * a backend JWT from the FastAPI server.
 *
 * The frontend should call this after login to get a token
 * for subsequent API calls.
 */
export async function GET() {
  // Verify NextAuth session server-side
  const session = await auth();

  if (!session?.user?.email) {
    return NextResponse.json(
      { error: "Not authenticated" },
      { status: 401 }
    );
  }

  // Request backend token
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  try {
    const response = await fetch(`${apiUrl}/api/auth/token`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email: session.user.email,
        name: session.user.name || "",
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Token request failed" }));
      return NextResponse.json(
        { error: error.detail || "Failed to get backend token" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Failed to get backend token:", error);
    return NextResponse.json(
      { error: "Failed to connect to backend" },
      { status: 503 }
    );
  }
}
