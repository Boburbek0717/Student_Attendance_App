// Progressive enhancement: content stays visible if scripts or animation fail.
(() => {
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (!('IntersectionObserver' in window) || !Element.prototype.animate) return;
    const targets = document.querySelectorAll(
        '.welcome-page .hero-copy, .welcome-page .teacher-portrait, ' +
        '.welcome-page .teacher-introduction, .welcome-page .section-heading, ' +
        '.welcome-page .student-ticket, .welcome-page .portal-banner'
    );
    const played = new WeakSet();
    const running = new Set();
    const observer = new IntersectionObserver(entries => {
        for (const entry of entries) {
            if (!entry.isIntersecting) continue;
            observer.unobserve(entry.target);
            if (preference.matches || played.has(entry.target)) continue;
            played.add(entry.target);
            const animation = entry.target.animate([
                { opacity: 0.65, translate: '0 14px' },
                { opacity: 1, translate: '0 0' }
            ], { duration: 480, easing: 'cubic-bezier(.2,.7,.2,1)' });
            running.add(animation);
            animation.finished.catch(() => {}).finally(() => running.delete(animation));
        }
    }, { threshold: 0.08 });
    function updatePreference() {
        observer.disconnect();
        if (preference.matches) {
            for (const animation of running) animation.cancel();
            running.clear();
        } else {
            for (const target of targets) {
                if (!played.has(target)) observer.observe(target);
            }
        }
    }
    preference.addEventListener('change', updatePreference);
    // Keyboard focus should never wait for an entrance animation.
    document.addEventListener('focusin', event => {
        for (const animation of running) {
            if (animation.effect.target.contains(event.target)) animation.cancel();
        }
    });
    updatePreference();
})();
