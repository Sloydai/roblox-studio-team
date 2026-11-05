--!strict
-- Entry point. Order matters: data first, then remotes, then the world and shop.

local ReplicatedStorage = game:GetService("ReplicatedStorage")

local DataService = require(script.Parent.DataService)
local WorldService = require(script.Parent.WorldService)
local ShopService = require(script.Parent.ShopService)

local remotes = Instance.new("Folder")
remotes.Name = "Remotes"
local notify = Instance.new("RemoteEvent")
notify.Name = "Notify"
notify.Parent = remotes
local dataChanged = Instance.new("RemoteEvent")
dataChanged.Name = "DataChanged"
dataChanged.Parent = remotes
local getData = Instance.new("RemoteFunction")
getData.Name = "GetData"
getData.Parent = remotes
getData.OnServerInvoke = function(player: Player)
	local data = DataService.get(player)
	return if data then { coins = data.coins, owned = data.owned, equipped = data.equipped } else nil
end
remotes.Parent = ReplicatedStorage

DataService.init()
DataService.Changed:Connect(function(player: Player, data: DataService.Data)
	dataChanged:FireClient(player, { coins = data.coins, owned = data.owned, equipped = data.equipped })
end)

ShopService.init(remotes)
WorldService.init()
