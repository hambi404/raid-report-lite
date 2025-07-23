const API_KEY = "585402d32f384078b03bd0cfe9ecf9b6";
const HEADERS = { "X-API-Key": API_KEY };
const CLAN_ID = "4901284"; // Salty Originalz Clan ID
const VAULT_OF_GLASS_ACTIVITY_HASH = 3881495763; // Gläserne Kammer (normal)

async function fetchClanMembers() {
  const res = await fetch(`https://www.bungie.net/Platform/GroupV2/${CLAN_ID}/Members/`, { headers: HEADERS });
  const data = await res.json();
  return data.Response.results;
}

async function fetchRaidCompletions(membershipId, membershipType) {
  const res = await fetch(`https://www.bungie.net/Platform/Destiny2/${membershipType}/Account/${membershipId}/Character/0/Stats/AggregateActivityStats/`, { headers: HEADERS });
  const data = await res.json();
  const activities = data.Response.activities || [];
  const vog = activities.find(a => a.activityHash === VAULT_OF_GLASS_ACTIVITY_HASH);
  return vog ? vog.values.activityCompletions.basic.value : 0;
}

async function main() {
  const output = document.getElementById("output");
  output.textContent = "Lade Raid-Daten...";

  const members = await fetchClanMembers();

  const raidStats = await Promise.all(members.map(async member => {
    const displayName = member.destinyUserInfo.displayName;
    const membershipId = member.destinyUserInfo.membershipId;
    const membershipType = member.destinyUserInfo.membershipType;

    const completions = await fetchRaidCompletions(membershipId, membershipType);

    return { displayName, completions };
  }));

  output.innerHTML = "";

  raidStats
    .sort((a, b) => b.completions - a.completions)
    .forEach(player => {
      const el = document.createElement("div");
      el.className = "guardian";
      el.textContent = `${player.displayName}: ${player.completions}x Gläserne Kammer`;
      output.appendChild(el);
    });
}

main().catch(err => {
  console.error(err);
  document.getElementById("output").textContent = "Fehler beim Laden der Daten.";
});