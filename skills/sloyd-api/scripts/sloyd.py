#!/usr/bin/env python3
"""Sloyd client for agents without the Sloyd MCP server. Standard library only.

Credentials come from SLOYD_CLIENT_ID / SLOYD_CLIENT_SECRET in the environment, or from a
.env file in the current folder (written by `setup`). Never pass them on the command line.

  sloyd.py setup                              # ask for the key, test it, save it to .env
  sloyd.py check                              # "credentials: ok" and the balance, nothing secret
  sloyd.py tool generate_3d_from_text '{"prompt": "a gumdrop platform"}'   # any Sloyd MCP tool
  sloyd.py balance
  sloyd.py estimate plan.json                 # credits a plan will cost vs. your balance
  sloyd.py text-to-3d "a gumdrop platform" --style Roblox --faces 4000 --texture 1k
  sloyd.py retexture <jobId> "mint green candy glaze"
  sloyd.py skybox "pastel candy land sky" --style CozyMobile
  sloyd.py job <jobId> --wait                 # poll until done, print outputs
  sloyd.py download <jobId> out.glb
  sloyd.py run plan.json --out roblox-assets  # submit a plan, max 5 concurrent jobs

Endpoints and behaviour follow Sloyd's API docs (api-dashboard/documentation):
create returns {"jobId"}; GET /jobs/{id} until status is success or error;
402 = not enough credits (nothing charged); 429 = more than 5 concurrent jobs on the key.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

API = os.environ.get("SLOYD_API_URL", "https://api.sloyd.ai/api")
MCP_URL = os.environ.get("SLOYD_MCP_URL", "https://api.sloyd.ai/api/mcp")
BUCKET = "https://storage.googleapis.com/ai-services-quality/jobs"
MAX_CONCURRENT = 5

# Credits per request, from https://www.sloyd.ai/api/pricing (USD 1 = 75 credits).
# 3D: 10 base mesh, +5 text input, +10 multiple images, +10 texturing, +5 quads, +10 at 500K+ faces.
FLAT_COSTS = {"retexture": 15, "split-to-parts": 40, "text-to-worldbox": 25, "skybox-from-image": 25,
              "skybox-edit": 25, "text-to-image": 10, "image-edit": 15, "image-upload": 0}


def cost_of(kind, body):
    if kind in FLAT_COSTS:
        return FLAT_COSTS[kind]
    cost = 10
    if kind == "text-to-3d":
        cost += 5
    if kind == "multi-image-to-3d":
        cost += 10
    if body.get("textureResolution", "auto") != "none":
        cost += 10
    if body.get("topology") == "quads":
        cost += 5
    if int(body.get("targetFaceCount") or 0) >= 500000:
        cost += 10
    return cost


class SloydError(Exception):
    def __init__(self, status, body):
        super().__init__(f"HTTP {status}: {body}")
        self.status = status
        self.body = body


def load_dotenv(path=".env"):
    """Read SLOYD_* keys from .env in the current folder. Real environment variables win."""
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip().removeprefix("export ").strip()
            val = val.strip().strip('"').strip("'")
            if key.startswith("SLOYD_") and val and not os.environ.get(key):
                os.environ[key] = val


def credentials():
    load_dotenv()
    cid = os.environ.get("SLOYD_CLIENT_ID", "").strip()
    secret = os.environ.get("SLOYD_CLIENT_SECRET", "").strip()
    if not cid or not secret:
        sys.exit(
            "No Sloyd API key found. In this folder, run:\n"
            f"  {'python' if os.name == 'nt' else 'python3'} {sys.argv[0]} setup\n"
            "(or set SLOYD_CLIENT_ID and SLOYD_CLIENT_SECRET)."
        )
    return {"x-client-id": cid, "x-client-secret": secret}


def mcp_tool(name, arguments):
    """Call one Sloyd MCP tool over plain HTTPS and return its result payload."""
    headers = credentials()
    headers.update({"Content-Type": "application/json", "Accept": "application/json, text/event-stream"})
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": arguments}}
    req = urllib.request.Request(MCP_URL, data=json.dumps(body).encode(), method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode()
    except urllib.error.HTTPError as err:
        raise SloydError(err.code, err.read().decode(errors="replace")) from None
    payload = None
    for line in raw.splitlines():
        if line.startswith("data:"):
            payload = json.loads(line[5:])
    if payload is None:
        payload = json.loads(raw)
    if "error" in payload:
        raise SloydError(None, payload["error"])
    result = payload["result"]
    if result.get("isError"):
        text = " ".join(c.get("text", "") for c in result.get("content", []))
        raise SystemExit(f"Sloyd tool error: {text}")
    if "structuredContent" in result:
        return result["structuredContent"]
    text = "".join(c.get("text", "") for c in result.get("content", []))
    try:
        return json.loads(text)
    except ValueError:
        return {"text": text}


def cmd_setup():
    """Ask for the key, test it, save it to .env here, and keep .env out of git."""
    import getpass

    print("Paste your key from https://api-dashboard.sloyd.ai -> API Keys.")
    cid = input("Client ID: ").strip().strip('"\'')
    secret = getpass.getpass("Client Secret (hidden, nothing shows while you paste): ").strip().strip('"\'')
    if not cid or not secret:
        sys.exit("Both the Client ID and the Client Secret are needed. Run setup again.")
    os.environ["SLOYD_CLIENT_ID"], os.environ["SLOYD_CLIENT_SECRET"] = cid, secret
    try:
        have = balance()
    except SloydError as err:
        if err.status == 401:
            sys.exit("Sloyd rejected this key. Copy the Client ID and Client Secret again and rerun setup. "
                     "If you lost the secret, generate a new key.")
        raise
    lines = []
    if os.path.isfile(".env"):
        with open(".env", encoding="utf-8") as fh:
            lines = [l for l in fh.read().splitlines() if not l.strip().startswith(("SLOYD_CLIENT_ID", "SLOYD_CLIENT_SECRET"))]
    lines += [f"SLOYD_CLIENT_ID={cid}", f"SLOYD_CLIENT_SECRET={secret}"]
    with open(".env", "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    ignored = False
    if os.path.isfile(".gitignore"):
        with open(".gitignore", encoding="utf-8") as fh:
            ignored = any(l.strip() in (".env", "/.env", ".env*", ".env.*") for l in fh)
    if not ignored:
        with open(".gitignore", "a", encoding="utf-8") as fh:
            fh.write("\n# Sloyd API key (never commit)\n.env\n")
    print(f"\nDone. Your key works and is saved in {os.path.abspath('.env')}")
    print(".env is in .gitignore, so it will not be committed.")
    print(f"Credit balance: {have}")
    if have < 25:
        print("You need credits before you can generate: https://api-dashboard.sloyd.ai -> Usage & Billing.")
    return 0


def cmd_check():
    try:
        have = balance()
    except SloydError as err:
        if err.status == 401:
            sys.exit("credentials: rejected. Run setup again with a working key.")
        raise
    print("credentials: ok")
    print(f"balance: {have} credits")
    return 0 if have > 0 else 1


def request(method, path, body=None):
    headers = credentials()
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(API + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as err:
        raw = err.read().decode(errors="replace")
        try:
            parsed = json.loads(raw)
        except ValueError:
            parsed = raw
        raise SloydError(err.code, parsed) from None


def balance():
    return request("GET", "/user/api-access/balance").get("balance", 0)


def create(kind, body, retries_429=30):
    """POST /jobs/<kind>. Waits and retries on 429 (concurrency cap); raises on 402."""
    for _ in range(retries_429):
        try:
            return request("POST", f"/jobs/{kind}", body)["jobId"]
        except SloydError as err:
            if err.status == 429:
                time.sleep(20)
                continue
            if err.status == 402:
                b = err.body if isinstance(err.body, dict) else {}
                raise SystemExit(
                    f"402 Payment Required: need {b.get('required')} credits, have {b.get('available')}. "
                    "Top up at https://api-dashboard.sloyd.ai and retry; nothing was charged."
                ) from None
            raise
    raise SystemExit("Still rate limited (429) after waiting. Another process may be holding 5 jobs.")


def outputs_for(job):
    """Same output shape as the MCP get_job tool."""
    if job.get("status") not in ("success", "completed"):
        return None
    flat = job.get("flatBoxData")
    if flat:
        return {
            "cubemapFaceUrls": [l["url"] for l in flat.get("layers", []) if l.get("usage") == "color"],
            "panoramaUrl": flat.get("panoramaUrl"),
        }
    service = (job.get("service") or "").upper()
    if "IMAGE" in service and "3D" not in service:
        return {"imageUrl": f"{BUCKET}/{job['id']}.webp"}
    return {"glbUrl": f"{BUCKET}/{job['id']}.glb"}


def get_job(job_id):
    job = request("GET", f"/jobs/{job_id}")
    status = job.get("status")
    return {
        "jobId": job.get("id", job_id),
        "status": status,
        "done": status in ("success", "error", "completed", "failed"),
        "errorMessage": job.get("errorMessage"),
        "service": job.get("service"),
        "outputs": outputs_for(job),
    }


def wait_job(job_id, interval=10, timeout=1200):
    start = time.time()
    while True:
        job = get_job(job_id)
        if job["done"]:
            return job
        if time.time() - start > timeout:
            raise SystemExit(f"Timed out waiting for {job_id}")
        time.sleep(interval)


def download(url, dest):
    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
    with urllib.request.urlopen(url, timeout=300) as resp, open(dest, "wb") as out:
        out.write(resp.read())
    return dest


def plan_jobs(plan):
    """A plan is the game-designer asset list: {"style": {...}, "assets": [...], "skybox": {...}}."""
    style = plan.get("style", {})
    jobs = []
    for a in plan.get("assets", []):
        body = {
            "prompt": f"{a['prompt']}, {style['promptSuffix']}" if style.get("promptSuffix") else a["prompt"],
            "genStyleId": a.get("genStyleId") or style.get("genStyleId", "Auto"),
            "topology": "triangles",
            "targetFaceCount": a.get("triBudget", 10000),
            "textureResolution": a.get("textureResolution", "1k"),
        }
        jobs.append({"name": a["name"], "kind": "text-to-3d", "body": body})
    sky = plan.get("skybox")
    if sky:
        jobs.append({"name": "Sky", "kind": "text-to-worldbox",
                     "body": {"prompt": sky["prompt"], "genStyleId": sky.get("genStyleId", style.get("genStyleId", "Auto"))}})
    return jobs


def variant_jobs(plan, base_job_ids):
    """Retexture jobs for skin variants; each needs its base asset's finished jobId."""
    jobs = []
    for v in plan.get("variants", []):
        base_id = base_job_ids.get(v["base"])
        jobs.append({"name": v["name"], "kind": "retexture", "base": v["base"],
                     "body": {"jobId": base_id, "prompt": v["prompt"], "textureResolution": v.get("textureResolution", "1k")}})
    return jobs


def plan_cost(plan):
    jobs = plan_jobs(plan) + variant_jobs(plan, {})
    return jobs, sum(cost_of(j["kind"], j["body"]) for j in jobs)


def cmd_estimate(args):
    jobs, total = plan_cost(json.load(open(args.plan)))
    have = balance()
    print(json.dumps({"jobs": len(jobs), "credits": total, "usd": round(total / 75, 2), "balance": have,
                      "enough": have >= total}, indent=2))
    return 0 if have >= total else 1


def cmd_run(args):
    """Submit a plan with at most 5 jobs in flight; download results; write manifest.json."""
    plan = json.load(open(args.plan))
    jobs, total = plan_cost(plan)
    have = balance()
    if have < total:
        sys.exit(f"Plan needs {total} credits, balance is {have}. Top up at https://api-dashboard.sloyd.ai.")
    os.makedirs(os.path.join(args.out, "raw"), exist_ok=True)
    # Submitted jobIds are saved immediately, so an interrupted run resumes without paying twice.
    state_path = os.path.join(args.out, "run_state.json")
    state = json.load(open(state_path)) if os.path.isfile(state_path) else {}

    def save_state():
        with open(state_path, "w") as fh:
            json.dump(state, fh, indent=2)

    pending, running, done = [], {}, []
    for j in plan_jobs(plan):
        if j["name"] in state:
            j["jobId"] = state[j["name"]]
            running[j["jobId"]] = j
            print(f"resuming {j['name']} -> {j['jobId']}", flush=True)
        else:
            pending.append(j)
    waiting_variants = variant_jobs(plan, {})
    for v in list(waiting_variants):
        if v["name"] in state:
            v["jobId"] = state[v["name"]]
            running[v["jobId"]] = v
            waiting_variants.remove(v)
            print(f"resuming {v['name']} -> {v['jobId']}", flush=True)
    while pending or running or waiting_variants:
        # A variant becomes submittable once its base model has succeeded.
        ok_ids = {j["name"]: j["jobId"] for j in done if j.get("status") in ("success", "completed")}
        failed = {j["name"] for j in done if j.get("status") not in ("success", "completed")}
        for v in list(waiting_variants):
            if v["base"] in ok_ids:
                v["body"]["jobId"] = ok_ids[v["base"]]
                pending.append(v)
                waiting_variants.remove(v)
            elif v["base"] in failed:
                print(f"skip {v['name']}: base {v['base']} failed")
                waiting_variants.remove(v)
        if not pending and not running:
            break
        while pending and len(running) < MAX_CONCURRENT:
            j = pending.pop(0)
            j["jobId"] = create(j["kind"], j["body"])
            state[j["name"]] = j["jobId"]
            save_state()
            running[j["jobId"]] = j
            print(f"submitted {j['name']} -> {j['jobId']}", flush=True)
        time.sleep(10)
        for job_id in list(running):
            status = get_job(job_id)
            if not status["done"]:
                continue
            j = running.pop(job_id)
            j["status"], j["outputs"], j["error"] = status["status"], status["outputs"], status["errorMessage"]
            if j["outputs"] and j["outputs"].get("glbUrl"):
                j["glbPath"] = os.path.relpath(download(j["outputs"]["glbUrl"], os.path.join(args.out, "raw", f"{j['name']}.glb")), args.out)
            print(f"{j['status']} {j['name']}", flush=True)
            done.append(j)
    by_name = {j["name"]: j for j in done}
    manifest = {"game": plan.get("game"), "style": plan.get("style"), "assets": [], "skybox": None}
    for a in plan.get("assets", []):
        j = by_name.get(a["name"], {})
        manifest["assets"].append({**a, "jobId": j.get("jobId"), "status": j.get("status"),
                                   "glbUrl": (j.get("outputs") or {}).get("glbUrl"), "glbPath": j.get("glbPath")})
    base_specs = {a["name"]: a for a in plan.get("assets", [])}
    for v in plan.get("variants", []):
        j = by_name.get(v["name"], {})
        base = base_specs.get(v["base"], {})
        manifest["assets"].append({**{k: base[k] for k in ("role", "heightStuds", "triBudget", "collision") if k in base},
                                   **v, "variantOf": v["base"], "jobId": j.get("jobId"), "status": j.get("status"),
                                   "glbUrl": (j.get("outputs") or {}).get("glbUrl"), "glbPath": j.get("glbPath")})
    if "Sky" in by_name:
        s = by_name["Sky"]
        manifest["skybox"] = {**plan["skybox"], "jobId": s.get("jobId"), "status": s.get("status"), "outputs": s.get("outputs")}
        if s.get("outputs"):
            os.makedirs(os.path.join(args.out, "sky"), exist_ok=True)
            with open(os.path.join(args.out, "sky", "sky_job.json"), "w") as fh:
                json.dump({"jobId": s["jobId"], "status": s["status"], "outputs": s["outputs"]}, fh, indent=2)
    with open(os.path.join(args.out, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    print(f"wrote {os.path.join(args.out, 'manifest.json')}")
    return 0 if all(j.get("status") in ("success", "completed") for j in done) else 1


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup", help="Ask for your key, test it, save it to .env")
    sub.add_parser("check", help="Test the saved key and print the balance")
    tl = sub.add_parser("tool", help="Call any Sloyd MCP tool by name with JSON arguments")
    tl.add_argument("name"); tl.add_argument("arguments", nargs="?", default="{}")
    sub.add_parser("balance")
    e = sub.add_parser("estimate"); e.add_argument("plan")
    t = sub.add_parser("text-to-3d"); t.add_argument("prompt"); t.add_argument("--style", default="Auto")
    t.add_argument("--faces", type=int, default=10000); t.add_argument("--texture", default="1k")
    r = sub.add_parser("retexture"); r.add_argument("job_id"); r.add_argument("prompt"); r.add_argument("--texture", default="1k")
    s = sub.add_parser("skybox"); s.add_argument("prompt"); s.add_argument("--style", default="Auto")
    j = sub.add_parser("job"); j.add_argument("job_id"); j.add_argument("--wait", action="store_true")
    d = sub.add_parser("download"); d.add_argument("job_id"); d.add_argument("dest")
    rn = sub.add_parser("run"); rn.add_argument("plan"); rn.add_argument("--out", default="roblox-assets")
    args = p.parse_args()

    if args.cmd == "setup":
        sys.exit(cmd_setup())
    elif args.cmd == "check":
        sys.exit(cmd_check())
    elif args.cmd == "tool":
        print(json.dumps(mcp_tool(args.name, json.loads(args.arguments)), indent=2))
    elif args.cmd == "balance":
        print(json.dumps({"balance": balance()}))
    elif args.cmd == "estimate":
        sys.exit(cmd_estimate(args))
    elif args.cmd == "text-to-3d":
        print(json.dumps({"jobId": create("text-to-3d", {"prompt": args.prompt, "genStyleId": args.style, "topology": "triangles",
                                                          "targetFaceCount": args.faces, "textureResolution": args.texture})}))
    elif args.cmd == "retexture":
        print(json.dumps({"jobId": create("retexture", {"jobId": args.job_id, "prompt": args.prompt, "textureResolution": args.texture})}))
    elif args.cmd == "skybox":
        print(json.dumps({"jobId": create("text-to-worldbox", {"prompt": args.prompt, "genStyleId": args.style})}))
    elif args.cmd == "job":
        print(json.dumps(wait_job(args.job_id) if args.wait else get_job(args.job_id), indent=2))
    elif args.cmd == "download":
        job = wait_job(args.job_id)
        url = (job["outputs"] or {}).get("glbUrl") or (job["outputs"] or {}).get("imageUrl")
        if not url:
            sys.exit(f"No downloadable output: {json.dumps(job)}")
        print(download(url, args.dest))
    elif args.cmd == "run":
        sys.exit(cmd_run(args))


if __name__ == "__main__":
    main()
