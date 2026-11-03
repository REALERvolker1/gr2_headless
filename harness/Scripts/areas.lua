-- Authored geometry. Dimensions and coordinates are Unreal centimeters.
---@class TestBox
---@field center number[]
---@field size number[]
---@field pitch? number
---@field yaw? number
---@class TestArea
---@field origin number[]
---@field boxes TestBox[]
---@field description string
---@type table<string, TestArea>
local areas = {}
---@param name string
---@param y number
---@param description string
---@return TestArea
local function area(name, y, description)
	local value = { origin = { -4500, y, 10100 }, boxes = {}, description = description }
	areas[name] = value
	return value
end
---@param a TestArea
---@param x number
---@param y number
---@param z number
---@param sx number
---@param sy number
---@param sz number
---@param pitch? number
---@param yaw? number
local function box(a, x, y, z, sx, sy, sz, pitch, yaw)
	a.boxes[#a.boxes + 1] = { center = { x, a.origin[2] + y, z }, size = { sx, sy, sz }, pitch = pitch, yaw = yaw }
end
local runway = area("runway", 0, "10000 x 1000 runway; 1000 cm marks; +X heading")
box(runway, 0, 0, 9950, 10000, 1000, 100)
for x = -4000, 4000, 1000 do
	box(runway, x, 520, 10010, 20, 40, 20)
end
local gaps = area("gaps", 10000, "400, 600, 800 cm gaps; platforms rise 100, 200, 300 cm")
box(gaps, -3500, 0, 9950, 3000, 1500, 100)
box(gaps, -600, 0, 10000, 2000, 1500, 200)
box(gaps, 2000, 0, 10050, 2000, 1500, 300)
box(gaps, 4800, 0, 10100, 2000, 1500, 400)
local walls = area("walls", 20000, "4000 cm wall; 1500 cm high; second wall at 15 degrees")
box(walls, 0, 0, 9950, 10000, 1600, 100)
box(walls, -1500, -500, 10750, 4000, 100, 1500)
box(walls, 2500, 500, 10750, 3000, 100, 1500, 0, 15)
local terrain = area("terrain", 30000, "15 degree ramp; 20 cm stair risers; 20 cm rail")
box(terrain, 0, 0, 9950, 10000, 2000, 100)
box(terrain, -2000, 0, 10200, 2000, 700, 100, 15)
for i = 1, 10 do
	box(terrain, i * 100, 0, 10000 + i * 10, 100, 700, i * 20)
end
box(terrain, 2500, 0, 10300, 2000, 20, 20)
local grapple = area("grapple", 40000, "native grapple targets at +X=0/2000, Z=11000/12000")
box(grapple, 0, 0, 9950, 10000, 3000, 100)
local combat = area("combat", 50000, "8000 x 6000 arena; explicit enemy spawn command")
box(combat, 0, 0, 9950, 10000, 6000, 100)
local resources = area("resources", 60000, "10000 x 2000 runway for stamina and copied upgrade loadout")
box(resources, 0, 0, 9950, 10000, 2000, 100)
local physics = area("physics", 70000, "10000 x 3000 floor; 100 cm falling cube; 800 cm moving platform")
box(physics, 0, 0, 9950, 10000, 3000, 100)
return areas
