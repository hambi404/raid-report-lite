// script.js

// Beispiel-Daten (Dummy-Daten, später via Bungie API ersetzen)
const raidStats = [
  { name: 'Spieler1', lastWish: 5, dsc: 12, root: 7 },
  { name: 'Spieler2', lastWish: 2, dsc: 7, root: 3 },
  { name: 'Spieler3', lastWish: 8, dsc: 10, root: 5 }
];

// Chart.js Setup
const ctx = document.getElementById('raidChart').getContext('2d');
const labels = raidStats.map(player => player.name);
const raidChart = new Chart(ctx, {
  type: 'bar',
  data: {
    labels: labels,
    datasets: [
      {
        label: 'Last Wish',
        data: raidStats.map(p => p.lastWish),
        backgroundColor: '#f87171'
      },
      {
        label: 'Deep Stone Crypt',
        data: raidStats.map(p => p.dsc),
        backgroundColor: '#60a5fa'
      },
      {
        label: 'Root of Nightmares',
        data: raidStats.map(p => p.root),
        backgroundColor: '#34d399'
      }
    ]
  },
  options: {
    responsive: true,
    plugins: {
      legend: { position: 'top' },
      title: { display: true, text: 'Raid-Kills pro Mitglied' }
    }
  }
});

// Tabelle für Clears pro Raid generieren
function renderRaidTable(data) {
  const table = document.createElement('table');
  table.className = 'min-w-full bg-gray-800 border border-gray-700 text-sm';

  const header = `
    <thead class="bg-gray-700">
      <tr>
        <th class="p-2 border">Name</th>
        <th class="p-2 border">Last Wish</th>
        <th class="p-2 border">Deep Stone Crypt</th>
        <th class="p-2 border">Root of Nightmares</th>
      </tr>
    </thead>
  `;
  const rows = data.map(p => `
    <tr>
      <td class="p-2 border">${p.name}</td>
      <td class="p-2 border text-center">${p.lastWish}</td>
      <td class="p-2 border text-center">${p.dsc}</td>
      <td class="p-2 border text-center">${p.root}</td>
    </tr>
  `).join('');

  table.innerHTML = header + `<tbody>${rows}</tbody>`;
  document.getElementById('raidTable').appendChild(table);
}

renderRaidTable(raidStats);
