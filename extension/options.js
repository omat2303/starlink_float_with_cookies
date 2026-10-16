const input = document.getElementById('token');
const msg = document.getElementById('msg');

chrome.storage.local.get('ingestToken').then(({ ingestToken }) => {
  input.value = ingestToken || '';
});

document.getElementById('save').onclick = async () => {
  await chrome.storage.local.set({ ingestToken: input.value.trim() });
  msg.textContent = 'Guardado.';
};
