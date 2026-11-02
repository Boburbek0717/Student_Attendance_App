/* Render escaped question text locally. Never enable trusted HTML or URLs. */
(() => {
    "use strict";
    if (typeof renderMathInElement !== "function") return;
    document.querySelectorAll("[data-math]").forEach(element => {
        if (!/\\\(|\\\[/.test(element.textContent)) return;
        renderMathInElement(element, {
            delimiters: [
                {left: "\\[", right: "\\]", display: true},
                {left: "\\(", right: "\\)", display: false}
            ],
            trust: false,
            strict: "error",
            throwOnError: false,
            maxExpand: 100,
            maxSize: 10,
            errorCallback: () => {} // Do not log question content.
        });
        // The offset highlighter must not replace generated math/MathML nodes.
        if (element.querySelector(".katex, .katex-error")) element.dataset.mathRendered = "true";
    });
})();
