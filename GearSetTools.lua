local addonName = ...
local _, NS = ...
local GST = CreateFrame("Frame")
local palette = {
    {1.00, 0.35, 0.25}, {0.25, 0.85, 0.40}, {0.30, 0.65, 1.00},
    {0.95, 0.75, 0.20}, {0.80, 0.40, 0.95}, {0.20, 0.85, 0.85},
}
local setItems = {}
local setIcons = {}
local overlays = setmetatable({}, {__mode = "k"})
local pending = false
local startupWarnings = {}
local lastError

local function ReportError(err)
    lastError = tostring(err)
    print("|cffff6666GearSetTools: " .. lastError .. "|r")
    return lastError
end

local function ContainerItemID(bag, slot)
    if C_Container and C_Container.GetContainerItemID then
        return C_Container.GetContainerItemID(bag, slot)
    elseif GetContainerItemID then
        return GetContainerItemID(bag, slot)
    elseif GetContainerItemLink then
        local link = GetContainerItemLink(bag, slot)
        return link and tonumber(link:match("item:(%d+)"))
    end
end

local function GetItemID(link)
    if type(link) == "number" then return link end
    if type(link) == "string" then return tonumber(link:match("item:(%d+)")) end
end

local function RefreshSets()
    wipe(setItems)
    wipe(setIcons)
    if not C_EquipmentSet or not C_EquipmentSet.GetEquipmentSetIDs then return end
    local ids = C_EquipmentSet.GetEquipmentSetIDs() or {}
    table.sort(ids)
    for i, setID in ipairs(ids) do
        local color = palette[((i - 1) % #palette) + 1]
        local icon
        if C_EquipmentSet.GetEquipmentSetInfo then
            local name
            name, icon = C_EquipmentSet.GetEquipmentSetInfo(setID)
        end
        local items = C_EquipmentSet.GetItemIDs and C_EquipmentSet.GetItemIDs(setID)
        if items then
            for _, item in pairs(items) do
                local itemID = GetItemID(item)
                if itemID and itemID > 0 and not setItems[itemID] then
                    setItems[itemID] = color
                    setIcons[itemID] = icon or "Interface\\Icons\\INV_Misc_QuestionMark"
                end
            end
        end
    end
end

local function GetOverlay(button)
    local overlay = overlays[button]
    if overlay then return overlay end
    overlay = CreateFrame("Frame", nil, button, "BackdropTemplate")
    overlay:SetSize(18, 18)
    overlay:SetPoint("TOPLEFT", button, "TOPLEFT", -2, 2)
    overlay:SetFrameLevel(button:GetFrameLevel() + 5)
    overlay:SetBackdrop({
        bgFile = "Interface\\Buttons\\WHITE8X8",
        edgeFile = "Interface\\Buttons\\WHITE8X8", edgeSize = 1,
    })
    overlay:SetBackdropColor(0.035, 0.025, 0.015, 0.96)
    overlay:SetBackdropBorderColor(0.75, 0.58, 0.25, 1)
    local icon = overlay:CreateTexture(nil, "ARTWORK")
    icon:SetSize(16, 16)
    icon:SetPoint("TOP", overlay, "TOP", 0, -1)
    icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
    overlay.setIcon = icon
    overlay:EnableMouse(false)
    overlays[button] = overlay
    return overlay
end

local function Paint(button, itemID)
    if not button then return end
    local color = itemID and setItems[itemID]
    local overlay = overlays[button]
    if color then
        overlay = overlay or GetOverlay(button)
        overlay.setIcon:SetTexture(setIcons[itemID])
        overlay:Show()
    elseif overlay then
        overlay:Hide()
    end
end

local function TryMethod(object, name)
    if type(object[name]) ~= "function" then return nil end
    local ok, value = pcall(object[name], object)
    if ok then return value end
end

local function ButtonItemID(button)
    -- BankPanel buttons use bankTabID/containerSlotID, not bagID/GetID.
    local bankTab = TryMethod(button, "GetBankTabID") or button.bankTabID
    local bankSlot = TryMethod(button, "GetContainerSlotID") or button.containerSlotID
    if type(bankTab) == "number" and type(bankSlot) == "number" and bankSlot > 0 then
        return ContainerItemID(bankTab, bankSlot)
    end
    local itemID = GetItemID(TryMethod(button, "GetItemID"))
        or GetItemID(button.itemID) or GetItemID(button.itemLink)
    if itemID then return itemID end
    local bag = TryMethod(button, "GetBagID") or button.bagID
    local slot = TryMethod(button, "GetSlotID") or button.slotID
    if bag ~= nil then
        slot = slot or TryMethod(button, "GetID")
        if type(bag) == "number" and type(slot) == "number" and slot > 0 then
            return ContainerItemID(bag, slot)
        end
    end
end

local function ScanBankTree(frame, depth)
    if not frame or depth > 12 or not frame:IsShown() then return 0, 0 end
    -- Snapshot children before Paint creates an overlay under this frame.
    local children = frame.GetChildren and {frame:GetChildren()} or {}
    local count, matches = 0, 0
    if frame.IsObjectType and frame:IsObjectType("Button") then
        local itemID = ButtonItemID(frame)
        Paint(frame, itemID)
        if itemID then
            count = 1
            if setItems[itemID] then matches = 1 end
        end
    end
    for _, child in ipairs(children) do
        local found, marked = ScanBankTree(child, depth + 1)
        count, matches = count + found, matches + marked
    end
    return count, matches
end

local function InspectMouse()
    local foci = GetMouseFoci and GetMouseFoci()
    local frame = foci and foci[1] or (GetMouseFocus and GetMouseFocus())
    for level = 1, 5 do
        if not frame then break end
        print("GearSetTools: hover " .. level .. " name=" .. tostring(TryMethod(frame, "GetName"))
            .. " id=" .. tostring(TryMethod(frame, "GetID")))
        for _, key in ipairs({"GetBagID", "GetSlotID", "GetItemID", "GetBankTabID", "GetContainerSlotID"}) do
            if frame[key] then print("  " .. key .. "=" .. tostring(TryMethod(frame, key))) end
        end
        for _, key in ipairs({"bagID", "bag", "slotID", "slot", "itemID", "containerID", "bankType", "bankTabID", "containerSlotID"}) do
            if frame[key] ~= nil then print("  " .. key .. "=" .. tostring(frame[key])) end
        end
        frame = TryMethod(frame, "GetParent")
    end
end

local function ScanButtons()
    -- Blizzard container frames use a shared pool of item buttons.
    if ContainerFrameUtil_EnumerateContainerFrames then
        for first, second in ContainerFrameUtil_EnumerateContainerFrames() do
            -- Some clients return (index, frame), others return just frame.
            local frame = second or first
            if type(frame) ~= "table" and type(frame) ~= "userdata" then frame = nil end
            if frame and frame:IsShown() and frame.EnumerateValidItems then
                for itemFirst, itemSecond in frame:EnumerateValidItems() do
                    local button = itemSecond or itemFirst
                    if type(button) == "table" or type(button) == "userdata" then
                        Paint(button, ButtonItemID(button))
                    end
                end
            end
        end
    end
    -- Combined bags can use pooled anonymous item buttons rather than the
    -- legacy ContainerFrameNItemM names, and may not be in the enumerator.
    if ContainerFrameCombinedBags and ContainerFrameCombinedBags:IsShown() then
        ScanBankTree(ContainerFrameCombinedBags, 0)
    end
    -- Fallback for the standard Blizzard bag/bank item button names.
    for frameIndex = 1, (NUM_CONTAINER_FRAMES or 13) do
        local frame = _G["ContainerFrame" .. frameIndex]
        if frame and frame:IsShown() then
            for slotIndex = 1, (MAX_CONTAINER_ITEMS or 36) do
                local button = _G["ContainerFrame" .. frameIndex .. "Item" .. slotIndex]
                if button then
                    local bag = frame.GetID and frame:GetID()
                    local slot = button:GetID()
                    local itemID = bag and slot and ContainerItemID(bag, slot)
                    Paint(button, itemID)
                end
            end
        end
    end
    -- The bank's main slots are not ContainerFrame items. Their IDs are
    -- inventory slots on some clients, so use the loop's bank slot instead.
    if BankFrame and BankFrame:IsShown() then
        ScanBankTree(BankFrame, 0)
        for slot = 1, (NUM_BANKGENERIC_SLOTS or 28) do
            local itemID = ContainerItemID(BANK_CONTAINER or -1, slot)
            Paint(_G["BankFrameItem" .. slot], itemID)
            Paint(_G["BankSlotsFrameItem" .. slot], itemID)
            if BankSlotsFrame and BankSlotsFrame.ItemButtons then
                Paint(BankSlotsFrame.ItemButtons[slot], itemID)
            end
        end
        for slot = 1, (NUM_REAGENTBANKGENERIC_SLOTS or 98) do
            local button = _G["ReagentBankFrameItem" .. slot]
            if button then
                Paint(button, ContainerItemID(REAGENTBANK_CONTAINER or -3, slot))
            end
        end
    end
end

local function Refresh()
    RefreshSets()
    ScanButtons()
end

local function ScheduleRefresh()
    if pending then return end
    pending = true
    C_Timer.After(0.1, function()
        pending = false
        xpcall(Refresh, ReportError)
    end)
end

local hookedBankPanels = setmetatable({}, {__mode = "k"})
local function HookBankPanel()
    local panel = BankPanel or (BankFrame and BankFrame.BankPanel)
    if not panel or hookedBankPanels[panel] then return end
    hookedBankPanels[panel] = true
    for _, method in ipairs({"RefreshAllItemsForSelectedTab", "GenerateItemSlotsForSelectedTab"}) do
        if type(panel[method]) == "function" then
            hooksecurefunc(panel, method, ScheduleRefresh)
        end
    end
end

local function OnEvent(_, event)
    if event == "PLAYER_LOGIN" or event == "BANKFRAME_OPENED" then
        HookBankPanel()
    end
    if event == "PLAYER_LOGIN" then
        if not C_EquipmentSet then
            print("|cffff6666GearSetTools: C_EquipmentSet API unavailable.|r")
        end
        -- Repaint when any Blizzard container updates its visible buttons.
        if ContainerFrame_Update then
            hooksecurefunc("ContainerFrame_Update", ScheduleRefresh)
        end
        if ContainerFrame_UpdateItem then
            hooksecurefunc("ContainerFrame_UpdateItem", ScheduleRefresh)
        end
    end
    ScheduleRefresh()
end

SLASH_GEARSETTOOLS1 = "/gst"
SLASH_GEARSETTOOLS2 = "/gearsettools"
local function HandleCommand(msg)
    msg = (msg or ""):lower():match("^%s*(.-)%s*$")
    print("GearSetTools 0.2.3: command received.")
    if msg == "comparedebug" and NS.Compare then
        NS.Compare.DebugHover()
    elseif msg == "next" and NS.Compare then
        NS.Compare.NextPage()
    elseif msg == "cache" and NS.Cache then
        NS.Cache.Refresh()
        NS.Cache.Debug()
    elseif msg == "hover" then
        print("GearSetTools: point at the bank item within 3 seconds.")
        C_Timer.After(3, function() xpcall(InspectMouse, ReportError) end)
    elseif msg == "debug" then
        if NS.Compare then NS.Compare.Debug()
        else print("GearSetTools: comparison module did not load.") end
        if NS.Cache then NS.Cache.Debug() end
        print("GearSetTools: C_EquipmentSet=" .. tostring(C_EquipmentSet ~= nil)
            .. ", C_Container=" .. tostring(C_Container ~= nil))
        for _, warning in ipairs(startupWarnings) do
            print("GearSetTools: " .. warning)
        end
        if lastError then print("GearSetTools: last error: " .. lastError) end
        RefreshSets()
        local n = 0
        for _ in pairs(setItems) do n = n + 1 end
        print("GearSetTools: " .. n .. " distinct item IDs in equipment sets.")
        local bankButtons, bankMatches = 0, 0
        for slot = 1, (NUM_BANKGENERIC_SLOTS or 28) do
            if _G["BankFrameItem" .. slot] or _G["BankSlotsFrameItem" .. slot]
                or (BankSlotsFrame and BankSlotsFrame.ItemButtons and BankSlotsFrame.ItemButtons[slot]) then
                bankButtons = bankButtons + 1
            end
            local itemID = ContainerItemID(BANK_CONTAINER or -1, slot)
            if itemID and setItems[itemID] then bankMatches = bankMatches + 1 end
        end
        print("GearSetTools: bank buttons=" .. bankButtons .. ", set items in bank=" .. bankMatches)
        local found, marked = ScanBankTree(BankFrame, 0)
        print("GearSetTools: bank tree items=" .. found .. ", marked=" .. marked)
        Refresh()
    else
        Refresh()
        print("GearSetTools: refreshed. Use /gst debug to inspect set item count.")
    end
end

-- Register commands before subscribing to events: an event absent from this
-- client must not prevent diagnostics from loading.
SlashCmdList.GEARSETTOOLS = function(msg)
    xpcall(function() HandleCommand(msg) end, ReportError)
end

GST:SetScript("OnEvent", function(self, event)
    xpcall(function() OnEvent(self, event) end, ReportError)
end)
for _, event in ipairs({
    "PLAYER_LOGIN", "PLAYER_ENTERING_WORLD", "PLAYER_EQUIPMENT_CHANGED", "BAG_UPDATE_DELAYED", "BAG_UPDATE",
    "EQUIPMENT_SETS_CHANGED", "BANKFRAME_OPENED", "BANKFRAME_CLOSED",
    "PLAYERBANKSLOTS_CHANGED",
}) do
    local ok, err = pcall(GST.RegisterEvent, GST, event)
    if not ok then
        startupWarnings[#startupWarnings + 1] = event .. ": " .. tostring(err)
    end
end
