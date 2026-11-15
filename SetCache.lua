local _, NS = ...
NS.Cache = {}
local Cache = NS.Cache
local bankOpen, pending, character
Cache.revision = 0

local function Call(fn, ...)
    if type(fn) ~= "function" then return nil end
    local ok, value = pcall(fn, ...)
    if ok then return value end
end
local function ID(link)
    return type(link) == "string" and tonumber(link:match("item:(%d+)")) or nil
end
local function DB()
    if character then return character end
    local guid = UnitGUID("player")
    if not guid then return nil end
    GearSetToolsDB = GearSetToolsDB or {}
    GearSetToolsDB.characters = GearSetToolsDB.characters or {}
    character = GearSetToolsDB.characters[guid] or {bank = {}, sets = {}}
    GearSetToolsDB.characters[guid] = character
    character.bank = character.bank or {}
    character.sets = character.sets or {}
    return character
end
local function ContainerLink(bag, slot)
    return Call(C_Container and C_Container.GetContainerItemLink or GetContainerItemLink, bag, slot)
end
local function NumSlots(bag)
    return Call(C_Container and C_Container.GetContainerNumSlots or GetContainerNumSlots, bag) or 0
end
local function LocationData(location)
    if type(location) ~= "number" or location <= 1 then return nil end
    local data = Call(EquipmentManager_GetLocationData, location)
    if data then return data end
    if EquipmentManager_UnpackLocation then
        local function Pack(...) return {n = select("#", ...), ...} end
        local values = Pack(EquipmentManager_UnpackLocation(location))
        local player, bank, bags = values[1], values[2], values[3]
        local slot, bag
        if values.n >= 6 then slot, bag = values[5], values[6]
        else slot, bag = values[4], values[5] end
        return {isPlayer = player, isBank = bank, isBags = bags, slot = slot, bag = bag}
    end
    -- Do not guess the encoding on a client without a native decoder.
end
local function LinkAt(location, db, expectedID)
    local data = LocationData(location)
    if not data then return nil end
    local slot, bag = data.slot, data.bag
    if data.isBank then
        -- Forever's BankPanel uses tab containers, whereas some location
        -- decoders still describe the main bank as legacy inventory slots.
        -- First trust an exact decoded container coordinate, if it matches.
        local function Read(container, index)
            if bankOpen then return ContainerLink(container, index) end
            local snapshot = db.bank[container]
            return snapshot and snapshot.items[index]
        end
        if bag ~= nil then
            local link = Read(bag, slot)
            if ID(link) == expectedID then return link, bankOpen and "bank" or "bank-cache" end
        end
        local bankSlot = slot
        if not data.isBags and slot and slot > (BANK_CONTAINER_INVENTORY_OFFSET or 51) then
            bankSlot = slot - (BANK_CONTAINER_INVENTORY_OFFSET or 51)
        end
        -- Resolve a main-bank coordinate across the actual scanned tabs.
        -- Different variants at this coordinate remain ambiguous, never guessed.
        local found
        for container in pairs(db.bank) do
            local link = Read(container, bankSlot)
            if ID(link) == expectedID then
                if found and found ~= link then return nil end
                found = link
            end
        end
        return found, bankOpen and "bank" or "bank-cache"
    end
    if data.isBags then
        return ContainerLink(bag, slot), "bags"
    elseif data.isPlayer then
        return GetInventoryItemLink("player", slot), "equipped"
    end
end

local function ScanContainer(db, bag)
    local count = NumSlots(bag)
    if count <= 0 then return end -- Unavailable tabs must not erase a snapshot.
    local items = {}
    local previous = db.bank[bag]
    for slot = 1, count do
        local link = ContainerLink(bag, slot)
        if not link then
            local info = Call(C_Container and C_Container.GetContainerItemInfo, bag, slot)
            -- A populated slot can briefly lack a link while its data loads.
            if info and info.itemID and previous then link = previous.items[slot] end
            if link and info and ID(link) ~= info.itemID then link = nil end
        end
        items[slot] = link
    end
    db.bank[bag] = {items = items, slots = count, updated = time()}
end

local function ScanBank(db)
    if not bankOpen then return end
    local bags = {[BANK_CONTAINER or -1] = true}
    local indices = Enum and Enum.BagIndex or {}
    for name, bag in pairs(indices) do
        if type(bag) == "number" and (name:match("^BankBag_") or name:match("^CharacterBankTab_")
            or name:match("^AccountBankTab_")) then bags[bag] = true end
    end
    if C_Bank and C_Bank.FetchPurchasedBankTabData and Enum and Enum.BankType then
        for _, bankType in pairs(Enum.BankType) do
            if type(bankType) == "number" then
                for _, tab in ipairs(Call(C_Bank.FetchPurchasedBankTabData, bankType) or {}) do
                    if tab.ID then bags[tab.ID] = true end
                end
            end
        end
    end
    -- Forever's bank panel can use different tab IDs from Retail's enum.
    local function Visit(frame, depth)
        if not frame or depth > 12 then return end
        if frame.GetBankTabID then
            local bag = Call(frame.GetBankTabID, frame)
            if type(bag) == "number" then bags[bag] = true end
        end
        if frame.GetChildren then
            for _, child in ipairs({frame:GetChildren()}) do Visit(child, depth + 1) end
        end
    end
    Visit(BankFrame, 0)
    for bag in pairs(bags) do ScanContainer(db, bag) end
    db.bankUpdated = time()
end

local function UniqueBankLink(db, itemID)
    local found, key
    local function Consider(link)
        if ID(link) ~= itemID then return true end
        local payload = link:match("|H(.-)|h") or link
        if key and payload ~= key then return false end
        key = payload
        return true
    end
    for _, snapshot in pairs(db.bank) do
        for _, link in pairs(snapshot.items) do
            if ID(link) == itemID then
                if not Consider(link) then return nil end
                found = link
            end
        end
    end
    if not found then return nil end
    -- A same-ID variant in bags or equipment makes the set reference ambiguous.
    for slot = 1, 19 do if not Consider(GetInventoryItemLink("player", slot)) then return nil end end
    for bag = 0, (NUM_BAG_SLOTS or 4) do
        for slot = 1, NumSlots(bag) do
            if not Consider(ContainerLink(bag, slot)) then return nil end
        end
    end
    return found, bankOpen and "bank" or "bank-cache"
end

function Cache.Refresh()
    local db = DB()
    if not db then return end
    ScanBank(db)
    if not C_EquipmentSet or not C_EquipmentSet.GetEquipmentSetIDs then return end
    local result = {}
    for _, setID in ipairs(C_EquipmentSet.GetEquipmentSetIDs() or {}) do
        local name, icon = C_EquipmentSet.GetEquipmentSetInfo(setID)
        local ids = C_EquipmentSet.GetItemIDs(setID)
        local locations = Call(C_EquipmentSet.GetItemLocations, setID)
        local ignored = Call(C_EquipmentSet.GetIgnoredSlots, setID) or {}
        local old = db.sets[setID]
        if name and ids and locations then
            local entry = {name = name, icon = icon, slots = {}}
            for slot = 1, 19 do
                local itemID, location = ids[slot], locations[slot]
                local value = {itemID = itemID, location = location}
                if ignored[slot] or location == 1 then
                    value.ignored = true
                elseif location == 0 or (itemID == nil and location == nil and ignored[slot] == false) then
                    value.empty = true
                elseif itemID and itemID > 1 then
                    local link, source = LinkAt(location, db, itemID)
                    if not link and location == -1 then
                        -- Forever reports banked set members as -1 even while
                        -- their full links are readable through BankPanel tabs.
                        link, source = UniqueBankLink(db, itemID)
                    end
                    if link and ID(link) == itemID then
                        value.link, value.source = link, source
                        value.updated = time()
                    elseif location ~= -1 and not bankOpen and old and old.name == name and old.slots[slot]
                        and old.slots[slot].itemID == itemID and old.slots[slot].location == location then
                        -- Last-known exact link, explicitly labelled as a snapshot.
                        local saved = old.slots[slot]
                        value.link, value.source, value.updated = saved.link, "snapshot", saved.updated
                    end
                end
                entry.slots[slot] = value
            end
            result[setID] = entry
        elseif old then
            result[setID] = old -- transient API unavailability
        end
    end
    db.sets = result -- deleted sets are removed too
    Cache.revision = Cache.revision + 1
end
function Cache.GetSets()
    local db = DB()
    return db and db.sets or {}
end
function Cache.Debug()
    local db = DB()
    if not db then return end
    local bankCount, setCount, links = 0, 0, 0
    for _, bag in pairs(db.bank) do for _ in pairs(bag.items) do bankCount = bankCount + 1 end end
    for _, set in pairs(db.sets) do
        setCount = setCount + 1
        for _, item in pairs(set.slots) do if item.link then links = links + 1 end end
    end
    print("GearSetTools: cached bank items=" .. bankCount .. ", sets=" .. setCount .. ", exact set links=" .. links)
    print("GearSetTools: location decoder=" .. tostring(type(EquipmentManager_GetLocationData) == "function"
        or type(EquipmentManager_UnpackLocation) == "function"))
    local shown = 0
    for _, set in pairs(db.sets) do
        for slot, item in pairs(set.slots) do
            if item.itemID and item.itemID > 1 and not item.link and not item.ignored and shown < 5 then
                local data = LocationData(item.location) or {}
                print("GearSetTools: unresolved " .. set.name .. " slot=" .. slot .. " item=" .. item.itemID
                    .. " location=" .. tostring(item.location) .. " bank=" .. tostring(data.isBank)
                    .. " bag=" .. tostring(data.bag) .. " decodedSlot=" .. tostring(data.slot))
                shown = shown + 1
            end
        end
    end
end
local function Schedule()
    if pending then return end
    pending = true
    C_Timer.After(0.2, function()
        pending = false
        local ok, err = pcall(Cache.Refresh)
        if not ok then print("GearSetTools cache: " .. tostring(err)) end
    end)
end
local frame = CreateFrame("Frame")
frame:SetScript("OnEvent", function(_, event, addon)
    if event == "ADDON_LOADED" and addon ~= "GearSetTools" then return end
    if event == "BANKFRAME_OPENED" then bankOpen = true end
    if event == "BANKFRAME_CLOSED" then bankOpen = false end
    Schedule()
end)
for _, event in ipairs({"ADDON_LOADED", "PLAYER_LOGIN", "PLAYER_ENTERING_WORLD", "BANKFRAME_OPENED",
    "BANKFRAME_CLOSED", "BAG_UPDATE_DELAYED", "PLAYERBANKSLOTS_CHANGED", "EQUIPMENT_SETS_CHANGED",
    "PLAYER_EQUIPMENT_CHANGED", "GET_ITEM_INFO_RECEIVED"}) do
    pcall(frame.RegisterEvent, frame, event)
end
-- Hook instances when the bank is first opened, including load-on-demand UI.
local hooked
frame:HookScript("OnEvent", function(_, event)
    if event ~= "BANKFRAME_OPENED" then return end
    local panel = BankPanel or (BankFrame and BankFrame.BankPanel)
    if not panel or panel == hooked then return end
    hooked = panel
    for _, method in ipairs({"RefreshAllItemsForSelectedTab", "GenerateItemSlotsForSelectedTab"}) do
        if type(panel[method]) == "function" then hooksecurefunc(panel, method, Schedule) end
    end
end)
