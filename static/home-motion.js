// One-shot reveals; content stays visible if JavaScript is unavailable.
(() => {
    const preference = matchMedia('(prefers-reduced-motion: reduce)');
    if (!('IntersectionObserver' in window) || !Element.prototype.animate) return;
    const active = new Set();
    const played = new WeakSet();
    const targets = document.querySelectorAll('.hero-copy, .score-scene, .featured-card, .teacher-feature, .portal-entry, .results-intro, .student-ticket, .auth-composition');
    const observer = new IntersectionObserver(entries => {
        for (const entry of entries) {
            if (!entry.isIntersecting) continue;
            observer.unobserve(entry.target);
            if (preference.matches || played.has(entry.target)) continue;
            played.add(entry.target);
            const animation = entry.target.animate([
                { opacity: .4, translate: '0 24px' },
                { opacity: 1, translate: '0 0' }
            ], { duration: 650, easing: 'cubic-bezier(.16,1,.3,1)' });
            active.add(animation);
            animation.finished.catch(() => {}).finally(() => active.delete(animation));
        }
    }, { threshold: .12 });
    function update() {
        observer.disconnect();
        if (preference.matches) {
            for (const animation of active) animation.cancel();
            active.clear();
        } else for (const target of targets) if (!played.has(target)) observer.observe(target);
    }
    preference.addEventListener('change', update);
    document.addEventListener('focusin', event => {
        for (const animation of active) if (animation.effect.target.contains(event.target)) animation.cancel();
        const card = event.target.closest('.featured-card');
        if (card) card.scrollIntoView({ behavior: 'instant', block: 'nearest', inline: 'nearest' });
    });
    update();
})();
