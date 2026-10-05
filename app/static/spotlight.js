// Manual switching preserves the server-rendered links and score breakdowns.
(() => {
    for (const scene of document.querySelectorAll('[data-spotlight]')) {
        const controls = scene.querySelector('.spotlight-controls');
        const buttons = Array.from(controls.querySelectorAll('button'));
        const cards = Array.from(scene.querySelectorAll('.spotlight-ticket'));
        const status = scene.querySelector('[data-spotlight-status]');
        for (const button of buttons) {
            button.addEventListener('click', () => {
                const id = button.getAttribute('aria-controls');
                for (const card of cards) card.hidden = card.id !== id;
                for (const item of buttons) item.setAttribute('aria-pressed', String(item === button));
                status.textContent = button.getAttribute('aria-label').replace(/^Show /, 'Showing ');
            });
        }
        controls.hidden = false;
    }
})();
