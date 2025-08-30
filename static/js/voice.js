document.addEventListener('DOMContentLoaded', () => {
  const startBtn = document.getElementById('start-btn');
  if (!startBtn) return;

  startBtn.addEventListener('click', async () => {
    try {
      const res = await fetch('/api/voice/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: window.AGENT_ID })
      });
      const data = await res.json();
      console.log('Received token', data);
    } catch (err) {
      console.error('Failed to get token', err);
    }
  });
});
