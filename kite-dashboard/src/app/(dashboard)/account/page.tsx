import { UserProfile } from "@clerk/nextjs";

export default function AccountPage() {
  return (
    <div className="flex justify-center py-4">
      <UserProfile
        // Clerk's full-screen account UI: name, email, phone, sign-in methods,
        // sign-out, delete account. Inherits the surrounding theme via
        // ClerkProvider in src/app/layout.tsx.
        path="/account"
        routing="path"
        appearance={{
          elements: {
            rootBox: "w-full max-w-4xl",
            card: "shadow-none border border-border",
          },
        }}
      />
    </div>
  );
}
