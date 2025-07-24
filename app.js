const API_KEY = "585402d32f384078b03bd0cfe9ecf9b6";
const GROUP_ID = "4901284";

const BASE_URL = "https://www.bungie.net/Platform";
const VOG_HASHES = [1485585878, 1681562271, 3022541210, 3711931140, 3881495763]; // Vault of Glass

async function fetchJson(url) {
  const res = await fetch(url, {
    headers: { "X-API-Key": API_KEY }
  });
  return res.json();
}

async function getClanMembers() {
  const data = await fetchJson(`${BASE_URL}/GroupV2/${GROUP_ID}/Members/`);
  return data.Response.results.map(m => ({
    name: m.bungieNetUserInfo?.bungieGlobalDisplayName || m.destinyUserInfo.displayName,
    membershipId: m.destinyUserInfo.membershipId,
    membershipType: m.destinyUserInfo.membershipType
  }));
}

async function getCharacters(membershipType, membershipId) {
  const profile = await fetchJson(`${BASE_URL}/Destiny2/${membershipType}/Profile/${membershipId}/?components=200`);
  return Object.keys(profile.Response.characters.data || {});
}

async function getVoGCompletions(membershipType, membershipId, charId) {
  const stats = await fetchJson(`${BASE_URL}/Destiny2/${membershipType}/Account/${membershipId}/Character/${charId}/Stats/AggregateActivityStats/`);
  if (stats.ErrorStatus !== "Success") return 0;

  const activities = stats.Response.activities || [];
  return activities
    .filter(a => VOG_HASHES.includes(a.activityHash))
    .reduce((sum, a) => sum + a.values.activityCompletions.basic.value, 0);
}

async function loadData() {
  const container = document.getElementById('clan-container');
  container.innerHTML = "<p>Lade Clan-Daten...</p>";

  const members = await getClanMembers();
  container.innerHTML = "";

  for (const member of members) {
    const charIds = await getCharacters(member.membershipType, member.membershipId);

    const charData = [];
    for (const charId of charIds) {
      const completions = await getVoGCompletions(member.membershipType, member.membershipId, charId);
      charData.push({ charId, completions });
    }

    const card = document.createElement('div');
    card.className = "bg-gray-800 p-4 rounded-lg shadow";
    card.innerHTML = `
      <h2 class="text-xl font-bold mb-2">${member.name}</h2>
      <ul>
        ${charData.map(c => `<li>Char ID: <code>${c.charId}</code> – <span class="text-green-400 font-semibold">${c.completions}</span> Abschlüsse</li>`).join('')}
      </ul>
    `;
    container.appendChild(card);
  }
}

loadData();
