// Cycle manually; leave the server-rendered first result available without JS.
(() => {
    for (const scene of document.querySelectorAll('[data-spotlight]')) {
        const controls = scene.querySelector('.spotlight-controls');
        const button = controls.querySelector('button');
        const cards = Array.from(scene.querySelectorAll('.spotlight-ticket'));
        const status = scene.querySelector('[data-spotlight-status]');
        if (cards.length < 2) continue;
        let index = 0;
        button.addEventListener('click', () => {
            index = (index + 1) % cards.length;
            cards.forEach((card, position) => { card.hidden = position !== index; });
            status.textContent = `Showing result ${index + 1} of ${cards.length}: ${cards[index].getAttribute('aria-label')}`;
        });
        controls.hidden = false;
    }
})();
