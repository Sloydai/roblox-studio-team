--!strict
-- Cosmetic shop: skins are retextured variants of one item (skin-variants generates them).
-- The server owns every price check; the client only sends a skin id.
-- Optional Robux coin packs via developer products, granted idempotently in ProcessReceipt.

local MarketplaceService = game:GetService("MarketplaceService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shared = ReplicatedStorage.Shared
local Config = require(Shared.GameConfig)
local AssetLibrary = require(Shared.AssetLibrary)
local DataService = require(script.Parent.DataService)

local ShopService = {}

local MAX_RECEIPTS = 50

local skinsById: { [string]: typeof(Config.Shop.skins[1]) } = {}
for _, skin in Config.Shop.skins do
	skinsById[skin.id] = skin
end

local function attachCosmetic(player: Player, skinId: string)
	local character = player.Character
	local skin = skinsById[skinId]
	if not character or not skin then
		return
	end
	local torso = (character:FindFirstChild("UpperTorso") or character:FindFirstChild("Torso")) :: BasePart?
	if not torso then
		return
	end
	local old = character:FindFirstChild("Cosmetic")
	if old then
		old:Destroy()
	end

	local item = AssetLibrary.spawn(skin.asset)
	AssetLibrary.applyRole(item, "cosmetic")
	item.Name = "Cosmetic"
	local _, size = if item:IsA("Model") then item:GetBoundingBox() else (item :: BasePart).CFrame, (item :: BasePart).Size
	-- On the back, facing the same way as the character.
	item:PivotTo(torso.CFrame * CFrame.new(0, 0, torso.Size.Z / 2 + size.Z / 2))
	for _, part in AssetLibrary.parts(item) do
		local weld = Instance.new("WeldConstraint")
		weld.Part0 = torso
		weld.Part1 = part
		weld.Parent = part
	end
	item.Parent = character
end

local function handleRequest(player: Player, action: unknown, skinId: unknown): (boolean, string)
	if type(action) ~= "string" or type(skinId) ~= "string" then
		return false, "bad request"
	end
	local skin = skinsById[skinId]
	local data = DataService.get(player)
	if not skin or not data then
		return false, "unknown skin"
	end
	if action == "buy" then
		if data.owned[skin.id] then
			return false, "already owned"
		end
		if data.coins < skin.price then
			return false, `need {skin.price - data.coins} more coins`
		end
		DataService.addCoins(player, -skin.price)
		DataService.update(player, function(d)
			d.owned[skin.id] = true
			d.equipped = skin.id
		end)
		attachCosmetic(player, skin.id)
		return true, `bought {skin.displayName}`
	elseif action == "equip" then
		if not data.owned[skin.id] then
			return false, "not owned"
		end
		DataService.update(player, function(d)
			d.equipped = skin.id
		end)
		attachCosmetic(player, skin.id)
		return true, `equipped {skin.displayName}`
	end
	return false, "unknown action"
end

local function processReceipt(receipt): Enum.ProductPurchaseDecision
	local player = Players:GetPlayerByUserId(receipt.PlayerId)
	local data = player and DataService.get(player)
	if not player or not data then
		return Enum.ProductPurchaseDecision.NotProcessedYet -- Roblox retries later
	end
	if table.find(data.receipts, receipt.PurchaseId) then
		return Enum.ProductPurchaseDecision.PurchaseGranted
	end
	for _, product in Config.Shop.coinProducts do
		if product.productId ~= 0 and product.productId == receipt.ProductId then
			DataService.addCoins(player, product.coins)
			DataService.update(player, function(d)
				table.insert(d.receipts, receipt.PurchaseId)
				while #d.receipts > MAX_RECEIPTS do
					table.remove(d.receipts, 1)
				end
			end)
			return Enum.ProductPurchaseDecision.PurchaseGranted
		end
	end
	return Enum.ProductPurchaseDecision.NotProcessedYet
end

function ShopService.init(remotes: Folder)
	local request = Instance.new("RemoteFunction")
	request.Name = "ShopRequest"
	request.Parent = remotes
	request.OnServerInvoke = handleRequest

	local openShop = Instance.new("RemoteEvent")
	openShop.Name = "OpenShop"
	openShop.Parent = remotes

	-- Shop stand with a ProximityPrompt next to the spawn.
	local stand = AssetLibrary.spawn(Config.Shop.stand)
	AssetLibrary.applyRole(stand, "shop")
	AssetLibrary.placeOnGround(stand, CFrame.new(Config.Shop.position) * CFrame.Angles(0, math.rad(90), 0))
	stand.Name = "ShopStand"
	stand.Parent = workspace
	local anchor = AssetLibrary.parts(stand)[1]
	local prompt = Instance.new("ProximityPrompt")
	prompt.ActionText = "Open shop"
	prompt.ObjectText = "Candy Shop"
	prompt.MaxActivationDistance = 12
	prompt.RequiresLineOfSight = false
	prompt.Parent = anchor
	prompt.Triggered:Connect(function(player)
		openShop:FireClient(player)
	end)

	MarketplaceService.ProcessReceipt = processReceipt

	Players.PlayerAdded:Connect(function(player)
		player.CharacterAdded:Connect(function()
			local data = DataService.get(player)
			if data then
				task.defer(attachCosmetic, player, data.equipped)
			end
		end)
	end)
end

return ShopService
