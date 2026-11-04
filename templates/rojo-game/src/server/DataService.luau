--!strict
-- Player data: coins, best stage, owned/equipped skins. One DataStore key per player.
-- If a load fails the session is marked unsaveable so a bad read never overwrites data.
-- In Studio, enable Game Settings -> Security -> "Enable Studio Access to API Services".

local DataStoreService = game:GetService("DataStoreService")
local Players = game:GetService("Players")

local Config = require(game:GetService("ReplicatedStorage").Shared.GameConfig)

export type Data = {
	coins: number,
	bestStage: number,
	owned: { [string]: boolean },
	equipped: string,
	receipts: { string }, -- recent developer-product PurchaseIds, for idempotent grants
}

type Session = { data: Data, canSave: boolean }

local DataService = {}

local store: DataStore? = nil
local sessions: { [Player]: Session } = {}
local changed = Instance.new("BindableEvent")
DataService.Changed = changed.Event -- (player, data)

local function defaultData(): Data
	local starter = Config.Shop.skins[1]
	return { coins = 0, bestStage = 0, owned = { [starter.id] = true }, equipped = starter.id, receipts = {} }
end

local function key(player: Player): string
	return "u_" .. player.UserId
end

local function withRetries<T>(fn: () -> T): (boolean, T | string)
	local lastErr: any = nil
	for attempt = 1, 3 do
		local ok, result = pcall(fn)
		if ok then
			return true, result
		end
		lastErr = result
		task.wait(attempt * 2)
	end
	return false, tostring(lastErr)
end

local function leaderstats(player: Player, data: Data)
	local folder: Folder = (player:FindFirstChild("leaderstats") :: Folder?) or Instance.new("Folder")
	folder.Name = "leaderstats"
	local coins: IntValue = (folder:FindFirstChild("Coins") :: IntValue?) or Instance.new("IntValue")
	coins.Name = "Coins"
	coins.Value = data.coins
	coins.Parent = folder
	local stage: IntValue = (folder:FindFirstChild("Stage") :: IntValue?) or Instance.new("IntValue")
	stage.Name = "Stage"
	stage.Parent = folder
	folder.Parent = player
end

local function load(player: Player)
	local data = defaultData()
	local canSave = false
	if store then
		local ok, result = withRetries(function()
			return (store :: DataStore):GetAsync(key(player))
		end)
		if ok then
			canSave = true
			if type(result) == "table" then
				local saved = result :: any
				data.coins = tonumber(saved.coins) or 0
				data.bestStage = tonumber(saved.bestStage) or 0
				data.owned = if type(saved.owned) == "table" then saved.owned else data.owned
				data.equipped = if type(saved.equipped) == "string" then saved.equipped else data.equipped
				data.receipts = if type(saved.receipts) == "table" then saved.receipts else {}
			end
		else
			warn(`[DataService] load failed for {player.Name}, progress will not save this session: {result}`)
		end
	end
	sessions[player] = { data = data, canSave = canSave }
	leaderstats(player, data)
	changed:Fire(player, data)
end

local function save(player: Player)
	local session = sessions[player]
	if not session or not session.canSave or not store then
		return
	end
	local snapshot = table.clone(session.data)
	local ok, err = withRetries(function()
		return (store :: DataStore):UpdateAsync(key(player), function()
			return snapshot
		end)
	end)
	if not ok then
		warn(`[DataService] save failed for {player.Name}: {err}`)
	end
end

function DataService.get(player: Player): Data?
	local s = sessions[player]
	return if s then s.data else nil
end

function DataService.addCoins(player: Player, amount: number)
	local data = DataService.get(player)
	if not data then
		return
	end
	data.coins = math.max(0, data.coins + amount)
	local stats = player:FindFirstChild("leaderstats")
	local coins = stats and stats:FindFirstChild("Coins") :: IntValue?
	if coins then
		coins.Value = data.coins
	end
	changed:Fire(player, data)
end

function DataService.update(player: Player, fn: (Data) -> ())
	local data = DataService.get(player)
	if data then
		fn(data)
		changed:Fire(player, data)
	end
end

function DataService.init()
	local ok, result = pcall(function()
		return DataStoreService:GetDataStore(Config.DataStoreName)
	end)
	if ok then
		store = result
	else
		warn("[DataService] DataStores unavailable, running without saving: " .. tostring(result))
	end

	Players.PlayerAdded:Connect(load)
	for _, p in Players:GetPlayers() do
		task.spawn(load, p)
	end
	Players.PlayerRemoving:Connect(function(player)
		save(player)
		sessions[player] = nil
	end)
	game:BindToClose(function()
		local remaining = 0
		for player in sessions do
			remaining += 1
			task.spawn(function()
				save(player)
				remaining -= 1
			end)
		end
		local deadline = os.clock() + 25 -- BindToClose has ~30 s before shutdown
		while remaining > 0 and os.clock() < deadline do
			task.wait(0.2)
		end
	end)
	task.spawn(function()
		while true do
			task.wait(Config.AutosaveSeconds)
			for player in sessions do
				task.spawn(save, player)
			end
		end
	end)
end

return DataService
