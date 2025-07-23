const express = require('express');
const axios = require('axios');
const cors = require('cors');

const API_KEY = '585402d32f384078b03bd0cfe9ecf9b6';
const GROUP_NAME = 'Salty Legendz';
const GROUP_TYPE = 1; // Clan

const app = express();
app.use(cors());

const BUNGIE_BASE = 'https://www.bungie.net/Platform';

app.get('/clan/members', async (req, res) => {
  try {
    const groupSearch = await axios.get(`${BUNGIE_BASE}/GroupV2/Name/${GROUP_NAME}/${GROUP_TYPE}/`, {
      headers: { 'X-API-Key': API_KEY }
    });
    const groupId = groupSearch.data.Response.detail.groupId;

    const membersRes = await axios.get(`${BUNGIE_BASE}/GroupV2/${groupId}/Members/`, {
      headers: { 'X-API-Key': API_KEY }
    });

    const members = membersRes.data.Response.results.map(m => ({
      bungieName: `${m.destinyUserInfo.bungieGlobalDisplayName}#${m.destinyUserInfo.bungieGlobalDisplayNameCode}`,
      membershipId: m.destinyUserInfo.membershipId,
      membershipType: m.destinyUserInfo.membershipType
    }));

    res.json({ members });
  } catch (err) {
    console.error(err.response?.data || err.message);
    res.status(500).json({ error: 'Fehler beim Abrufen der Clanmitglieder' });
  }
});

app.listen(3000, () => {
  console.log('API läuft auf http://localhost:3000');
});
