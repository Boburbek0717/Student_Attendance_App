(() => {
    const search = document.getElementById('assignment-search');
    const difficulty = document.getElementById('assignment-difficulty');
    const count = document.getElementById('assignment-count');
    const choices = [...document.querySelectorAll('[data-question-choice]')];
    const categories = [...document.querySelectorAll('[data-assignment-category]')].map(section => ({
        section,
        toggle: section.querySelector('[data-select-category]'),
        rows: [...section.querySelectorAll('[data-question-choice]')],
    }));
    function refresh() {
        const query = search.value.trim().toLowerCase();
        for (const row of choices) {
            const matches = (!difficulty.value || row.dataset.difficulty === difficulty.value) &&
                (row.dataset.category + ' ' + row.textContent).toLowerCase().includes(query);
            row.hidden = !matches;
            row.style.display = matches ? '' : 'none';
        }
        const selected = choices.filter(row => row.querySelector('input').checked).length;
        count.textContent = `${selected} selected · ${choices.filter(row => !row.hidden).length} shown. Maximum 50; hidden selections stay selected.` +
            (selected > 50 ? ` Deselect ${selected - 50} questions before assigning.` : '');
        for (const {section, toggle, rows} of categories) {
            const checked = rows.filter(row => row.querySelector('input').checked).length;
            toggle.checked = checked === rows.length;
            toggle.indeterminate = checked > 0 && checked < rows.length;
            section.hidden = rows.every(row => row.hidden);
        }
        if (choices.length) choices[0].querySelector('input').setCustomValidity(
            selected > 50 ? 'Select no more than 50 questions.' : selected === 0 ? 'Select at least one question.' : '');
    }
    search.addEventListener('input', refresh);
    difficulty.addEventListener('change', refresh);
    for (const row of choices) row.addEventListener('change', refresh);
    for (const {section, toggle, rows} of categories) {
        section.querySelector('[data-category-control]').hidden = false;
        toggle.addEventListener('change', () => {
            for (const row of rows) row.querySelector('input').checked = toggle.checked;
            refresh();
        });
    }
    // A filtered-out question cannot receive browser validation focus.
    if (choices.length) choices[0].querySelector('input').addEventListener('invalid', () => {
        search.value = '';
        difficulty.value = '';
        refresh();
    });
    refresh();
})();
