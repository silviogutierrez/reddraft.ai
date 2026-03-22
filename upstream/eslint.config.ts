import reactivatedConfig from "reactivated/dist/eslint.config";
import tseslint from "typescript-eslint";

export default tseslint.config(...reactivatedConfig, {
    rules: {
        "react/no-unescaped-entities": ["error", {forbid: [">", '"', "}"]}],
    },
});
