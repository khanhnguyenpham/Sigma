import "@testing-library/jest-dom/vitest";
import { configure } from "@testing-library/react";

// Lazy page imports include charts; transformation in jsdom can exceed one second.
configure({ asyncUtilTimeout: 3000 });
