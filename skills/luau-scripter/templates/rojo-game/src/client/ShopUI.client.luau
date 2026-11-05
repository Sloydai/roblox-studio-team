--!strict
-- Shop window (built in code so it ships with the scripts), coin packs, and toasts.

local MarketplaceService = game:GetService("MarketplaceService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("GameConfig"))
local remotes = ReplicatedStorage:WaitForChild("Remotes")
local shopRequest = remotes:WaitForChild("ShopRequest") :: RemoteFunction
local openShop = remotes:WaitForChild("OpenShop") :: RemoteEvent
local notify = remotes:WaitForChild("Notify") :: RemoteEvent
local dataChanged = remotes:WaitForChild("DataChanged") :: RemoteEvent
local getData = remotes:WaitForChild("GetData") :: RemoteFunction

local player = Players.LocalPlayer

type View = { coins: number, owned: { [string]: boolean }, equipped: string }
local state: View = { coins = 0, owned = {}, equipped = "" }

local PINK = Color3.fromRGB(255, 120, 190)
local DARK = Color3.fromRGB(18, 35, 74)

local gui = Instance.new("ScreenGui")
gui.Name = "ShopUI"
gui.ResetOnSpawn = false
gui.Parent = player:WaitForChild("PlayerGui")

local function corner(parent: GuiObject, radius: number)
	local c = Instance.new("UICorner")
	c.CornerRadius = UDim.new(0, radius)
	c.Parent = parent
end

local function label(parent: Instance, text: string, size: UDim2, pos: UDim2): TextLabel
	local l = Instance.new("TextLabel")
	l.BackgroundTransparency = 1
	l.Text = text
	l.Size = size
	l.Position = pos
	l.Font = Enum.Font.FredokaOne
	l.TextScaled = true
	l.TextColor3 = Color3.new(1, 1, 1)
	l.Parent = parent
	return l
end

local toast = label(gui, "", UDim2.fromScale(0.5, 0.06), UDim2.fromScale(0.25, 0.12))
toast.Visible = false

local function showToast(text: string)
	toast.Text = text
	toast.Visible = true
	local stamp = os.clock()
	toast:SetAttribute("Stamp", stamp)
	task.delay(2.5, function()
		if toast:GetAttribute("Stamp") == stamp then
			toast.Visible = false
		end
	end)
end

local window = Instance.new("Frame")
window.Name = "Window"
window.AnchorPoint = Vector2.new(0.5, 0.5)
window.Position = UDim2.fromScale(0.5, 0.5)
window.Size = UDim2.fromScale(0.5, 0.6)
window.BackgroundColor3 = DARK
window.Visible = false
window.Parent = gui
corner(window, 18)
local ratio = Instance.new("UIAspectRatioConstraint")
ratio.AspectRatio = 1.4
ratio.Parent = window

label(window, "Candy Shop", UDim2.fromScale(0.6, 0.12), UDim2.fromScale(0.2, 0.03))
local coinsLabel = label(window, "0 coins", UDim2.fromScale(0.3, 0.07), UDim2.fromScale(0.03, 0.05))

local close = Instance.new("TextButton")
close.Text = "X"
close.Size = UDim2.fromScale(0.08, 0.11)
close.Position = UDim2.fromScale(0.9, 0.03)
close.BackgroundColor3 = PINK
close.TextColor3 = Color3.new(1, 1, 1)
close.Font = Enum.Font.FredokaOne
close.TextScaled = true
close.Parent = window
corner(close, 10)
close.Activated:Connect(function()
	window.Visible = false
end)

local list = Instance.new("Frame")
list.BackgroundTransparency = 1
list.Size = UDim2.fromScale(0.94, 0.62)
list.Position = UDim2.fromScale(0.03, 0.18)
list.Parent = window
local grid = Instance.new("UIGridLayout")
grid.CellSize = UDim2.fromScale(0.23, 0.95)
grid.CellPadding = UDim2.fromScale(0.02, 0)
grid.Parent = list

local buttons: { [string]: TextButton } = {}

local function refresh()
	coinsLabel.Text = `{state.coins} coins`
	for _, skin in Config.Shop.skins do
		local b = buttons[skin.id]
		if b then
			if state.equipped == skin.id then
				b.Text = "Equipped"
			elseif state.owned[skin.id] then
				b.Text = "Equip"
			else
				b.Text = `Buy {skin.price}`
			end
		end
	end
end

for _, skin in Config.Shop.skins do
	local card = Instance.new("Frame")
	card.BackgroundColor3 = Color3.fromRGB(11, 24, 51)
	card.Parent = list
	corner(card, 12)
	label(card, skin.displayName, UDim2.fromScale(0.9, 0.25), UDim2.fromScale(0.05, 0.08))
	local button = Instance.new("TextButton")
	button.Size = UDim2.fromScale(0.86, 0.22)
	button.Position = UDim2.fromScale(0.07, 0.7)
	button.BackgroundColor3 = PINK
	button.TextColor3 = Color3.new(1, 1, 1)
	button.Font = Enum.Font.FredokaOne
	button.TextScaled = true
	button.Parent = card
	corner(button, 10)
	buttons[skin.id] = button
	button.Activated:Connect(function()
		local action = if state.owned[skin.id] then "equip" else "buy"
		local ok, message = shopRequest:InvokeServer(action, skin.id)
		showToast(message)
		if ok then
			window.Visible = false
		end
	end)
end

local packs = Instance.new("Frame")
packs.BackgroundTransparency = 1
packs.Size = UDim2.fromScale(0.94, 0.12)
packs.Position = UDim2.fromScale(0.03, 0.84)
packs.Parent = window
local row = Instance.new("UIListLayout")
row.FillDirection = Enum.FillDirection.Horizontal
row.Padding = UDim.new(0.02, 0)
row.Parent = packs
for _, product in Config.Shop.coinProducts do
	if product.productId ~= 0 then
		local b = Instance.new("TextButton")
		b.Size = UDim2.fromScale(0.3, 1)
		b.Text = `+{product.coins} coins (R$)`
		b.BackgroundColor3 = Color3.fromRGB(3, 245, 132)
		b.TextColor3 = DARK
		b.Font = Enum.Font.FredokaOne
		b.TextScaled = true
		b.Parent = packs
		corner(b, 10)
		b.Activated:Connect(function()
			MarketplaceService:PromptProductPurchase(player, product.productId)
		end)
	end
end

openShop.OnClientEvent:Connect(function()
	refresh()
	window.Visible = true
end)
notify.OnClientEvent:Connect(showToast)
dataChanged.OnClientEvent:Connect(function(view: View)
	state = view
	refresh()
end)

local initial = getData:InvokeServer()
if initial then
	state = initial
end
refresh()
