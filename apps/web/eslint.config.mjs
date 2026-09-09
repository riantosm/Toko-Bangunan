import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
  {
    rules: {
      // Our client components load data in a mount effect (fetch, or a cookie
      // read that must happen post-hydration). setState there lands after an
      // await, not synchronously — keep this visible as a warning, not a build
      // break.
      "react-hooks/set-state-in-effect": "warn",
    },
  },
]);

export default eslintConfig;
