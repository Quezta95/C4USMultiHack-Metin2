const $ = id => document.getElementById(id);
let selected = null, previewUrl = null, generation = 0;
const resetResults = () => {
  for (const key of ['raven', 'map']) {
    $(key + '-status').textContent = '—';
    $(key + '-status').className = 'pill';
    $(key + '-detail').textContent = 'Oczekiwanie na analizę';
  }
};
function selectFile(file) {
  if (!file) return;
  generation++;
  resetResults();
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  selected = null;
  $('preview').hidden = true;
  $('placeholder').hidden = false;
  $('change').hidden = true;
  $('analyze').disabled = true;
  $('filename').textContent = 'Nie wybrano pliku';
  if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type) || file.size > 20 * 1024 * 1024 || !file.size) {
    $('status').textContent = 'Wybierz plik PNG, JPG lub WEBP o rozmiarze do 20 MB.';
    return;
  }
  selected = file;
  previewUrl = URL.createObjectURL(file);
  $('preview').src = previewUrl;
  $('preview').hidden = false;
  $('placeholder').hidden = true;
  $('change').hidden = false;
  $('filename').textContent = file.name;
  $('analyze').disabled = false;
  $('status').textContent = 'Obraz gotowy do analizy.';
}
$('choose').onclick = $('change').onclick = () => $('file').click();
$('file').onchange = e => { selectFile(e.target.files[0]); e.target.value = ''; };
for (const event of ['dragenter', 'dragover']) $('drop').addEventListener(event, e => { e.preventDefault(); $('drop').classList.add('dragging'); });
for (const event of ['dragleave', 'drop']) $('drop').addEventListener(event, e => { e.preventDefault(); $('drop').classList.remove('dragging'); });
$('drop').addEventListener('drop', e => selectFile(e.dataTransfer.files[0]));
$('analyze').onclick = async () => {
  if (!selected) return;
  const current = ++generation;
  $('analyze').disabled = true;
  $('status').textContent = 'Trwa analiza obrazu…';
  resetResults();
  try {
    const response = await fetch('/api/analyze', {method: 'POST', headers: {'Content-Type': 'application/octet-stream'}, body: selected});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Analiza nie powiodła się.');
    if (current !== generation) return;
    for (const [key, result] of [['raven', data.raven_visible], ['map', data.map_completed]]) {
      $(key + '-status').textContent = result.detected ? 'WYKRYTO' : 'BRAK';
      $(key + '-status').className = 'pill ' + (result.detected ? 'found' : 'missing');
      $(key + '-detail').textContent = `Dopasowanie: ${(result.score * 100).toFixed(1)}%`;
    }
    $('status').textContent = 'Analiza zakończona.';
  } catch (err) {
    if (current === generation) $('status').textContent = err.message || 'Nie udało się połączyć z analizatorem.';
  } finally {
    if (current === generation) $('analyze').disabled = !selected;
  }
};
