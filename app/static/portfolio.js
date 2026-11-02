(() => {
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const reduced = () => motion.matches;

    // Entrances: each section's parts arrive once, in reading order.
    const revealed = [...document.querySelectorAll('[data-reveal], [data-reveal-group]')];
    document.querySelectorAll('[data-reveal-group]').forEach((group) => {
        [...group.children].forEach((child, index) => { child.style.transitionDelay = `${index * 70}ms`; });
    });
    const show = (element) => element.classList.add('is-in');
    if ('IntersectionObserver' in window) {
        // A picture that opens from a clip is watched through its section: a fully clipped box never intersects.
        const watched = new Map(revealed.map((element) => [element.closest('.pf-platform__plate') ? element.parentElement : element, element]));
        const observer = new IntersectionObserver((entries) => {
            for (const entry of entries) {
                if (entry.isIntersecting) { show(watched.get(entry.target)); observer.unobserve(entry.target); }
            }
        }, { rootMargin: '0px 0px -12% 0px', threshold: 0.08 });
        watched.forEach((element, target) => observer.observe(target));
    } else {
        revealed.forEach(show);
    }

    // Rolling figures: each digit rolls to its value once; the real number stays readable.
    const rolls = [...document.querySelectorAll('[data-roll]')];
    rolls.forEach((element) => {
        const value = element.textContent.trim();
        const said = Object.assign(document.createElement('span'), { className: 'sr-only', textContent: value });
        const shown = Object.assign(document.createElement('span'), { className: 'pf-roll' });
        shown.setAttribute('aria-hidden', 'true');
        let column = 0;
        for (const character of value) {
            if (!/\d/.test(character)) {
                const mark = Object.assign(document.createElement('span'), { className: 'pf-roll__mark' });
                mark.dataset.d = character;
                shown.append(mark);
                continue;
            }
            // Digits are drawn from data-d, so the visible text stays the real figure.
            const col = Object.assign(document.createElement('span'), { className: 'pf-roll__col' });
            col.dataset.d = character;
            const strip = Object.assign(document.createElement('span'), { className: 'pf-roll__strip' });
            strip.style.transform = `translateY(${-Number(character)}em)`;
            strip.style.transitionDelay = `${column++ * 70}ms`;
            for (let digit = 0; digit < 10; digit++) {
                const cell = document.createElement('span');
                cell.dataset.d = digit;
                strip.append(cell);
            }
            col.append(strip);
            shown.append(col);
        }
        element.replaceChildren(said, shown);
    });
    if ('IntersectionObserver' in window) {
        const rollObserver = new IntersectionObserver((entries) => {
            for (const entry of entries) {
                if (entry.isIntersecting) {
                    entry.target.querySelectorAll('.pf-roll').forEach(show);
                    rollObserver.unobserve(entry.target);
                }
            }
        }, { rootMargin: '0px 0px -15% 0px' });
        rolls.forEach((element) => rollObserver.observe(element));
    } else {
        document.querySelectorAll('.pf-roll').forEach(show);
    }

    // The live thing: set a target on the 400–1600 scale and see who reached it.
    const target = document.querySelector('[data-target]');
    if (target) {
        const input = target.querySelector('input');
        const output = target.querySelector('output');
        const result = document.getElementById('pf-target-result');
        const dots = [...target.querySelectorAll('.pf-target__dot')];
        const rows = [...document.querySelectorAll('[data-result]')];
        const count = rows.length;
        const scale = (total) => `${(Number(total) - 400) / 12}%`;
        dots.forEach((dot, index) => {
            dot.style.left = scale(dot.dataset.total);
            dot.style.transitionDelay = `${120 + index * 60}ms`;
        });
        // Each row's bar shows its total on the same 400–1600 scale as the slider.
        rows.forEach((row, index) => {
            const bar = row.querySelector('[data-bar]');
            bar.style.width = scale(row.dataset.total);
            bar.style.transitionDelay = `${200 + index * 70}ms, 0ms`;
        });
        const update = () => {
            const goal = Number(input.value);
            const reached = rows.filter((row) => Number(row.dataset.total) >= goal).length;
            output.value = goal;
            rows.forEach((row) => row.classList.toggle('is-below', Number(row.dataset.total) < goal));
            dots.forEach((dot) => dot.classList.toggle('is-below', Number(dot.dataset.total) < goal));
            const strong = document.createElement('strong');
            if (reached === 0) {
                strong.textContent = 'Nobody yet';
                result.replaceChildren(strong, ` has reached ${goal}. Be the first.`);
            } else {
                strong.textContent = `${reached} of ${count}`;
                result.replaceChildren(strong, ` students reached ${goal} or higher.`);
            }
        };
        input.addEventListener('input', update);
        update();
    }

    // Platform tabs: one plate and one description at a time.
    const tabs = document.querySelector('[data-tabs]');
    if (tabs) {
        const buttons = [...tabs.querySelectorAll('[role="tab"]')];
        const plates = [...document.querySelectorAll('[data-plate]')];
        const select = (button, focus) => {
            buttons.forEach((other) => {
                const active = other === button;
                other.setAttribute('aria-selected', String(active));
                other.tabIndex = active ? 0 : -1;
                document.getElementById(other.getAttribute('aria-controls')).hidden = !active;
            });
            plates.forEach((plate) => plate.classList.toggle('is-shown', plate.dataset.plate === button.dataset.tab));
            if (focus) button.focus();
        };
        buttons.forEach((button, index) => {
            button.addEventListener('click', () => select(button, false));
            button.addEventListener('keydown', (event) => {
                const step = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
                if (event.key === 'Home' || event.key === 'End') {
                    event.preventDefault();
                    select(buttons[event.key === 'Home' ? 0 : buttons.length - 1], true);
                } else if (step) {
                    event.preventDefault();
                    select(buttons[(index + step + buttons.length) % buttons.length], true);
                }
            });
        });
        select(buttons.find((button) => button.getAttribute('aria-selected') === 'true') || buttons[0], false);
    }

    // Two clocks: where the teacher is and where the students are.
    const clocks = [...document.querySelectorAll('[data-clock]')];
    const tick = () => clocks.forEach((clock) => {
        try {
            clock.textContent = new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: clock.dataset.clock }).format(new Date());
        } catch { /* keep the written time zone */ }
    });
    if (clocks.length) { tick(); setInterval(tick, 30000); }

    // The moving picture: the river photograph settles slowly as it passes.
    const drift = document.querySelector('[data-drift]');
    if (drift && 'IntersectionObserver' in window) {
        let visible = false, frame = 0;
        const place = () => {
            frame = 0;
            if (reduced()) { drift.style.transform = ''; return; }
            const box = drift.parentElement.getBoundingClientRect();
            const height = window.innerHeight;
            const progress = Math.min(1, Math.max(0, (height - box.top) / (height + box.height)));
            drift.style.transform = `translateY(${(0.5 - progress) * 48}px) scale(${1.14 - 0.14 * progress})`;
        };
        const request = () => { if (visible && !frame) frame = requestAnimationFrame(place); };
        new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; request(); }).observe(drift.parentElement);
        window.addEventListener('scroll', request, { passive: true });
        window.addEventListener('resize', request);
        motion.addEventListener('change', place);
    }

    // The close: the back of the card rises out of its frame as the page ends.
    const back = document.querySelector('.pf-back__card');
    if (back && 'IntersectionObserver' in window) {
        let visible = false, frame = 0;
        const place = () => {
            frame = 0;
            if (reduced()) { back.style.transform = ''; return; }
            const box = back.parentElement.getBoundingClientRect();
            const progress = Math.min(1, Math.max(0, (window.innerHeight - box.top) / box.height));
            back.style.transform = `translateY(${(1 - progress) * 32}%)`;
        };
        const request = () => { if (visible && !frame) frame = requestAnimationFrame(place); };
        new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; request(); }).observe(back.parentElement);
        window.addEventListener('scroll', request, { passive: true });
        window.addEventListener('resize', request);
        motion.addEventListener('change', place);
        place();
    }
})();
