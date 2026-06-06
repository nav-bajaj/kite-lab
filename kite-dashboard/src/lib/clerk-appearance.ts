/**
 * Brand appearance for the Clerk <SignIn> / <SignUp> components on the
 * light-locked marketing surfaces. Lichen primary, Outfit type, mist/white
 * surfaces, 8px radius — mirrors the @marketworks/design role tokens.
 * Typed structurally where it's passed to the `appearance` prop (avoids a
 * direct dep on the transitive @clerk/types package).
 */
export const clerkAppearance = {
  variables: {
    colorPrimary: "#14715F", // lichen
    colorText: "#1A1A1A", // ink
    colorTextSecondary: "#737373", // neutral-500
    colorBackground: "#FFFFFF",
    colorInputBackground: "#FFFFFF",
    colorInputText: "#1A1A1A",
    colorDanger: "#A64C42", // semantic negative
    borderRadius: "0.5rem",
    fontFamily: "var(--font-outfit), ui-sans-serif, system-ui, sans-serif",
  },
  elements: {
    card: "shadow-sm border border-[#D4D4D4]",
    headerTitle: "font-[family-name:var(--font-fraunces)]",
    formButtonPrimary: "text-[15px] font-semibold normal-case",
  },
};
