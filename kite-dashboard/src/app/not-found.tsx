import Link from "next/link";
import { FileQuestion, Home } from "lucide-react";

export default function NotFound() {
    return (
        <div className="flex min-h-screen items-center justify-center bg-background">
            <div className="mx-auto max-w-md text-center">
                {/* Icon */}
                <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-muted">
                    <FileQuestion className="h-10 w-10 text-muted-foreground" />
                </div>

                {/* 404 text */}
                <p className="mb-2 text-sm font-medium text-muted-foreground">404</p>
                <h1 className="mb-2 text-3xl font-bold tracking-tight">
                    Page Not Found
                </h1>
                <p className="mb-8 text-muted-foreground">
                    The page you&apos;re looking for doesn&apos;t exist or has been moved.
                </p>

                {/* Actions */}
                <div className="flex justify-center gap-3">
                    <Link
                        href="/"
                        className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 transition-colors"
                    >
                        <Home className="h-4 w-4" />
                        Go home
                    </Link>
                </div>
            </div>
        </div>
    );
}
