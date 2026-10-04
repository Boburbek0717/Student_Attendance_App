(() => {
    "use strict";
    const error = document.getElementById("answer-error");
    if (error) {
        error.focus({preventScroll: true});
        error.scrollIntoView({block: "nearest", behavior: "instant"});
    }
    const feedback = document.getElementById("answer-feedback");
    if (feedback?.dataset.fresh === "true") {
        feedback.focus({preventScroll: true});
        feedback.scrollIntoView({block: "nearest", behavior: "instant"});
    }
    const form = document.getElementById("practice-answer-form");
    const button = document.getElementById("practice-submit");
    if (form && button) {
        form.addEventListener("submit", () => {
            if (!form.checkValidity()) return;
            button.disabled = true;
            button.textContent = "Checking answer…";
            button.setAttribute("aria-busy", "true");
        });
        window.addEventListener("pageshow", () => {
            button.disabled = false;
            button.textContent = "Check answer →";
            button.removeAttribute("aria-busy");
        });
    }
})();
