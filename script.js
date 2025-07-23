// Dummy-Daten simulieren Clan-Mitglieder und Raid-Clears
const dummyData = [
  { name: 'Spieler1', clears: ['Last Wish', 'Deep Stone Crypt'] },
  { name: 'Spieler2', clears: ['Root of Nightmares'] },
  { name: 'Spieler3', clears: ['Last Wish', 'Root of Nightmares'] },
  { name: 'Spieler4', clears: ['Deep Stone Crypt'] },
  { name: 'Spieler5', clears: [] }
];

const raids = ['Last Wish', 'Deep Stone Crypt', 'Root of Nightmares'];

// Dynamisch Buttons erzeugen
const raidSelection = document.getElementById('raidSelection');
raids.forEach(raid => {
  const btn = document.createElement('button');
  btn.textContent = raid;
  btn.className = 'bg-gray-700 hover:bg-indigo-600 transition text-white font-medium py-3 px-4 rounded-lg shadow';
  btn.onclick = () => showClearedMembers(raid);
  raidSelection.appendChild(btn);
});

function showClearedMembers(raid) {
  const container = document.getElementById('memberList');
  container.innerHTML = ''; // Leeren

  const title = document.createElement('h2');
  title.className = 'text-2xl font-semibold mb-4';
  title.textContent = `Raid: ${raid}`;
  container.appendChild(title);

  const list = document.createElement('ul');
  list.className = 'space-y-2';

  const filtered = dummyData.filter(player => player.clears.includes(raid));
  if (filtered.length === 0) {
    list.innerHTML = '<li class="text-gray-400">Niemand hat diesen Raid gecleart.</li>';
  } else {
    filtered.forEach(player => {
      const li = document.createElement('li');
      li.className = 'bg-gray-800 p-3 rounded-md shadow border border-gray-700';
      li.textContent = player.name;
      list.appendChild(li);
    });
  }

  container.appendChild(list);
}
