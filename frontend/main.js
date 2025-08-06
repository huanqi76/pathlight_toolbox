document.addEventListener("DOMContentLoaded", function () {
const scrapeBtn = document.getElementById('scrapeBtn');
const showConnectionsBtn = document.getElementById('showConnectionsBtn');
const status = document.getElementById('status');
const navLinks = document.querySelectorAll('.nav-link');
const toolSections = document.querySelectorAll('.tool-section');
const confirmCheckbox = document.getElementById('confirmCheckbox');
const connectionsResults = document.getElementById('connectionsResults');
const connectionsTable = document.getElementById('connectionsTable');

confirmCheckbox.addEventListener('change', () => {
  scrapeBtn.disabled = !confirmCheckbox.checked;
  showConnectionsBtn.disabled = !confirmCheckbox.checked;
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

// Show connections button behavior
showConnectionsBtn.addEventListener('click', async () => {
  showConnectionsBtn.disabled = true;
  showConnectionsBtn.textContent = 'Loading...';

  try {
    const response = await fetch('/connections');
    const data = await response.json();

    if (response.ok) {
      displayConnections(data.connections);
      connectionsResults.style.display = 'block';
    } else {
      status.className = 'status error';
      status.textContent = `Error: ${data.detail}`;
      status.style.display = 'block';
    }
  } catch (error) {
    status.className = 'status error';
    status.textContent = `Network error: ${error.message}`;
    status.style.display = 'block';
  } finally {
    showConnectionsBtn.disabled = false;
    showConnectionsBtn.textContent = 'Show Current Connections';
  }
});

function displayConnections(connections) {
  if (!connections || connections.length === 0) {
    connectionsTable.innerHTML = '<div class="no-connections">No connections found. Run a scrape first to collect data.</div>';
    return;
  }

  const table = document.createElement('table');
  table.className = 'connections-table';
  
  // Create header
  const header = table.createTHead();
  const headerRow = header.insertRow();
  ['LinkedIn Handle', 'Company', 'Date Scraped'].forEach(text => {
    const th = document.createElement('th');
    th.textContent = text;
    headerRow.appendChild(th);
  });

  // Create body
  const tbody = table.createTBody();
  connections.forEach(conn => {
    const row = tbody.insertRow();
    row.insertCell(0).textContent = conn.handle;
    row.insertCell(1).textContent = conn.company;
    row.insertCell(2).textContent = new Date(conn.date_scraped).toLocaleDateString();
  });

  connectionsTable.innerHTML = '';
  connectionsTable.appendChild(table);
}
});