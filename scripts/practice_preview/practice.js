/* Local preview only: answer keys are in the artifact, never use for graded exams. */
function freshState(count) {
  return {index: 0, selections: Array(count).fill(null), submitted: Array(count).fill(false), flagged: Array(count).fill(false)};
}
function restoreState(value, questions) {
  const state = freshState(questions.length);
  if (!value || typeof value !== 'object') return state;
  if (Number.isInteger(value.index) && value.index >= 0 && value.index < questions.length) state.index = value.index;
  questions.forEach((q, i) => {
    const selected = value.selections?.[i];
    if (Number.isInteger(selected) && selected >= 0 && selected < q.choices.length) {
      state.selections[i] = selected;
      state.submitted[i] = value.submitted?.[i] === true;
    }
    state.flagged[i] = value.flagged?.[i] === true;
  });
  return state;
}
function totals(state, questions) {
  return questions.reduce((result, q, i) => {
    if (state.submitted[i]) {
      result.answered++;
      if (state.selections[i] === q.answer) result.correct++;
    }
    if (state.flagged[i]) result.flagged++;
    return result;
  }, {answered: 0, correct: 0, flagged: 0});
}
function submitAnswer(state) {
  if (state.selections[state.index] === null || state.submitted[state.index]) return false;
  state.submitted[state.index] = true;
  return true;
}
if (typeof module !== 'undefined') module.exports = {freshState, restoreState, totals, submitAnswer};

if (typeof document !== 'undefined') {
  const data = JSON.parse(document.getElementById('question-data').textContent);
  const questions = data.questions;
  const key = 'sat-factory-preview-v1:' + data.source_sha256;
  let stored;
  try { stored = JSON.parse(sessionStorage.getItem(key)); } catch (_) { /* Storage may be unavailable. */ }
  const state = restoreState(stored, questions);
  const $ = id => document.getElementById(id);
  let storageAvailable = true;
  const persist = () => {
    try { sessionStorage.setItem(key, JSON.stringify(state)); }
    catch (_) { storageAvailable = false; }
    $('storage-note').textContent = storageAvailable ? 'Progress stays in this tab. No course records are changed.' : 'Progress lasts until this page reloads. Browser storage is unavailable.';
  };
  const label = i => String.fromCharCode(65 + i);
  function updateProgress() {
    const result = totals(state, questions);
    $('progress').textContent = `${result.answered} of ${questions.length} checked · ${result.correct} correct`;
    $('progress-bar').max = questions.length;
    $('progress-bar').value = result.answered;
    $('jump').replaceChildren();
    questions.forEach((q, i) => {
      const option = document.createElement('option');
      option.value = i;
      option.textContent = `Question ${i + 1}${state.submitted[i] ? ' · checked' : ''}${state.flagged[i] ? ' · marked' : ''}`;
      option.selected = i === state.index;
      $('jump').append(option);
    });
  }
  function render(focus = false) {
    const i = state.index, q = questions[i], checked = state.submitted[i];
    $('workspace').hidden = false;
    $('summary').hidden = true;
    $('question-number').textContent = `Question ${i + 1}`;
    $('metadata').textContent = `${q.difficulty[0].toUpperCase()+q.difficulty.slice(1)} · Source ${q.source_id} · PDF page ${q.page}`;
    $('passage').textContent = q.passage;
    $('passage-panel').hidden = !q.passage;
    $('workspace').classList.toggle('single', !q.passage);
    $('stem').textContent = q.stem;
    $('mark').checked = state.flagged[i];
    $('choices').replaceChildren();
    q.choices.forEach((text, position) => {
      const row = document.createElement('label');
      row.className = 'choice';
      const input = document.createElement('input');
      input.type = 'radio'; input.name = 'answer'; input.value = position;
      input.checked = state.selections[i] === position; input.disabled = checked;
      const copy = document.createElement('span'); copy.textContent = `${label(position)}. ${text}`; copy.className = 'choice-copy';
      // The visible label includes the letter so speech input and screen readers agree.
      row.append(input, copy);
      if (checked && position === q.answer) row.classList.add('correct');
      if (checked && input.checked && position !== q.answer) row.classList.add('incorrect');
      input.addEventListener('change', () => {
        state.selections[i] = position;
        $('check').disabled = false;
        persist();
      });
      $('choices').append(row);
    });
    $('check').disabled = checked || state.selections[i] === null;
    $('check').textContent = checked ? 'Answer checked' : 'Check answer';
    $('feedback').hidden = !checked;
    $('feedback-title').textContent = checked ? (state.selections[i] === q.answer ? `Correct — ${label(q.answer)}` : `Not quite — correct answer: ${label(q.answer)}`) : '';
    $('explanation').textContent = checked ? q.explanation : '';
    $('previous').disabled = i === 0;
    $('next').textContent = i === questions.length - 1 ? 'See summary' : 'Next →';
    updateProgress(); persist();
    if (focus) { $('question-number').focus(); window.scrollTo({top:0, behavior:'instant'}); }
  }
  function showSummary() {
    const result = totals(state, questions);
    $('workspace').hidden = true; $('summary').hidden = false;
    $('summary-text').textContent = `${result.correct} correct out of ${result.answered} checked. ${questions.length-result.answered} unanswered. ${result.flagged} marked for review.`;
    $('summary-questions').replaceChildren();
    questions.forEach((q, i) => {
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'summary-question';
      button.textContent = `${i+1} · ${state.submitted[i] ? (state.selections[i]===q.answer?'Correct':'Incorrect'):'Unanswered'}${state.flagged[i]?' · Marked':''}`;
      button.addEventListener('click', () => {state.index=i; render(true);});
      $('summary-questions').append(button);
    });
    $('summary-title').focus(); window.scrollTo({top:0, behavior:'instant'});
  }
  $('answer-form').addEventListener('submit', event => {
    event.preventDefault();
    if (!submitAnswer(state)) return;
    render();
    $('feedback-title').focus();
  });
  $('mark').addEventListener('change', () => {state.flagged[state.index]=$('mark').checked; updateProgress(); persist();});
  $('previous').addEventListener('click', () => {if(state.index>0){state.index--;render(true);}});
  $('next').addEventListener('click', () => {if(state.index<questions.length-1){state.index++;render(true);}else showSummary();});
  $('jump').addEventListener('change', () => {state.index=Number($('jump').value);render(true);});
  $('show-summary').addEventListener('click', showSummary);
  render();
}
