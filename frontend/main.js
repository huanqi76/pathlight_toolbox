document.addEventListener("DOMContentLoaded", function () {
const scrapeBtn = document.getElementById('scrapeBtn');
const status = document.getElementById('status');
const navLinks = document.querySelectorAll('.nav-link');
const toolSections = document.querySelectorAll('.tool-section');
const confirmCheckbox = document.getElementById('confirmCheckbox');

confirmCheckbox.addEventListener('change', () => {
  scrapeBtn.disabled = !confirmCheckbox.checked;
});

// Sidebar nav tool switching
function switchTool(toolId) {
  navLinks.forEach(link => link.classList.remove('active'));
  toolSections.forEach(section => section.classList.remove('active'));

  document.querySelector(`[data-tool="${toolId}"]`).classList.add('active');
  document.getElementById(toolId).classList.add('active');
}

navLinks.forEach(link => {
  link.addEventListener('click', (e) => {
    e.preventDefault();
    const toolId = link.getAttribute('data-tool');
    switchTool(toolId);
  });
});

// Scrape button behavior
scrapeBtn.addEventListener('click', async () => {
  scrapeBtn.disabled = true;
  scrapeBtn.textContent = 'Scraping...';

  status.className = 'status loading';
  status.textContent = 'Scraping in progress...';
  status.style.display = 'block';

  try {
    const response = await fetch('/scrape', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    });

    const data = await response.json();

    if (response.ok) {
      status.className = 'status success';
      status.textContent = `${data.message}. Collected ${data.data_count || 'unknown number of'} companies.`;
    } else {
      status.className = 'status error';
      status.textContent = `Error: ${data.detail}`;
    }
  } catch (error) {
    status.className = 'status error';
    status.textContent = `Network error: ${error.message}`;
  } finally {
    scrapeBtn.disabled = false;
    scrapeBtn.textContent = 'Start Scraping';
  }
});
});