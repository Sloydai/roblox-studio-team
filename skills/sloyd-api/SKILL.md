---
name: sloyd-api
description: Use first, before any other Roblox Studio Team skill calls Sloyd, and whenever the user needs to connect Sloyd, set or fix SLOYD_CLIENT_ID / SLOYD_CLIENT_SECRET, check their credit balance, estimate what a Roblox asset run will cost, poll a jobId, download a GLB or skybox, or recover from a 401, 402 (insufficient credits) or 429 (5 concurrent jobs) error. Also use when the agent has no MCP support and must call Sloyd over plain HTTP or curl.
---

# Sloyd API: connection, credits and the job loop

> **Script paths:** `<skills>` below means the folder this skill is installed in, the parent of this `SKILL.md`'s folder (for example `.agents/skills` or `.claude/skills`). All Roblox Studio Team skills sit side by side there. On Windows, use `python` instead of `python3`.

Every role in the Roblox Studio Team spends real credits through this API: game-designer, prop-modeler, skin-variants and world-backdrop. This skill is the shared contract. It covers how to connect, how to price a request before running it, how to run a job to completion, and what to do when it fails.

Source of truth: the Sloyd API docs (api-dashboard.sloyd.ai) and the live tool schemas on the MCP server. Never invent a tool or a parameter that isn't listed here or returned by `tools/list`.

## 1. Credentials: every user brings their own

Each user creates their own key, and generations are billed to that user's prepaid credits.

1. Sign in at https://api-dashboard.sloyd.ai, open **API Keys**, and click **Generate Key**. Copy the Client ID and the Client Secret. The secret is shown once.
2. Buy credits under **Usage & Billing** (minimum $12 = 900 credits). A key with 0 credits authenticates, but every paid call returns 402.
3. In a terminal in the game project folder, the user runs:

   ```bash
   python3 <skills>/sloyd-api/scripts/sloyd.py setup
   ```

   It asks for the ID and the secret (hidden input), tests them, saves them to `.env` in the project and adds `.env` to `.gitignore`.

Environment variables `SLOYD_CLIENT_ID` / `SLOYD_CLIENT_SECRET` also work and win over `.env`.

Rules for the agent:

- **Check the key with `python3 <skills>/sloyd-api/scripts/sloyd.py check`**, run from the project folder. It reads the environment and `.env` and prints only `credentials: ok` and the balance. Don't check the environment variables alone: a key saved by `setup` lives in `.env`.
- If `check` fails, stop. Tell the user to run the `setup` command above **themselves, in their own terminal**, then try again. Don't generate anything without a working key.
- Never ask the user to paste a secret into chat, never read `.env` aloud, never write the key into a tracked file, a manifest, a log or a commit, and never echo it back.

## 2. Connect

**No setup needed: the bundled client.** `<skills>/sloyd-api/scripts/sloyd.py` uses only the Python standard library and reads the same key. `tool` calls any tool in the table below over plain HTTPS, with the same arguments and prices as the MCP server:

```bash
python3 <skills>/sloyd-api/scripts/sloyd.py check
python3 <skills>/sloyd-api/scripts/sloyd.py tool generate_3d_from_text '{"prompt":"a gumdrop platform","topology":"triangles","targetFaceCount":3000,"textureResolution":"1k"}'
python3 <skills>/sloyd-api/scripts/sloyd.py tool get_job '{"jobId":"<jobId>","wait":30}'
python3 <skills>/sloyd-api/scripts/sloyd.py estimate roblox-assets/plan.json
python3 <skills>/sloyd-api/scripts/sloyd.py run roblox-assets/plan.json --out roblox-assets
```

`run` takes a game-designer `plan.json` and runs every prop, skin variant and the skybox:
- it keeps at most 5 jobs in flight
- it saves each `jobId` to `run_state.json` as soon as it gets one, so a re-run resumes instead of paying twice
- it writes `manifest.json`, and `sky/sky_job.json` for world-backdrop

**The Sloyd MCP server (optional).** When the user installed the Claude Code plugin, or added the server by hand, the same tools appear as MCP tools. Use them when they're there. The plugin reads the key from the environment variables, not from `.env`. To add the server by hand:

```bash
claude mcp add --transport http sloyd https://api.sloyd.ai/api/mcp \
  --header "x-client-id: $SLOYD_CLIENT_ID" \
  --header "x-client-secret: $SLOYD_CLIENT_SECRET"
```

Other clients (Cursor, VS Code, Claude Desktop via `mcp-remote`): see [references/clients.md](references/clients.md). The curl equivalents are in [references/rest-fallback.md](references/rest-fallback.md).

**Script paths.** Commands use `<skills>/...`, the folder the skills are installed in. All scripts are Python 3.9+ with the standard library only. Run them from the user's project folder, because outputs go to the paths you pass in.

## 3. Tools (the complete list)

| Tool | Used by | Credits |
|---|---|---|
| `get_credit_balance` | everyone, before spending | free |
| `get_generation_styles` | game-designer | free |
| `generate_3d_from_text` | prop-modeler. Args: `prompt`, `genStyleId`, `topology`, `targetFaceCount` (0 to 500000), `textureResolution`, `tPose` | 25 textured |
| `generate_3d_from_image` | prop-modeler (concept route). Args: `file` {url or base64+mimeType} or `imageJobId`, `topology`, `targetFaceCount`, `textureResolution` | 20 textured |
| `generate_3d_from_images` | prop-modeler (multi-view). Args: `frontImage` plus at least one other view, `FaceCount` (string), `EnablePBR` ("true"/"false" string) | 40 textured (estimate) |
| `upload_image` | prop-modeler, world-backdrop | free |
| `generate_image` | game-designer (concept art). Args: `prompt`, `genStyleId`, `aspectRatio`, `referenceImageJobId`, `tPose` | 10 |
| `edit_image` | game-designer. Args: `jobId`, `prompt`, `genStyleId` | 15 |
| `retexture_model` | skin-variants. Args: `jobId` (a model this key owns), `prompt`, `textureResolution` | 15 |
| `split_model_into_parts` | prop-modeler (optional). Args: `jobId`, `method`, `numberOfParts`, `attachmentPoints` | 40 |
| `generate_skybox` | world-backdrop. Args: `prompt`, `genStyleId` | 25 |
| `generate_skybox_from_image` | world-backdrop. Args: `imageJobId`, `prompt`, `genStyleId` | 25 |
| `edit_skybox` | world-backdrop. Args: `jobId`, `prompt`, `genStyleId` | 25 (estimate) |
| `get_job` | everyone. Args: `jobId`, `wait` (0 to 30) | free |

Prices come from https://www.sloyd.ai/api/pricing (1 USD = 75 credits). The 25-credit text-to-3D price was confirmed against a live 402 response. When an estimate and a 402 disagree, the 402 `required` value wins.

**Not available to public API keys:** Roblox avatar creator, selfie-to-Roblox avatar, upload to a Roblox account / the Studio plugin queue, auto-rig, animation and spritesheets. They need a signed-in Sloyd web account. Don't call them and don't imitate them; call them "coming soon" if asked.

### Settings that matter for Roblox

- `topology: "triangles"` and `targetFaceCount` set to the asset's triangle budget, so the model arrives under Roblox's 20,000-triangle limit. On the launch run, Sloyd met every budget exactly.
- `textureResolution: "1k"`. The exporter then sizes textures for each prop's stud size.
- `genStyleId`: `Roblox`, `CozyMobile`, `Cartoon` and `Polygonal` read well at Roblox scale. `Roblox` gives blocky, voxel-like shapes; use `CozyMobile` or `Cartoon` for smooth ones.

## 4. Spend safely

Before any paid call or batch:

1. Call `get_credit_balance`.
2. Price the whole plan with the table above, or run `sloyd.py estimate plan.json`. For a game, add about 15% for rerolls.
3. Tell the user the total, the balance and what's left after, in one line. For example: `This run costs 245 credits (~$3.27). Balance: 415. Remaining after: ~170.`
4. Wait for a yes, unless the user already approved a budget that covers it.

Credits are charged when a job starts and refunded automatically if the job fails.

## 5. The job loop

1. A generation tool returns `{ "jobId": "..." }` immediately.
2. Call `get_job` with `{ "jobId": "...", "wait": 30 }`. Each call waits up to 30 seconds. Repeat until `done` is `true`. Jobs take one to several minutes.
3. On `status: "success"`, read `outputs`:
   - `outputs.glbUrl` for 3D models
   - `outputs.imageUrl` for images
   - `outputs.panoramaUrl` and `outputs.cubemapFaceUrls` for skyboxes
4. On `status: "error"`, read `errorMessage`. Credits were refunded. Retry once with the same arguments. If it fails again, change the input (a simpler prompt, one object) instead of retrying blindly.
5. Write every `jobId` down the moment you get it. There's no list-jobs endpoint, so a lost id means a paid result you can't find. On resume, poll the saved id instead of starting a new job.

Output URLs are public. Download the files you want to keep into the user's project, and don't commit them to a public repo.

## 6. Errors

| Status | Meaning | What to do |
|---|---|---|
| 401 | Missing or wrong credentials | Re-check the two env vars. A revoked key fails immediately |
| 402 | Not enough credits. The body has `required` and `available` | Stop launching new jobs. Tell the user the shortfall and the dashboard link. Nothing was charged, and the same call can be retried after a top-up |
| 403 | Not your job (for example, retexturing someone else's model) | Use a jobId this key created, or upload the GLB first (REST `POST /jobs/upload-3d`, free) |
| 422 | Bad field (enum, range, missing image) | Fix the argument. Nothing was charged |
| 429 | 5 jobs are already pending or running on this key, including jobs from other tools or teammates | Wait for a running job to finish, then retry. Never fire a 6th job in parallel |
| 500 | Server error | Retry with backoff. Report the jobId if it persists |

Over MCP, these arrive as tool errors whose text contains the status code.

## 7. Concurrency

At most 5 jobs per key can be pending or running. Keep a hard cap of 5 in-flight jobs in any batch, and treat 429 as "slot not free yet", not as a failure. If the user runs other Sloyd work on the same key at the same time, lower your cap. Skin variants can only start once their base model has succeeded; `sloyd.py run` handles that ordering.
