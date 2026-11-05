--!strict
-- Builds the level from GameConfig: obby platforms, collectibles, checkpoints, finish,
-- kill floor, decor and sky. Deterministic (seeded), so every server gets the same course.

local CollectionService = game:GetService("CollectionService")
local Lighting = game:GetService("Lighting")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage.Shared
local Config = require(Shared.GameConfig)
local AssetLibrary = require(Shared.AssetLibrary)
local DataService = require(script.Parent.DataService)

local WorldService = {}

local world: Folder

local function playerFromHit(hit: BasePart): (Player?, Humanoid?)
	local character = hit:FindFirstAncestorOfClass("Model")
	if not character then
		return nil, nil
	end
	local humanoid = character:FindFirstChildOfClass("Humanoid")
	if not humanoid or humanoid.Health <= 0 then
		return nil, nil
	end
	return Players:GetPlayerFromCharacter(character), humanoid
end

local function spawnAsset(name: string, ground: CFrame, parent: Instance): PVInstance
	local inst = AssetLibrary.spawn(name)
	local spec = Config.Assets[name]
	AssetLibrary.applyRole(inst, if spec then spec.role else "decor")
	AssetLibrary.placeOnGround(inst, ground)
	inst.Parent = parent
	return inst
end

local function onTouched(inst: Instance, handler: (Player, BasePart) -> ())
	for _, part in AssetLibrary.parts(inst) do
		if part.CanTouch then
			part.Touched:Connect(function(hit)
				local player = playerFromHit(hit)
				if player then
					handler(player, part)
				end
			end)
		end
	end
end

local function spawnCollectible(position: Vector3)
	local inst = spawnAsset(Config.Collectibles.asset, CFrame.new(position), world)
	CollectionService:AddTag(inst, "Collectible")
	local taken = false
	onTouched(inst, function(player)
		if taken then
			return
		end
		taken = true
		DataService.addCoins(player, Config.Collectibles.value)
		inst:Destroy()
		task.delay(Config.Collectibles.respawnSeconds, spawnCollectible, position)
	end)
end

local function makeCheckpoint(stage: number, ground: CFrame)
	local marker = spawnAsset(Config.Course.checkpoint, ground * CFrame.new(0, 0, -2.5), world)
	marker.Name = `Checkpoint{stage}`
	CollectionService:AddTag(marker, "Checkpoint")

	local spawn = Instance.new("SpawnLocation")
	spawn.Name = `Spawn{stage}`
	spawn.Anchored = true
	spawn.Size = Vector3.new(6, 1, 6)
	spawn.CFrame = ground * CFrame.new(0, 0.5, 2)
	spawn.Transparency = 1
	spawn.CanCollide = false
	spawn.Neutral = true
	spawn.Duration = 0
	spawn.Enabled = false -- only used via Player.RespawnLocation
	spawn.Parent = world

	onTouched(marker, function(player)
		local stats = player:FindFirstChild("leaderstats")
		local value = stats and stats:FindFirstChild("Stage") :: IntValue?
		if value and value.Value < stage then
			value.Value = stage
			player.RespawnLocation = spawn
			DataService.update(player, function(data)
				data.bestStage = math.max(data.bestStage, stage)
			end)
		end
	end)
end

local function buildCourse(): CFrame
	local course = Config.Course
	local rng = Random.new(course.seed)
	local platformTop = 1 -- the Start spawn pad's top surface
	local position = Vector3.new(0, 0, 0)
	local finishGround = CFrame.new()

	for stage = 1, course.stages do
		local dz = rng:NextNumber(-course.sideways, course.sideways)
		local dy = rng:NextNumber(0.5, course.rise)
		position = Vector3.new(position.X + course.gap, platformTop + dy - Config.Assets[course.platform].size.Y, position.Z + dz)
		position = Vector3.new(position.X, math.max(position.Y, -4), math.clamp(position.Z, -20, 20))

		local platform = spawnAsset(course.platform, CFrame.new(position), world)
		platform.Name = `Platform{stage}`
		platformTop = AssetLibrary.topY(platform)
		local top = CFrame.new(position.X, platformTop, position.Z)

		if stage % course.checkpointEvery == 0 then
			makeCheckpoint(stage, top)
		else
			spawnCollectible(top.Position + Vector3.new(0, Config.Collectibles.hover, 0))
		end
		finishGround = top
	end
	return finishGround
end

local function buildFinish(lastTop: CFrame)
	local ground = lastTop + Vector3.new(Config.Course.gap + 4, 0, 0)
	local pad = Instance.new("Part")
	pad.Name = "FinishPad"
	pad.Anchored = true
	pad.Size = Vector3.new(24, 2, 24)
	pad.CFrame = ground - Vector3.new(0, 1, 0)
	pad.Color = Color3.fromRGB(255, 200, 230)
	pad.Material = Enum.Material.SmoothPlastic
	pad.Parent = world

	local finish = spawnAsset(Config.Course.finish, ground + Vector3.new(4, 0, 0), world)
	finish.Name = "Finish"
	local rewarded: { [Player]: boolean } = {}
	onTouched(finish, function(player)
		if rewarded[player] then
			return
		end
		rewarded[player] = true
		DataService.addCoins(player, Config.Course.finishReward)
		local remote = ReplicatedStorage:FindFirstChild("Remotes") and ReplicatedStorage.Remotes:FindFirstChild("Notify")
		if remote and remote:IsA("RemoteEvent") then
			remote:FireClient(player, `You beat the course! +{Config.Course.finishReward} coins`)
		end
	end)
	Players.PlayerRemoving:Connect(function(player)
		rewarded[player] = nil
	end)
end

local function buildKillFloor()
	if not Config.KillFloor.enabled then
		return
	end
	local floor = Instance.new("Part")
	floor.Name = "KillFloor"
	floor.Anchored = true
	floor.Size = Vector3.new(2048, 2, 2048)
	floor.Position = Vector3.new(0, Config.KillFloor.height, 0)
	floor.Color = Config.KillFloor.color
	floor.Material = Enum.Material.Neon
	floor.Parent = world
	floor.Touched:Connect(function(hit)
		local _, humanoid = playerFromHit(hit)
		if humanoid then
			humanoid.Health = 0
		end
	end)
end

local function buildDecor()
	local rng = Random.new(Config.Course.seed + 1)
	local ground = Instance.new("Part")
	ground.Name = "Ground"
	ground.Anchored = true
	ground.Size = Vector3.new(80, 2, 80)
	ground.Position = Vector3.new(-10, -1, 0)
	ground.Color = Color3.fromRGB(255, 214, 236)
	ground.Material = Enum.Material.SmoothPlastic
	ground.Parent = world

	for _, entry in Config.Decor do
		for i = 1, entry.count do
			local angle = rng:NextNumber(0, math.pi * 2)
			local radius = rng:NextNumber(entry.minRadius, entry.maxRadius)
			local pos = Vector3.new(math.cos(angle) * radius, Config.KillFloor.height + 1, math.sin(angle) * radius)
			if math.abs(pos.Z) < 26 and pos.X > -10 then
				continue -- keep the course lane clear
			end
			local inst = spawnAsset(entry.asset, CFrame.new(pos) * CFrame.Angles(0, rng:NextNumber(0, math.pi * 2), 0), world)
			inst.Name = `{entry.asset}{i}`
		end
	end
end

local SKY_FACES = { "SkyboxBk", "SkyboxDn", "SkyboxFt", "SkyboxLf", "SkyboxRt", "SkyboxUp" }

local function applySky()
	local ids = Config.Sky
	if not ids then
		return
	end
	local sky = Lighting:FindFirstChildOfClass("Sky") or Instance.new("Sky")
	for _, face in SKY_FACES do
		local id = ids[face]
		if id then
			(sky :: any)[face] = id
		end
	end
	sky.CelestialBodiesShown = false
	sky.StarCount = 0
	sky.Parent = Lighting
end

function WorldService.init()
	world = Instance.new("Folder")
	world.Name = "World"
	world.Parent = workspace

	applySky()
	buildKillFloor()
	buildDecor()
	buildFinish(buildCourse())

	Players.PlayerAdded:Connect(function(player)
		player.CharacterAdded:Connect(function()
			-- RespawnLocation is reset on rejoin; restore it from saved progress.
			local data = DataService.get(player)
			if data and data.bestStage > 0 and not player.RespawnLocation then
				local best = math.floor(data.bestStage / Config.Course.checkpointEvery) * Config.Course.checkpointEvery
				local spawn = world:FindFirstChild(`Spawn{best}`) :: SpawnLocation?
				if spawn then
					player.RespawnLocation = spawn
					local stats = player:FindFirstChild("leaderstats")
					local stage = stats and stats:FindFirstChild("Stage") :: IntValue?
					if stage then
						stage.Value = best
					end
					task.defer(function()
						local character = player.Character
						if character then
							character:PivotTo(spawn.CFrame + Vector3.new(0, 4, 0))
						end
					end)
				end
			end
		end)
	end)
end

return WorldService
