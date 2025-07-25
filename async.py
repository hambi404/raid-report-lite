#!/usr/bin/env python3
import asyncio
import time
import argparse
from typing import Dict, Any, List, Tuple, Set
import aiohttp
from aiohttp import ClientSession, TCPConnector
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import orjson as json
from datetime import datetime, timezone

BASE = "https://www.bungie.net/Platform"

# ---> Hier alle Raid-Hashes & Namen eintragen
RAIDS: Dict[int, str] = {
    548750096:  "Root of Nightmares",
    3881495763: "Vault of Glass",
    1374392663: "Kingsfall",
    2122313384: "Last Wish",
}

class BungieError(Exception):
    pass

def dumps(o) -> bytes:
    # erlaube non-str keys (zur Sicherheit) – wir serialisieren unten trotzdem selbst als str
    return json.dumps(o, option=json.OPT_NON_STR_KEYS)

def loads(b) -> Any:
    return json.loads(b)

async def fetch_json(session: ClientSession, url: str, headers: Dict[str, str], *, sem: asyncio.Semaphore) -> Dict[str, Any]:
    async with sem:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as r:
            if r.status >= 400:
                text = await r.text()
                raise BungieError(f"HTTP {r.status} for {url} - {text[:200]}")
            data = await r.json(loads=loads)
            if data.get("ErrorStatus") != "Success":
                raise BungieError(f"Bungie API Error {data.get('ErrorStatus')}: {data.get('Message')}")
            return data

@retry(
    reraise=True,
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
    retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError, BungieError)),
)
async def fetch_json_retry(*args, **kwargs):
    return await fetch_json(*args, **kwargs)

async def get_members(session: ClientSession, api_key: str, group_id: str, sem: asyncio.Semaphore) -> List[Dict[str, Any]]:
    url = f"{BASE}/GroupV2/{group_id}/Members/"
    headers = {"X-API-Key": api_key}
    data = await fetch_json_retry(session, url, headers, sem=sem)
    members = []
    for m in data["Response"]["results"]:
        members.append({
            "membershipType": m["destinyUserInfo"]["membershipType"],
            "membershipId": m["destinyUserInfo"]["membershipId"],
            "name": (m.get("bungieNetUserInfo", {}) or {}).get("bungieGlobalDisplayName")
                    or m["destinyUserInfo"].get("displayName")
                    or "Unbekannt"
        })
    return members

async def get_profile_characters(session: ClientSession, api_key: str, member: Dict[str, Any], sem: asyncio.Semaphore) -> Tuple[Dict[str, Any], List[str]]:
    headers = {"X-API-Key": api_key}
    url = f"{BASE}/Destiny2/{member['membershipType']}/Profile/{member['membershipId']}/?components=200"
    try:
        data = await fetch_json_retry(session, url, headers, sem=sem)
    except Exception:
        return member, []
    chars = list((data["Response"].get("characters", {}).get("data") or {}).keys())
    return member, chars

async def get_char_stats_multi(session: ClientSession, api_key: str, member: Dict[str, Any], char_id: str, raid_hashes: Set[int], sem: asyncio.Semaphore) -> Dict[int, int]:
    """
    Holt AggregateActivityStats EINMAL und liefert ein Dict raid_hash -> completions
    für alle gewünschten Raids.
    """
    headers = {"X-API-Key": api_key}
    url = f"{BASE}/Destiny2/{member['membershipType']}/Account/{member['membershipId']}/Character/{char_id}/Stats/AggregateActivityStats/"
    try:
        data = await fetch_json_retry(session, url, headers, sem=sem)
    except Exception:
        return {rh: 0 for rh in raid_hashes}

    activities = data["Response"].get("activities", []) or []
    totals = {rh: 0 for rh in raid_hashes}
    for a in activities:
        rh = a.get("activityHash")
        if rh in totals:
            totals[rh] += int(a["values"]["activityCompletions"]["basic"]["value"])
    return totals

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--group-id", required=True)
    parser.add_argument("--out", default="results.json")
    parser.add_argument("--concurrency", type=int, default=150)
    # Neue Option: mehrere Raids auf einmal (Default: alle bekannten)
    parser.add_argument("--raid-hashes", nargs="*", type=int, help="Liste von Raid Hashes (default: alle bekannten)")
    # Für Rückwärtskompatibilität: einzelner Hash (optional, wenn jemand's gewohnt ist)
    parser.add_argument("--raid-hash", type=int, help="Einzelner Raid Hash (deprecated, nutze --raid-hashes)")
    args = parser.parse_args()

    if args.raid_hashes:
        raid_hashes: Set[int] = set(args.raid_hashes)
    elif args.raid_hash:
        raid_hashes = {args.raid_hash}
    else:
        raid_hashes = set(RAIDS.keys())

    start = time.perf_counter()
    connector = TCPConnector(limit=0, ttl_dns_cache=300)
    sem = asyncio.Semaphore(args.concurrency)

    async with aiohttp.ClientSession(connector=connector, json_serialize=dumps) as session:
        members = await get_members(session, args.api_key, args.group_id, sem)

        prof_tasks = [get_profile_characters(session, args.api_key, m, sem) for m in members]
        prof_results = await asyncio.gather(*prof_tasks)

        stat_tasks = []
        owner_map: List[Dict[str, Any]] = []
        for member, chars in prof_results:
            for cid in chars:
                stat_tasks.append(get_char_stats_multi(session, args.api_key, member, cid, raid_hashes, sem))
                owner_map.append(member)

        char_results: List[Dict[int, int]] = []
        if stat_tasks:
            char_results = await asyncio.gather(*stat_tasks)

        # Aggregation pro Member
        member_totals: Dict[str, Dict[str, Any]] = {}
        for member in members:
            member_totals[member["membershipId"]] = {
                "membershipId": member["membershipId"],
                "name": member["name"],
                # Keys als STRINGS schreiben!
                "completions": {str(rh): 0 for rh in raid_hashes},
                "total": 0
            }

        for comp_dict, member in zip(char_results, owner_map):
            mt = member_totals[member["membershipId"]]
            for rh, count in comp_dict.items():
                mt["completions"][str(rh)] += count

        # total berechnen
        for m in member_totals.values():
            m["total"] = sum(m["completions"].values())

        result = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "group_id": args.group_id,
            # Raids-Block: Keys als STRINGS
            "raids": {str(rh): {"name": RAIDS.get(rh, f"Raid {rh}")} for rh in raid_hashes},
            "members": list(member_totals.values()),
        }

        with open(args.out, "wb") as f:
            f.write(dumps(result))

    dur = time.perf_counter() - start
    print(f"Fertig in {dur:.2f}s. Ergebnisse in {args.out}")

if __name__ == "__main__":
    asyncio.run(main())
