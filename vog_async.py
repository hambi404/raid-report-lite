#!/usr/bin/env python3
import asyncio
import time
import argparse
from typing import Dict, Any, List, Tuple
import aiohttp
from aiohttp import ClientSession, TCPConnector
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import orjson as json

BASE = "https://www.bungie.net/Platform"

class BungieError(Exception):
    pass

def dumps(o) -> bytes:
    return json.dumps(o)

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

async def get_char_stats(session: ClientSession, api_key: str, member: Dict[str, Any], char_id: str, raid_hash: int, sem: asyncio.Semaphore) -> int:
    headers = {"X-API-Key": api_key}
    url = f"{BASE}/Destiny2/{member['membershipType']}/Account/{member['membershipId']}/Character/{char_id}/Stats/AggregateActivityStats/"
    try:
        data = await fetch_json_retry(session, url, headers, sem=sem)
    except Exception:
        return 0

    activities = data["Response"].get("activities", []) or []
    total = 0
    for a in activities:
        if a.get("activityHash") == raid_hash:
            total += int(a["values"]["activityCompletions"]["basic"]["value"])
    return total

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--group-id", required=True)
    parser.add_argument("--raid-hash", type=int, default=3881495763)
    parser.add_argument("--concurrency", type=int, default=150)
    parser.add_argument("--out", default="results.json")
    args = parser.parse_args()

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
                stat_tasks.append(get_char_stats(session, args.api_key, member, cid, args.raid_hash, sem))
                owner_map.append(member)

        completions: List[int] = []
        if stat_tasks:
            completions = await asyncio.gather(*stat_tasks)

        member_totals: Dict[str, Dict[str, Any]] = {}
        for member in members:
            member_totals[member["membershipId"]] = {
                "name": member["name"],
                "vog_completions": 0
            }

        for comp, member in zip(completions, owner_map):
            member_totals[member["membershipId"]]["vog_completions"] += comp

        result_list = list(member_totals.values())

        with open(args.out, "wb") as f:
            f.write(dumps(result_list))

    dur = time.perf_counter() - start
    print(f"Fertig in {dur:.2f}s. Ergebnisse in {args.out}")

if __name__ == "__main__":
    asyncio.run(main())