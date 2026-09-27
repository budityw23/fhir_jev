import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import tseslint from "typescript-eslint";

export default tseslint.config(
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{ts,tsx,js}"],
    plugins: { "react-hooks": reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "max-len": [
        "error",
        {
          code: 100,
          ignoreStrings: true,
          ignoreTemplateLiterals: true,
          ignoreUrls: true,
          ignoreRegExpLiterals: true,
        },
      ],
    },
  },
  { ignores: ["dist", "node_modules", "src/api/schema.d.ts"] },
);
