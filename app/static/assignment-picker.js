(() => {
    const search = document.getElementById('assignment-search');
    const difficulty = document.getElementById('assignment-difficulty');
    const count = document.getElementById('assignment-count');
    const choices = [...document.querySelectorAll('[data-question-choice]')];
    function refresh() {
        const query = search.value.trim().toLowerCase();
        for (const row of choices) {
            const matches = (!difficulty.value || row.dataset.difficulty === difficulty.value) &&
                (row.dataset.category + ' ' + row.textContent).toLowerCase().includes(query);
            row.hidden = !matches;
            row.style.display = matches ? '' : 'none';
        }
        count.textContent = `${choices.filter(row => row.querySelector('input').checked).length} selected · ${choices.filter(row => !row.hidden).length} shown. Maximum 50; hidden selections stay selected.`;
    }
    search.addEventListener('input', refresh);
    difficulty.addEventListener('change', refresh);
    for (const row of choices) row.addEventListener('change', refresh);
    refresh();
})();
