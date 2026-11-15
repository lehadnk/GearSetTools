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
SlashCmdList = {}
frames, timers, messages = {}, {}, {}
local methods = {}
function methods:SetScript(name, fn) self.scripts[name] = fn end
function methods:HookScript(name, fn)
    local prev = self.scripts[name]
    self.scripts[name] = function(...) if prev then prev(...) end; fn(...) end
end
function methods:RegisterEvent(name) self.events[name] = true end
function methods:Show()
    if self.kind=='GameTooltip' and #self.lines==0 and not self.link and not self.GetPrimaryTooltipData then
        self.shown=false
    else self.shown=true end
end
function methods:Hide()
    local wasShown=self.shown
    self.shown = false
    if self.kind=='GameTooltip' and self.name and self.name:find('GearSetToolsCompare',1,true) then
        self.lines={}; self.link=nil
    end
    if wasShown and self.scripts and self.scripts.OnHide then self.scripts.OnHide(self) end
end
function methods:GetOwner() return self.owner end
function methods:SetOwner(owner) self.owner=owner end
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
function methods:SetPoint(...) self.point = {...}; self.setPointCalls=(self.setPointCalls or 0)+1 end
function methods:ClearAllPoints() self.point = nil end
function methods:ClearLines() self.lines = {}; self.link = nil end
function methods:AddLine(text) self.lines[#self.lines+1] = text end
function methods:SetHyperlink(link) self.link = link; self.lines = {link} end
function methods:GetItem() return 'item', self.link end
function methods:SetText(text) self.text = text end
function methods:GetStringHeight() return math.ceil(#(self.text or '') * 7 / (self.width or 200)) * 14 end
function methods:SetTexture(texture) self.texture = texture end
function methods:CreateTexture() return setmetatable({}, {__index = methods}) end
function methods:CreateFontString() return setmetatable({}, {__index = methods}) end
for _, name in ipairs({'SetFrameStrata','EnableMouse','SetClampedToScreen','SetBackdrop','SetBackdropColor',
    'SetBackdropBorderColor','SetAllPoints','SetJustifyH','SetFrameLevel','SetTexCoord'}) do
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
function hooksecurefunc(object, method, callback)
    if type(object)=='string' then return end
    local original=object[method]
    object[method]=function(...)
        local result={original(...)}
        callback(...)
        return unpack(result)
    end
end
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


def new_runtime(with_markers=False):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(STUBS)
    if with_markers:
        lua.globals().LoadModule((ROOT / "GearSetTools.lua").read_text(encoding="utf-8"))
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
local stableX,stableY=GameTooltip.point[4],GameTooltip.point[5]
local anchorCalls=GameTooltip.setPointCalls
Tick(); Tick()
assert(GameTooltip.setPointCalls==anchorCalls,'stable anchors are not cleared and rewritten every frame')
assert(GearSetToolsCompare1.gstHeader:GetHeight()>=GearSetToolsCompare1.gstHeader.label:GetStringHeight()+12)
for i=1,20 do
    GameTooltip:SetPoint('BOTTOMLEFT',UIParent,'BOTTOMLEFT',200,100+i)
    assert(GameTooltip.point[1]=='TOPLEFT' and GameTooltip.point[4]==stableX and GameTooltip.point[5]==stableY,
        'native reposition must be corrected synchronously, before the next timer tick')
end
compareHeld=false; Tick()
assert(not GearSetToolsCompare1:IsShown() and not GearSetToolsCompare2:IsShown(), 'hide on Shift release')
GameTooltip:SetPoint('BOTTOMLEFT',UIParent,'BOTTOMLEFT',200,100)
assert(GameTooltip.point[1]=='BOTTOMLEFT' and GameTooltip.point[5]==100,'release anchor control outside comparison')
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
        assert(tip.link and #tip.lines>0,'visible comparisons retain full item data after layout')
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
for iteration=1,10 do
    NS.Compare.NextPage()
    local shown=0
    for i=1,13 do
        local tip=_G['GearSetToolsCompare'..i]
        if tip:IsShown() then assert(tip.link and #tip.lines>0); shown=shown+1 end
    end
    assert(shown>0,'page cycling refills tooltips cleared by OnHide')
end
compareHeld=false; Tick(); assert(GameTooltip:GetScale()==1,'restore candidate scale on Shift release')
''')
print("PASS: full tooltip rendering, headers, visibility, screen bounds, comparison pages")

lua.execute(r'''
local sizes={{width=250,height=300},{width=170,height=350},{width=160,height=250},{width=180,height=260}}
local pages=NS.Compare.Layout(sizes,1000,600,8)
assert(#pages==1)
assert(pages[1].positions[2].x==258 and pages[1].positions[3].x==436 and pages[1].positions[4].x==604,
    'narrow tooltips follow actual preceding width, with exactly 8px spacing')
local seen={}
pages=NS.Compare.Layout(sizes,440,400,8)
for _,p in ipairs(pages) do
    assert(p.positions[1].index==1,'candidate first on every page')
    for _,pos in ipairs(p.positions) do
        local size=sizes[pos.index]
        assert(pos.x+size.width<=440 and pos.y+size.height<=400,'all cards inside page bounds')
        if pos.index>1 then assert(not seen[pos.index]); seen[pos.index]=true end
    end
end
assert(seen[2] and seen[3] and seen[4],'pagination preserves every comparison')
''')
print("PASS: compact variable-width layout, pagination bounds, stable anchors, wrapped header height")

startup = new_runtime(with_markers=True)
startup.execute(r'''
sets[0]={name='Restoration',icon=123,items={[6]=100},locations={[6]=1048582}}
inventory[6]='item:100'; locations[1048582]={isPlayer=true,slot=6}
ContainerFrameCombinedBags=CreateFrame('Frame'); ContainerFrameCombinedBags:Show()
local button=CreateFrame('Button',nil,ContainerFrameCombinedBags)
button.itemID=100; button:Show()
Event('PLAYER_LOGIN')
assert(NS.Compare.ready,'all three TOC modules initialize together')
assert(button.children[1] and button.children[1]:IsShown(),'anonymous combined-bag buttons get set badges')
compareHeld=true; GameTooltip.link='item:200'; GameTooltip:Show(); Tick()
assert(GearSetToolsCompare1:IsShown(),'comparison works with markers active')
SlashCmdList.GEARSETTOOLS('debug')
local healthy=false
for _,message in ipairs(messages) do
    assert(not message:find('attempt to',1,true),message)
    if message:find('compare module=true',1,true) then healthy=true end
end
assert(healthy,'slash command includes comparison module diagnostics')
''')
print("PASS: complete TOC startup, anonymous combined-bag badges, comparison and slash diagnostics together")

modern = new_runtime()
modern.execute(r'''
inventory[6]='item:300'
GameTooltip.GetItem=function() return nil end
GameTooltip.GetPrimaryTooltipData=function() return {hyperlink='item:200'} end
C_CVar.GetCVarBool=function() return true end
compareHeld=false; GameTooltip:Show(); Tick()
assert(GearSetToolsCompare1 and GearSetToolsCompare1:IsShown(),'modern tooltip data works without GetItem or Shift')
assert(NS.Compare.TooltipLink(GameTooltip)=='item:200')
GameTooltip.GetPrimaryTooltipData=function() return {guid='test-guid'} end
C_Item.GetItemLinkByGUID=function(guid) assert(guid=='test-guid'); return 'item:200' end
assert(NS.Compare.TooltipLink(GameTooltip)=='item:200','GUID resolves exact hyperlink')
GameTooltip:Hide()
GameTooltipTooltip=CreateFrame('GameTooltip')
GameTooltipTooltip.link='item:201'; GameTooltipTooltip:Show(); Tick()
assert(GearSetToolsCompare1:IsShown(),'embedded item tooltip is discovered')
''')
print("PASS: modern tooltip payloads, exact GUID links, embedded tooltips, Always Compare without Shift")

loot = new_runtime()
loot.execute(r'''
inventory[6]='item:300'
local bagButton=CreateFrame('Button')
local lootButton=CreateFrame('Button')
GameTooltip:SetOwner(bagButton)
GameTooltip.link='item:200'; GameTooltip:Show(); compareHeld=true; Tick()
assert(GearSetToolsCompare1:IsShown())
-- A new loot button takes ownership before its item data has been set.
GameTooltip:SetOwner(lootButton)
GameTooltip:SetPoint('BOTTOMLEFT',UIParent,'BOTTOMLEFT',51,67)
assert(GameTooltip.point[5]==67,'old comparison must not hijack a new loot owner')
equipTypes['item:900']='' -- quest item, not equippable
GameTooltip.link='item:900'; GameTooltip.lines={'Quest item', 'Required for a quest'}
Tick()
assert(not GearSetToolsCompare1:IsShown())
assert(GameTooltip:IsShown() and GameTooltip.link=='item:900' and #GameTooltip.lines==2)
assert(GameTooltip.point[1]=='BOTTOMLEFT' and GameTooltip.point[5]==67,'quest tooltip anchors preserved')
-- The same owner can switch from gear to quest loot too.
GameTooltip.link='item:200'; Tick(); assert(GearSetToolsCompare1:IsShown())
GameTooltip.link='item:900'; GameTooltip.lines={'Quest loot'}
GameTooltip:SetPoint('TOPRIGHT',UIParent,'TOPRIGHT',-13,-24)
Tick()
assert(GameTooltip.point[1]=='TOPRIGHT' and GameTooltip.point[5]==-24)
assert(GameTooltip.lines[1]=='Quest loot')
-- Loot event lifecycle clears comparisons without changing loot content.
LootFrame=CreateFrame('Frame'); LootFrame:Show()
LootFrame.slots={{link='item:900',quest=true}}
GameTooltip.link='item:200'; Tick(); assert(GearSetToolsCompare1:IsShown())
Event('LOOT_OPENED')
assert(not GearSetToolsCompare1:IsShown())
assert(LootFrame:IsShown() and #LootFrame.slots==1 and LootFrame.slots[1].quest)
GameTooltip:Hide(); Tick()
GameTooltip:SetPoint('BOTTOMLEFT',UIParent,'BOTTOMLEFT',10,20)
assert(GameTooltip.point[5]==20,'hidden source releases anchor hooks')
''')
print("PASS: gear-to-quest loot transitions, owner changes, native quest content/anchors, loot lifecycle")

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
