local _, NS = ...
local Cache = NS.Cache
local Compare = {}
NS.Compare = Compare
local tips, cards = {}, {}
local source, signature, page, pageCount, busy = nil, nil, 1, 1, false
local lastError
local original, sourcePosition
local positioningSource = false
local function ReportError(err)
    positioningSource = false
    local message = tostring(err)
    if lastError ~= message then print("GearSetTools compare: " .. message) end
    lastError = message
end
local ru = GetLocale() == "ruRU"
local function L(en, russian) return ru and russian or en end
local slotsByType = {
    INVTYPE_HEAD = {1}, INVTYPE_NECK = {2}, INVTYPE_SHOULDER = {3}, INVTYPE_BODY = {4},
    INVTYPE_CHEST = {5}, INVTYPE_ROBE = {5}, INVTYPE_WAIST = {6}, INVTYPE_LEGS = {7},
    INVTYPE_FEET = {8}, INVTYPE_WRIST = {9}, INVTYPE_HAND = {10}, INVTYPE_FINGER = {11, 12},
    INVTYPE_TRINKET = {13, 14}, INVTYPE_CLOAK = {15}, INVTYPE_WEAPON = {16, 17},
    INVTYPE_2HWEAPON = {16, 17}, INVTYPE_WEAPONMAINHAND = {16}, INVTYPE_WEAPONOFFHAND = {17},
    INVTYPE_HOLDABLE = {17}, INVTYPE_SHIELD = {17}, INVTYPE_RANGED = {18},
    INVTYPE_RANGEDRIGHT = {18}, INVTYPE_THROWN = {18}, INVTYPE_RELIC = {18}, INVTYPE_TABARD = {19},
}
local slotNames = {
    [11] = L("Ring 1", "Кольцо 1"), [12] = L("Ring 2", "Кольцо 2"),
    [13] = L("Trinket 1", "Аксессуар 1"), [14] = L("Trinket 2", "Аксессуар 2"),
    [16] = L("Main hand", "Правая рука"), [17] = L("Off hand", "Левая рука"),
}
local sourceNames = {
    equipped = L("Equipped", "Надето"), bags = L("Bags", "Сумки"), bank = L("Bank", "Банк"),
    ["bank-cache"] = L("Bank: cached", "Банк: кэш"), snapshot = L("Last seen: cached", "Последние данные: кэш"),
}
local function Call(fn, ...)
    if type(fn) ~= "function" then return nil end
    local ok, value = pcall(fn, ...)
    if ok then return value end
end
local function EquipType(link)
    local fn = C_Item and C_Item.GetItemInfoInstant or GetItemInfoInstant
    if not fn then return nil end
    local ok, _, _, _, equipType = pcall(fn, link)
    if ok then return equipType end
end
local function TooltipLink(tooltip)
    if not tooltip then return nil end
    if type(tooltip.GetItem) == "function" then
        local ok, _, link = pcall(tooltip.GetItem, tooltip)
        if ok and type(link) == "string" and link:find("item:", 1, true) then return link end
    end
    local data = Call(tooltip.GetPrimaryTooltipData, tooltip) or Call(tooltip.GetTooltipData, tooltip)
    if data then
        if type(data.hyperlink) == "string" and data.hyperlink:find("item:", 1, true) then return data.hyperlink end
        if data.guid then return Call(C_Item and C_Item.GetItemLinkByGUID, data.guid) end
    end
end
Compare.TooltipLink = TooltipLink
function Compare.BuildCards(link)
    local equipType = EquipType(link)
    local slots = slotsByType[equipType]
    if not slots then return {}, equipType end
    local result, currentBySlot = {}, {}
    local function ItemKey(item)
        return item and item.link and (item.link:match("|H(.-)|h") or item.link)
    end
    local function SameItem(a, b)
        local key = ItemKey(a)
        return key and key == ItemKey(b)
    end
    local function SamePair(a, b)
        if not a and not b then return true end
        if a and b and a.empty and b.empty then return true end
        return SameItem(a, b)
    end
    local function AddSet(name, icon, items, isCurrent)
        for _, slot in ipairs(slots) do
            local item = items[slot] or {}
            if not item.empty and not item.ignored and (item.link or (item.itemID and item.itemID > 1)) then
            local paired = equipType == "INVTYPE_2HWEAPON" and slot == 16 and items[17] or nil
            local current = not isCurrent and currentBySlot[slot]
            if current and SameItem(current.item, item) and SamePair(current.paired, paired) then
                current.setNames = current.setNames or {}
                current.setNames[#current.setNames + 1] = name
                current.name = table.concat(current.setNames, ", ") .. L(" (Currently Equipped)", " (Надето)")
                current.icon = current.setIcon or icon
                current.setIcon = current.icon
            else
            local card = {
                name = name, icon = icon, slot = slot, item = item,
                paired = paired, combined = equipType == "INVTYPE_2HWEAPON" and slot == 16,
                included = equipType == "INVTYPE_2HWEAPON" and slot == 17,
            }
            result[#result + 1] = card
            if isCurrent then currentBySlot[slot] = card end
            end
            end
        end
    end
    local worn = {}
    for slot = 1, 19 do
        local item = GetInventoryItemLink("player", slot)
        worn[slot] = {link = item, source = "equipped", empty = item == nil}
    end
    AddSet(L("Currently equipped", "Текущая экипировка"), "Interface\\Icons\\INV_Chest_Chain", worn, true)
    local ids = {}
    for id in pairs(Cache.GetSets()) do ids[#ids + 1] = id end
    table.sort(ids)
    for _, id in ipairs(ids) do
        local set = Cache.GetSets()[id]
        AddSet(set.name, set.icon, set.slots)
    end
    return result, equipType
end

local function FallbackDelta(candidate, old, paired)
    local fn = C_Item and C_Item.GetItemStats or GetItemStats
    local newStats, oldStats = Call(fn, candidate), old and Call(fn, old) or {}
    local pairStats = paired and Call(fn, paired) or {}
    if not newStats or not oldStats or not pairStats then return nil end
    local keys, lines = {}, {}
    for key in pairs(newStats) do keys[key] = true end
    for key in pairs(oldStats) do keys[key] = true end
    for key in pairs(pairStats) do keys[key] = true end
    local sorted = {}
    for key in pairs(keys) do sorted[#sorted + 1] = key end
    table.sort(sorted)
    for _, key in ipairs(sorted) do
        local delta = (newStats[key] or 0) - (oldStats[key] or 0) - (pairStats[key] or 0)
        if math.abs(delta) > 0.001 then
            local number = string.format("%+.2f", delta):gsub("%.00$", ""):gsub("(%..-)0$", "%1")
            lines[#lines + 1] = (delta > 0 and "|cff40ff80" or "|cffff6060")
                .. number .. " " .. (_G[key] or key) .. "|r"
        end
    end
    return lines
end
function Compare.Delta(candidate, item, paired)
    if item.ignored or (not item.link and not item.empty) then return nil end
    if paired and (paired.ignored or (not paired.link and not paired.empty)) then return nil end
    if item.link and C_TooltipComparison and C_TooltipComparison.GetItemComparisonDelta then
        local lines = Call(C_TooltipComparison.GetItemComparisonDelta,
            {hyperlink = candidate}, {hyperlink = item.link},
            paired and paired.link and {hyperlink = paired.link} or nil, false)
        if lines then return lines end
    end
    return FallbackDelta(candidate, item.link, paired and paired.link)
end

local function GetTip(index)
    if tips[index] then return tips[index] end
    local tip = CreateFrame("GameTooltip", "GearSetToolsCompare" .. index, UIParent, "GameTooltipTemplate")
    tip:SetFrameStrata("TOOLTIP")
    tip:EnableMouse(false)
    tip:SetClampedToScreen(false) -- the grid accounts for headers and screen edges
    local header = CreateFrame("Frame", nil, tip, "BackdropTemplate")
    header:SetPoint("BOTTOMLEFT", tip, "TOPLEFT", 0, -1)
    header:SetPoint("BOTTOMRIGHT", tip, "TOPRIGHT", 0, -1)
    header:SetHeight(25)
    header:SetBackdrop({bgFile = "Interface\\Buttons\\WHITE8X8", edgeFile = "Interface\\Buttons\\WHITE8X8", edgeSize = 1})
    header:SetBackdropColor(0.06, 0.045, 0.025, 0.98)
    header:SetBackdropBorderColor(0.65, 0.5, 0.22, 1)
    header:EnableMouse(false)
    header.icon = header:CreateTexture(nil, "ARTWORK")
    header.icon:SetSize(19, 19)
    header.icon:SetPoint("LEFT", 4, 0)
    header.label = header:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    header.label:SetPoint("LEFT", header.icon, "RIGHT", 5, 0)
    header.label:SetJustifyH("LEFT")
    tip.gstHeader = header
    tips[index] = tip
    return tip
end
local function Hide()
    for _, tip in ipairs(tips) do tip:Hide() end
    local restore = original
    -- Disable anchor hooks before restoring Blizzard's original position.
    original, sourcePosition = nil, nil
    if restore then
        restore.tooltip:SetScale(restore.scale)
        restore.tooltip:ClearAllPoints()
        for _, point in ipairs(restore.points) do restore.tooltip:SetPoint(unpack(point)) end
    end
    signature, source = nil, nil
end
local function PositionSource()
    if positioningSource or not original or not sourcePosition then return end
    positioningSource = true
    local tooltip, pos = original.tooltip, sourcePosition
    local point, relative, relativePoint, x, y = tooltip:GetPoint(1)
    if tooltip:GetNumPoints() == 1 and point == "TOPLEFT" and relative == UIParent
        and relativePoint == "BOTTOMLEFT" and x and y
        and math.abs(x - pos.x / pos.scale) < 0.01 and math.abs(y - pos.y / pos.scale) < 0.01
        and math.abs(tooltip:GetScale() - pos.scale) < 0.001 then
        positioningSource = false
        return
    end
    tooltip:SetScale(pos.scale)
    tooltip:ClearAllPoints()
    tooltip:SetPoint("TOPLEFT", UIParent, "BOTTOMLEFT", pos.x / pos.scale, pos.y / pos.scale)
    positioningSource = false
end
local function WantsComparison()
    return IsModifiedClick("COMPAREITEMS") or Call(C_CVar and C_CVar.GetCVarBool or GetCVarBool, "alwaysCompareItems")
end
local function SuppressNative(tooltip)
    for _, tip in ipairs(tooltip.shoppingTooltips or {}) do tip:Hide() end
end
local function Fill(tip, card, candidate)
    tip:SetOwner(UIParent, "ANCHOR_NONE")
    tip:ClearLines()
    local item = card.item
    if item.link then
        tip:SetHyperlink(item.link)
    else
        tip:AddLine(item.ignored and L("Slot ignored by set", "Слот исключён из комплекта")
            or item.empty and L("Empty slot", "Пустой слот")
            or L("Exact item is not cached", "Точного предмета ещё нет в кэше"), 1, 0.8, 0.3, true)
        if not item.empty and not item.ignored then
            tip:AddLine(L("Open the bank to save this item's full link.", "Откройте банк для сохранения полной ссылки предмета."), 0.8, 0.8, 0.8, true)
        end
    end
    tip:AddLine(" ")
    if item.source then tip:AddLine(sourceNames[item.source] or item.source, 0.6, 0.7, 0.8, true) end
    if card.included then
        tip:AddLine(L("Included in main-hand replacement comparison.", "Учтён в сравнении замены оружия в правой руке."), 0.8, 0.8, 0.8, true)
    else
        tip:AddLine(card.combined and L("If replacing both hands:", "При замене обоих предметов в руках:")
            or L("If replacing this slot:", "При замене этого слота:"), 1, 0.82, 0, true)
        local lines = Compare.Delta(candidate, item, card.paired)
        if lines then
            if #lines == 0 then tip:AddLine(L("No stat changes", "Характеристики не изменятся"), 0.8, 0.8, 0.8) end
            for _, line in ipairs(lines) do tip:AddLine(line, 1, 1, 1, true) end
        else
            tip:AddLine(L("Comparison data unavailable", "Данные для сравнения недоступны"), 0.65, 0.65, 0.65, true)
        end
    end
    tip.gstHeader.icon:SetTexture(card.icon or "Interface\\Icons\\INV_Misc_QuestionMark")
    tip.gstHeader.label:SetText(card.name .. (slotNames[card.slot] and " - " .. slotNames[card.slot] or ""))
    tip:Show()
    tip.gstHeader.label:SetWidth(math.max(80, tip:GetWidth() - 36))
    tip.gstHeader:SetHeight(math.max(28, tip.gstHeader.label:GetStringHeight() + 12))
end

-- Pack actual card widths, keeping the candidate first on every page.
function Compare.Layout(sizes, availableWidth, availableHeight, gap)
    local pages, current, x, y, rowHeight = {}, nil, 0, 0, 0
    local function StartPage()
        current = {positions = {}, width = sizes[1].width, height = sizes[1].height}
        pages[#pages + 1] = current
        current.positions[1] = {index = 1, x = 0, y = 0}
        x, y, rowHeight = sizes[1].width + gap, 0, sizes[1].height
    end
    StartPage()
    for index = 2, #sizes do
        local size = sizes[index]
        if x + size.width > availableWidth then x, y, rowHeight = 0, y + rowHeight + gap, 0 end
        if y + size.height > availableHeight then StartPage() end
        current.positions[#current.positions + 1] = {index = index, x = x, y = y}
        current.width = math.max(current.width, x + size.width)
        current.height = math.max(current.height, y + size.height)
        rowHeight = math.max(rowHeight, size.height)
        x = x + size.width + gap
    end
    return pages
end

local function Render(tooltip, link)
    cards = Compare.BuildCards(link)
    if #cards == 0 then Hide(); return end
    if original and original.tooltip ~= tooltip then Hide() end
    if not original then
        local points = {}
        for index = 1, tooltip:GetNumPoints() do points[index] = {tooltip:GetPoint(index)} end
        original = {tooltip = tooltip, scale = tooltip:GetScale(), points = points,
            left = (tooltip:GetLeft() or 0) * tooltip:GetEffectiveScale() / UIParent:GetEffectiveScale(),
            top = (tooltip:GetTop() or UIParent:GetHeight()) * tooltip:GetEffectiveScale() / UIParent:GetEffectiveScale()}
    end
    local width, height = UIParent:GetWidth(), UIParent:GetHeight()
    local available = width - 16
    local headerHeight = 28
    local maxWidth, maxHeight = tooltip:GetWidth(), tooltip:GetHeight()
    -- Build full tooltips once per item/cache revision, then lay out a page.
    for index, card in ipairs(cards) do
        local tip = GetTip(index)
        tip:SetScale(1)
        Fill(tip, card, link)
        maxWidth = math.max(maxWidth, tip:GetWidth())
        maxHeight = math.max(maxHeight, tip:GetHeight())
        headerHeight = math.max(headerHeight, tip.gstHeader:GetHeight())
    end
    local scale = math.min(0.9, (available - 8) / (2 * maxWidth), (height - 24) / (maxHeight + headerHeight))
    local sizes = {{width = tooltip:GetWidth() * scale, height = (tooltip:GetHeight() + headerHeight) * scale}}
    for index = 1, #cards do
        sizes[index + 1] = {width = tips[index]:GetWidth() * scale, height = (tips[index]:GetHeight() + headerHeight) * scale}
    end
    local pages = Compare.Layout(sizes, available, height - 16, 8)
    pageCount = #pages
    page = math.min(page, pageCount)
    local layout = pages[page]
    local x = math.max(8, math.min(original.left, width - layout.width - 8))
    local top = math.max(layout.height + 8, math.min(height - 8, original.top + headerHeight * scale))
    sourcePosition = {x = x, y = top - headerHeight * scale, scale = scale}
    PositionSource()
    -- GameTooltip OnHide clears its item data. Do not hide the page's freshly
    -- filled tooltips before positioning them, or Show() has nothing to render.
    local visible = {}
    for _, position in ipairs(layout.positions) do
        if position.index > 1 then
            local tip = tips[position.index - 1]
            visible[tip] = true
            tip.gstHeader:SetHeight(headerHeight)
            tip:SetScale(scale)
            tip:ClearAllPoints()
            tip:SetPoint("TOPLEFT", UIParent, "BOTTOMLEFT", (x + position.x) / scale,
                (top - position.y - headerHeight * scale) / scale)
            tip:Show()
        end
    end
    for _, tip in ipairs(tips) do if not visible[tip] then tip:Hide() end end
    SuppressNative(tooltip)
end

local function Update(tooltip)
    if busy then return end
    if not tooltip or not tooltip:IsShown() or not WantsComparison() then Hide(); return end
    local link = TooltipLink(tooltip)
    Compare.lastLink, Compare.lastEquipType = link, link and EquipType(link)
    if not link then Hide(); return end
    local key = link .. ":" .. Cache.revision .. ":" .. page
    if source == tooltip and signature == key then SuppressNative(tooltip); PositionSource(); return end
    if source ~= tooltip or (signature and signature:sub(1, #link) ~= link) then page = 1 end
    busy = true
    local success, err = pcall(Render, tooltip, link)
    busy = false
    if not success then
        Hide()
        if lastError ~= tostring(err) then print("GearSetTools compare: " .. tostring(err)) end
        lastError = tostring(err)
        return
    end
    lastError = nil
    if #cards > 0 then source, signature = tooltip, link .. ":" .. Cache.revision .. ":" .. page end
end
function Compare.NextPage()
    if pageCount > 1 then page = page % pageCount + 1; signature = nil; Update(source) end
end
function Compare.Debug()
    print("GearSetTools: compare module=" .. tostring(Compare.ready == true)
        .. ", active=" .. tostring(source ~= nil) .. ", cards=" .. #cards)
    print("GearSetTools: comparison modifier=" .. tostring(IsModifiedClick("COMPAREITEMS"))
        .. ", always compare=" .. tostring(Call(C_CVar and C_CVar.GetCVarBool or GetCVarBool, "alwaysCompareItems")))
    if lastError then print("GearSetTools: comparison last error: " .. lastError) end
    print("GearSetTools: last candidate=" .. tostring(Compare.lastLink)
        .. ", equip type=" .. tostring(Compare.lastEquipType))
    for _, name in ipairs({"GameTooltip", "GameTooltipTooltip", "ItemRefTooltip"}) do
        local tooltip = _G[name]
        if tooltip then
            local link = TooltipLink(tooltip)
            print("GearSetTools: " .. name .. " shown=" .. tostring(tooltip:IsShown())
                .. ", item=" .. tostring(link) .. ", type=" .. tostring(link and EquipType(link)))
        end
    end
    for index, tip in ipairs(tips) do
        if index <= #cards then
            print("GearSetTools: comparison " .. index .. " shown=" .. tostring(tip:IsShown())
                .. ", item=" .. tostring(TooltipLink(tip)))
        end
    end
end
function Compare.DebugHover()
    print("GearSetTools: hover the item within 3 seconds.")
    C_Timer.After(3, function() xpcall(Compare.Debug, ReportError) end)
end
local watcher = CreateFrame("Frame")
local elapsed, altWasDown = 0, false
local function OnUpdate(_, delta)
    -- Reapply before this frame is drawn, including engine-driven anchoring
    -- that does not call the public SetPoint method. Data refresh stays throttled.
    if original and original.tooltip:IsShown() and WantsComparison() then PositionSource() end
    elapsed = elapsed + delta
    if elapsed < 0.1 then return end
    elapsed = 0
    local alt = IsAltKeyDown()
    if alt and not altWasDown and source then Compare.NextPage() end
    altWasDown = alt
    local tooltip
    for _, name in ipairs({"GameTooltip", "GameTooltipTooltip", "ItemRefTooltip"}) do
        local candidate = _G[name]
        if candidate and candidate:IsShown() and TooltipLink(candidate) then tooltip = candidate; break end
    end
    Update(tooltip)
end
watcher:SetScript("OnUpdate", function(self, delta)
    xpcall(function() OnUpdate(self, delta) end, ReportError)
end)
for _, name in ipairs({"GameTooltip", "GameTooltipTooltip", "ItemRefTooltip"}) do
    local tooltip = _G[name]
    if tooltip then
    -- Blizzard reanchors a live item tooltip repeatedly. Correct that in the
    -- same call, rather than visibly moving it back on the next 0.1s timer tick.
    for _, method in ipairs({"SetPoint", "SetAnchorType"}) do
        if type(tooltip[method]) == "function" then
            hooksecurefunc(tooltip, method, function()
                if original and original.tooltip == tooltip then xpcall(PositionSource, ReportError) end
            end)
        end
    end
    end
end
if GameTooltip_ShowCompareItem then
    hooksecurefunc("GameTooltip_ShowCompareItem", function(tooltip)
        if tooltip == GameTooltip or tooltip == GameTooltipTooltip or tooltip == ItemRefTooltip then
            xpcall(function() Update(tooltip) end, ReportError)
        end
    end)
end
Compare.ready = true
