import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import security from "eslint-plugin-security";

// Closes R-007 in docs/security/risk-register.md.
//
// eslint-plugin-security adds Node/JS security rules: ReDoS detection,
// non-literal fs paths, non-literal regex, eval-with-expression, etc.
// We use the plugin's flat-config `recommended` preset.
//
// If a rule turns out to be too noisy on this codebase, downgrade the
// specific rule to "warn" or "off" here AND open a register row to track
// the suppression rather than silently disabling.
const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  security.configs.recommended,
  {
    rules: {
      // Tighten the two rules that catch the most-impactful issues for our
      // codebase. The others stay at the plugin's recommended levels.
      "security/detect-eval-with-expression": "error",
      "security/detect-non-literal-require": "error",
    },
  },
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
]);

export default eslintConfig;
