import "@testing-library/jest-dom/vitest";
import { configure } from "@testing-library/react";

// Lazy page imports include charts; transformation in jsdom can exceed one second.
configure({ asyncUtilTimeout: 3000 });

// jsdom lacks native dialog opening; browser QA checks modal focus and Escape.
HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
HTMLDialogElement.prototype.close = function () { this.removeAttribute("open"); };
