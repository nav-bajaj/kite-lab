/**
 * Brand appearance for the Clerk <SignIn> / <SignUp> components. Lichen
 * primary, Outfit type, white surfaces, 8px radius — mirrors the
 * @marketworks/design Mint tokens. Literal hexes on purpose: Clerk derives
 * hover/shade colors from these values, so var() references would break its
 * color math — the widget stays Mint-branded inside palette-themed shells
 * (standard embedded-widget behavior).
 * Typed structurally where it's passed to the `appearance` prop (avoids a
 * direct dep on the transitive @clerk/types package).
 */
export const clerkAppearance = {
  variables: {
    colorPrimary: "#0C7A62", // lichen (vibrance pass 2026.07.22)
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
