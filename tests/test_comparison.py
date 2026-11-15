"""Offline tests with WoW API stubs; run using Lupa (Lua 5.1)."""
import os
import sys
from pathlib import Path

if os.environ.get("GEARSETTOOLS_TEST_DEPS"):
    sys.path.insert(0, os.environ["GEARSETTOOLS_TEST_DEPS"])
from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
STUBS = r'''
NS = {}
frames, timers, messages = {}, {}, {}
local methods = {}
function methods:SetScript(name, fn) self.scripts[name] = fn end
function methods:HookScript(name, fn)
    local prev = self.scripts[name]
    self.scripts[name] = function(...) if prev then prev(...) end; fn(...) end
end
function methods:RegisterEvent(name) self.events[name] = true end
function methods:Show() self.shown = true end
function methods:Hide() self.shown = false end
function methods:IsShown() return self.shown end
function methods:IsObjectType(name) return self.kind == name end
function methods:GetChildren() return unpack(self.children) end
function methods:GetEffectiveScale() return self.scale or 1 end
function methods:GetScale() return self.scale or 1 end
function methods:GetNumPoints() return self.point and 1 or 0 end
function methods:GetPoint() if self.point then return unpack(self.point) end end
function methods:GetWidth() return self.width or 260 end
function methods:GetHeight() return self.height or (80 + #(self.lines or {}) * 15) end
function methods:SetWidth(w) self.width = w end
function methods:SetHeight(h) self.height = h end
function methods:SetSize(w,h) self.width,self.height = w,h end
function methods:SetScale(s) self.scale = s end
function methods:GetLeft() return self.left or 450 end
function methods:GetRight() return self.right or 710 end
function methods:GetTop() return 700 end
function methods:GetName() return self.name end
function methods:GetID() return 0 end
function methods:GetFrameLevel() return 5 end
function methods:SetPoint(...) self.point = {...} end
function methods:ClearAllPoints() self.point = nil end
function methods:ClearLines() self.lines = {}; self.link = nil end
function methods:AddLine(text) self.lines[#self.lines+1] = text end
function methods:SetHyperlink(link) self.link = link; self.lines = {link} end
function methods:GetItem() return 'item', self.link end
function methods:SetText(text) self.text = text end
function methods:SetTexture(texture) self.texture = texture end
function methods:CreateTexture() return setmetatable({}, {__index = methods}) end
function methods:CreateFontString() return setmetatable({}, {__index = methods}) end
for _, name in ipairs({'SetFrameStrata','EnableMouse','SetClampedToScreen','SetBackdrop','SetBackdropColor',
    'SetBackdropBorderColor','SetAllPoints','SetJustifyH','SetOwner','SetFrameLevel','SetTexCoord'}) do
    methods[name] = function() end
end
function CreateFrame(kind, name, parent)
    local f = setmetatable({kind=kind,name=name,scripts={},events={},children={},lines={}}, {__index=methods})
    frames[#frames+1] = f
    if parent then parent.children[#parent.children+1] = f end
    if name then _G[name] = f end
    return f
end
UIParent = CreateFrame('Frame'); UIParent:SetSize(1600,900); UIParent:Show()
GameTooltip = CreateFrame('GameTooltip'); GameTooltip.shoppingTooltips = {CreateFrame('GameTooltip'),CreateFrame('GameTooltip')}
ItemRefTooltip = CreateFrame('GameTooltip')
function hooksecurefunc() end
function GetLocale() return 'enUS' end
function UnitGUID() return playerGUID or 'Player-A' end
function time() return 123456 end
function print(...) messages[#messages+1] = table.concat({...}, ' ') end
function wipe(t) for k in pairs(t) do t[k] = nil end end
function IsModifiedClick() return compareHeld end
function IsAltKeyDown() return altHeld end
C_CVar = {GetCVarBool=function() return false end}
C_Timer = {After=function(_,fn) timers[#timers+1]=fn end}
function Flush()
    local pending = timers; timers={}
    for _, fn in ipairs(pending) do fn() end
end
function Event(event,...)
    for _, f in ipairs(frames) do
        if f.events[event] and f.scripts.OnEvent then f.scripts.OnEvent(f,event,...) end
    end
    Flush()
end
function Tick() for _,f in ipairs(frames) do if f.scripts.OnUpdate then f.scripts.OnUpdate(f,0.2) end end end
inventory, containers, sets, locations = {}, {}, {}, {}
Enum = {BagIndex={CharacterBankTab_1=6}, BankType={Character=0}}
C_Bank = {FetchPurchasedBankTabData=function() return {{ID=6}} end}
C_Container = {
    GetContainerNumSlots=function(bag) return bankAccessible and containers[bag] and 48 or 0 end,
    GetContainerItemLink=function(bag,slot) return bankAccessible and containers[bag] and containers[bag][slot] end,
    GetContainerItemInfo=function(bag,slot)
        local link = bankAccessible and containers[bag] and containers[bag][slot]
        if link then return {itemID=tonumber(link:match('item:(%d+)'))} end
    end,
}
function GetInventoryItemLink(_,slot) return inventory[slot] end
function EquipmentManager_GetLocationData(location) return locations[location] end
C_EquipmentSet = {
    GetEquipmentSetIDs=function() local ids={} for id in pairs(sets) do ids[#ids+1]=id end return ids end,
    GetEquipmentSetInfo=function(id) return sets[id].name, sets[id].icon end,
    GetItemIDs=function(id) return sets[id].items end,
    GetItemLocations=function(id) return sets[id].locations end,
    GetIgnoredSlots=function(id) return sets[id].ignored or {} end,
}
stats, equipTypes = {}, {}
C_Item = {
    GetItemInfoInstant=function(link) return 100, 'Armor', 'Leather', equipTypes[link] or 'INVTYPE_WAIST' end,
    GetItemStats=function(link) return stats[link] end,
}
function LoadModule(code) assert(loadstring(code))('GearSetTools',NS) end
'''


def new_runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(STUBS)
    lua.globals().LoadModule((ROOT / "SetCache.lua").read_text(encoding="utf-8"))
    lua.globals().LoadModule((ROOT / "SetCompare.lua").read_text(encoding="utf-8"))
    return lua


lua = new_runtime()
lua.execute(r'''
sets[1] = {name='Restoration',icon=123,items={[6]=100},locations={[6]=500}}
locations[500] = {isBank=true, bag=6, slot=8}
containers[6] = {[8]='item:100:enchant:healing',[9]='item:100:enchant:agility'}
NS.Cache.Refresh()
assert(not NS.Cache.GetSets()[1].slots[6].link, 'must not invent a base-item link')
bankAccessible = true; Event('BANKFRAME_OPENED')
assert(NS.Cache.GetSets()[1].slots[6].link == containers[6][8], 'exact bank variant')
assert(NS.Cache.GetSets()[1].slots[6].source == 'bank')
locations[500] = {isBank=true,slot=8}
NS.Cache.Refresh()
assert(NS.Cache.GetSets()[1].slots[6].link == containers[6][8], 'main bank uses normalized slot and actual tab')
locations[500] = {isBank=true,slot=59}
NS.Cache.Refresh()
assert(NS.Cache.GetSets()[1].slots[6].link == containers[6][8], 'legacy main-bank inventory slot')
locations[500] = {isBank=true,bag=6,slot=8}
local db = GearSetToolsDB
assert(db.characters['Player-A'].bank[6].items[9] == containers[6][9], 'cache entire bank, not just sets')
Event('BANKFRAME_CLOSED'); bankAccessible = false; NS.Cache.Refresh()
assert(NS.Cache.GetSets()[1].slots[6].link == 'item:100:enchant:healing', 'closed-bank lookup')
assert(NS.Cache.GetSets()[1].slots[6].source == 'bank-cache')
-- Separate addon initialization, same SavedVariables: simulate /reload.
savedDB = db
''')
reloaded = new_runtime()
# A round trip through Lua source avoids sharing live objects across runtimes.
reloaded.execute(r'''
GearSetToolsDB = {characters={['Player-A']={bank={[6]={items={[8]='item:100:enchant:healing'},slots=48}},sets={}}}}
sets[1]={name='Restoration',icon=123,items={[6]=100},locations={[6]=500}}
locations[500]={isBank=true,bag=6,slot=8}
NS.Cache.Refresh()
assert(NS.Cache.GetSets()[1].slots[6].link == 'item:100:enchant:healing', 'persistent bank snapshot')
sets[1].items[6] = 200
NS.Cache.Refresh()
assert(not NS.Cache.GetSets()[1].slots[6].link, 'changed set must not inherit old item')
sets[1].ignored = {[6]=true}; NS.Cache.Refresh()
assert(NS.Cache.GetSets()[1].slots[6].ignored)
sets={}; NS.Cache.Refresh(); assert(next(NS.Cache.GetSets())==nil, 'remove deleted sets')
''')
print("PASS: exact bank variants, full bank snapshot, reload, changed/ignored/deleted sets")

bank_regression = new_runtime()
bank_regression.execute(r'''
GearSetToolsDB={characters={['Player-A']={sets={},bank={[6]={items={
    [6]='item:6901:healing', [8]='item:15136:physician'},slots=48}}}}}
sets[0]={name='Restoration',icon=236157,items={[15]=6901,[6]=15136},locations={[15]=-1,[6]=-1}}
NS.Cache.Refresh()
assert(NS.Cache.GetSets()[0].slots[15].link=='item:6901:healing', 'Forever -1 bank member resolves persisted full link')
assert(NS.Cache.GetSets()[0].slots[6].link=='item:15136:physician')
GearSetToolsDB.characters['Player-A'].bank[6].items[9]='item:15136:agility'
NS.Cache.Refresh()
assert(not NS.Cache.GetSets()[0].slots[6].link, 'ambiguous bank variants must not resolve')
inventory[15]='item:6901:different-enchant'
NS.Cache.Refresh()
assert(not NS.Cache.GetSets()[0].slots[15].link, 'different equipped variant also blocks guessing')
''')
print("PASS: Forever bank location -1, cached full links, ambiguous bank/equipped variants")

merge_regression = new_runtime()
merge_regression.execute(r'''
inventory[6]='|cff0070dd|Hitem:300:123|h[Worn item]|h|r'
sets[1]={name='Feral',icon=77,items={[6]=300},locations={[6]=1048582}}
locations[1048582]={isPlayer=true,slot=6}
NS.Cache.Refresh()
local cards=NS.Compare.BuildCards('item:200')
assert(#cards==1 and cards[1].name=='Feral (Currently Equipped)' and cards[1].icon==77)
assert(cards[1].item.link==inventory[6])
-- Display color/name do not affect identity, while enchantments do.
NS.Cache.GetSets()[1].slots[6].link='|cff00ff00|Hitem:300:123|h[Other display name]|h|r'
assert(#NS.Compare.BuildCards('item:200')==1)
NS.Cache.GetSets()[1].slots[6].link='item:300:456'
assert(#NS.Compare.BuildCards('item:200')==2,'same item ID with another enchant stays separate')
equipTypes['item:200']='INVTYPE_2HWEAPON'
inventory[16]='item:301'; inventory[17]='item:302'
sets[1].items={[16]=301,[17]=303};sets[1].locations={[16]=1048592,[17]=500}
locations[1048592]={isPlayer=true,slot=16};locations[500]={isBank=true,bag=6,slot=1}
GearSetToolsDB.characters['Player-A'].bank[6]={items={[1]='item:303'},slots=48}
NS.Cache.Refresh()
cards=NS.Compare.BuildCards('item:200')
assert(#cards==4,'same main hand but different off hand must retain combined comparison')
''')
print("PASS: equipped/set merge, set icon, full item identity, different two-hand comparison pairs")

lua.execute(r'''
local candidate='item:200'
inventory[6]='item:300'
stats[candidate]={ITEM_MOD_INTELLECT_SHORT=10,ITEM_MOD_STAMINA_SHORT=2}
stats['item:100:enchant:healing']={ITEM_MOD_INTELLECT_SHORT=6,ITEM_MOD_STAMINA_SHORT=4}
stats['item:300']={ITEM_MOD_INTELLECT_SHORT=1}
local cards=NS.Compare.BuildCards(candidate)
assert(#cards==2 and cards[1].item.link=='item:300' and cards[2].name=='Restoration')
local delta=NS.Compare.Delta(candidate,cards[2].item)
assert(#delta==2 and delta[1]:find('+4',1,true) and delta[2]:find('-2',1,true), 'candidate minus saved item')
assert(NS.Compare.Delta(candidate,{ignored=true})==nil)
assert(NS.Compare.Delta(candidate,{itemID=999})==nil)
assert(#NS.Compare.Delta(candidate,{empty=true})==2)
equipTypes[candidate]='INVTYPE_FINGER'
inventory[11]='item:300'; inventory[12]='item:300'
sets[1].items[11]=100; sets[1].items[12]=100
sets[1].locations[11]=500; sets[1].locations[12]=500
NS.Cache.Refresh()
cards=NS.Compare.BuildCards(candidate)
assert(#cards==4 and cards[1].slot==11 and cards[2].slot==12 and cards[4].slot==12, 'both ring slots for every set')
inventory[12]=nil; sets[1].ignored={[12]=true}; NS.Cache.Refresh()
cards=NS.Compare.BuildCards(candidate)
assert(#cards==2 and cards[1].slot==11 and cards[2].slot==11, 'empty and ignored slots are not shown')
equipTypes[candidate]='INVTYPE_2HWEAPON'
inventory[16]='item:300'; inventory[17]='item:100:enchant:healing'
cards=NS.Compare.BuildCards(candidate)
assert(cards[1].paired.link==inventory[17] and cards[2].included)
delta=NS.Compare.Delta(candidate,cards[1].item,cards[1].paired)
assert(delta[1]:find('+3',1,true), 'two-handed replacement subtracts both old hands')
local received
C_TooltipComparison={GetItemComparisonDelta=function(a,b,p,add)
    received={a,b,p,add}; return {'native delta'}
end}
delta=NS.Compare.Delta(candidate,cards[1].item,cards[1].paired)
assert(delta[1]=='native delta' and received[3].hyperlink==inventory[17] and received[4]==false)
''')
print("PASS: all sets/current gear, paired slots, missing data, signed deltas, two-hand replacement")

lua.execute(r'''
equipTypes['item:200']='INVTYPE_WAIST'
GameTooltip.link='item:200'; GameTooltip:Show(); compareHeld=true
Tick()
assert(GearSetToolsCompare1:IsShown() and GearSetToolsCompare2:IsShown())
assert(GearSetToolsCompare2.link=='item:100:enchant:healing', 'renders exact full tooltip')
assert(GearSetToolsCompare2.gstHeader.label.text=='Restoration')
compareHeld=false; Tick()
assert(not GearSetToolsCompare1:IsShown() and not GearSetToolsCompare2:IsShown(), 'hide on Shift release')
compareHeld=true; Tick(); GameTooltip:Hide(); Tick()
assert(not GearSetToolsCompare1:IsShown(), 'hide when original tooltip disappears')
-- Many full tooltips must page, without going beyond the screen.
UIParent:SetSize(1000,600)
for id=2,12 do sets[id]={name='Set '..id,icon=id,items={[6]=100},locations={[6]=500}} end
NS.Cache.Refresh(); GameTooltip:Show(); Tick()
local before={}
for i=1,13 do before[i]=_G['GearSetToolsCompare'..i]:IsShown() end
NS.Compare.NextPage()
local changed=false
for i=1,13 do
    local tip=_G['GearSetToolsCompare'..i]
    if before[i]~=tip:IsShown() then changed=true end
    if tip:IsShown() then
        local x,y=tip.point[4]*tip.scale,tip.point[5]*tip.scale
        assert(x>=0 and x+tip:GetWidth()*tip.scale<=UIParent:GetWidth()+1)
        assert(y-tip:GetHeight()*tip.scale>=0 and y+25*tip.scale<=UIParent:GetHeight()+1)
    end
end
assert(changed,'next comparison page')
assert(GameTooltip.point[4] * GameTooltip.scale < 1000, 'candidate anchored in comparison group')
local candidateX = GameTooltip.point[4] * GameTooltip.scale
local candidateY = GameTooltip.point[5] * GameTooltip.scale
local firstTip
for i=1,13 do if _G['GearSetToolsCompare'..i]:IsShown() then firstTip=_G['GearSetToolsCompare'..i]; break end end
assert(firstTip.point[4]*firstTip.scale > candidateX and firstTip.point[5]*firstTip.scale == candidateY,
    'hovered item comes immediately before comparison cards')
compareHeld=false; Tick(); assert(GameTooltip:GetScale()==1,'restore candidate scale on Shift release')
''')
print("PASS: full tooltip rendering, headers, visibility, screen bounds, comparison pages")

for path in ROOT.glob("*.lua"):
    lua.execute("assert(loadstring(...))", path.read_text(encoding="utf-8"))
print("PASS: all addon files compile as Lua 5.1")

if len(sys.argv) > 1:
    actual = new_runtime()
    actual.execute(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
    actual.execute(r'''
    for guid, db in pairs(GearSetToolsDB.characters) do
        playerGUID=guid
        for id,s in pairs(db.sets) do
            sets[id]={name=s.name,icon=s.icon,items={},locations={}}
            for slot,item in pairs(s.slots) do
                sets[id].items[slot]=item.itemID
                sets[id].locations[slot]=item.empty and 0 or item.location
                if item.source=='equipped' then
                    inventory[slot]=item.link
                    locations[item.location]={isPlayer=true,slot=slot}
                end
            end
        end
    end
    NS.Cache.Refresh()
    local restored
    for _,s in pairs(NS.Cache.GetSets()) do if s.name=='Restoration' then restored=s end end
    assert(restored.slots[15].link:find('item:6901:',1,true),'real bank cloak resolves')
    equipTypes['item:200']='INVTYPE_CLOAK'
    local cards=NS.Compare.BuildCards('item:200')
    assert(#cards==2 and cards[1].name=='Feral (Currently Equipped)' and cards[2].name=='Restoration')
    ''')
    print("PASS: actual SavedVariables restores banked Restoration cloak and merges equipped Feral")
