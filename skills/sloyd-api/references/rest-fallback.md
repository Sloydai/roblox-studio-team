# REST fallback (curl)

For agents or scripts with no MCP client. The base URL is `https://api.sloyd.ai/api`. Every request sends both headers. Each MCP tool maps to one endpoint and takes the same fields at the same price.

```bash
H=(-H "x-client-id: $SLOYD_CLIENT_ID" -H "x-client-secret: $SLOYD_CLIENT_SECRET")
```

| MCP tool | REST endpoint | Body |
|---|---|---|
| `generate_3d_from_text` | `POST /jobs/text-to-3d` | JSON |
| `generate_3d_from_image` | `POST /jobs/image-to-3d` | multipart (`file` or `imageJobId`) |
| `generate_3d_from_images` | `POST /jobs/multi-image-to-3d` | multipart (`frontImage`, `leftImage`, `backImage`, `rightImage`) |
| `upload_image` | `POST /jobs/image-upload` | multipart (`file`) |
| `generate_image` | `POST /jobs/text-to-image` | JSON |
| `edit_image` | `POST /jobs/image-edit` | JSON |
| `generate_skybox` | `POST /jobs/text-to-worldbox` | JSON |
| `generate_skybox_from_image` | `POST /jobs/skybox-from-image` | JSON |
| `edit_skybox` | `POST /jobs/skybox-edit` | JSON |
| `retexture_model` | `POST /jobs/retexture` | JSON |
| `split_model_into_parts` | `POST /jobs/split-to-parts` | JSON |
| (no MCP tool) | `POST /jobs/upload-3d` | multipart (`file`: GLB, OBJ, FBX, STL, BLEND, PLY, USDC or USDA, up to 500 MB). Free. Returns a `jobId` you own, ready for retexture or split |
| `get_job` | `GET /jobs/{jobId}` | |
| `get_credit_balance` | `GET /user/api-access/balance` | |

## Examples

```bash
# Balance
curl -s https://api.sloyd.ai/api/user/api-access/balance "${H[@]}"

# A Roblox prop: triangles, budget under the 20k limit, 1k texture
curl -s https://api.sloyd.ai/api/jobs/text-to-3d "${H[@]}" -H "Content-Type: application/json" \
  -d '{"prompt":"a wide round gumdrop platform with a flat top","genStyleId":"CozyMobile","topology":"triangles","targetFaceCount":3000,"textureResolution":"1k"}'

# A shop skin from a model job you own
curl -s https://api.sloyd.ai/api/jobs/retexture "${H[@]}" -H "Content-Type: application/json" \
  -d '{"jobId":"JOB_ID","prompt":"mint green and white peppermint swirl, glossy hard candy","textureResolution":"1k"}'

# A skybox
curl -s https://api.sloyd.ai/api/jobs/text-to-worldbox "${H[@]}" -H "Content-Type: application/json" \
  -d '{"prompt":"pastel candy land sky at golden hour","genStyleId":"CozyMobile"}'

# Bring your own model (then retexture or split it)
curl -s https://api.sloyd.ai/api/jobs/upload-3d "${H[@]}" -F "file=@my_prop.fbx"

# Poll (REST has no wait parameter: poll every 5 to 10 seconds)
curl -s https://api.sloyd.ai/api/jobs/JOB_ID "${H[@]}"

# Download a finished model (public URL, no auth)
curl -o prop.glb https://storage.googleapis.com/ai-services-quality/jobs/JOB_ID.glb
```

REST `GET /jobs/{jobId}` reports `status` (`pending`, `running`, `success` or `error`). For a skybox, the response's `flatBoxData.layers` (where `usage` is `color`) hold the six cube faces in the order +X, −X, +Y, −Y, +Z, −Z, and `flatBoxData.panoramaUrl` holds the panorama. `scripts/sloyd.py job JOB_ID` maps these to the same `outputs` shape that MCP `get_job` returns.

Errors use the same status codes as MCP: 401, 402 (`{available, error, message, required}`), 403, 404, 422, 429 and 500.
