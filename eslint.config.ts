import path from "path";

import {includeIgnoreFile} from "@eslint/compat";
import tseslint from "typescript-eslint";

import upstreamConfig from "./upstream/eslint.config";

export default tseslint.config(
    includeIgnoreFile(path.resolve(import.meta.dirname, ".gitignore")),
    ...upstreamConfig,
);
