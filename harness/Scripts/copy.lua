-- Bounded serializer adapted from earlier recorder work.
local Copy = {}
local object_names = {}
local struct_members = {}
---@param object unknown
---@param key string|integer
---@return unknown
local function read(object, key)
	local ok, value = pcall(function()
		return object[key]
	end)
	if ok then
		return value
	end
	return nil
end
local struct_fields = {
	"X",
	"Y",
	"Z",
	"Pitch",
	"Yaw",
	"Roll",
	"bBlockingHit",
	"bStartPenetrating",
	"bWalkableFloor",
	"bLineTrace",
	"FloorDist",
	"LineDist",
	"HitResult",
	"Time",
	"Distance",
	"Location",
	"ImpactPoint",
	"Normal",
	"ImpactNormal",
	"TraceStart",
	"TraceEnd",
	"PenetrationDepth",
	"Actor",
	"Component",
	"BoneName",
	"FaceIndex",
	"Type",
	"State",
	"bIsBoosted",
	"IsAvailable",
	"AvailableOnTier",
	"ShardCost",
	"DataCost",
	"BoostCondition",
	"RequiredTier",
	"Branches",
	"Sockets",
	"KeyName",
	"Translation",
	"Rotation",
	"Scale3D",
}

---@param value unknown
---@param depth integer
---@return JsonValue|nil
function Copy.copy(value, depth)
	local kind = type(value)
	if kind == "boolean" or kind == "number" or kind == "string" then
		return value
	elseif value == nil or depth > 5 then
		return nil
	end
	-- UE4SS __index is a native reflection operation, not a harmless Lua
	-- capability probe. Dispatch on its documented type before touching members.
	local wrapper
	if kind == "userdata" then
		wrapper = value:type()
	elseif kind == "table" then
		local type_method = rawget(value, "type")
		if type(type_method) == "function" then
			wrapper = type_method(value)
		end
	else
		return nil
	end
	if wrapper == "UObject" or wrapper == "UClass" or wrapper == "UStruct" or wrapper == "UFunction" then
		if value:IsValid() then
			local address = value:GetAddress()
			local name = object_names[address]
			if name == nil then
				name = value:GetFullName()
				object_names[address] = name
			end
			return { object = name }
		end
		return { unavailable = true, type = wrapper }
	elseif wrapper == "FName" or wrapper == "FText" then
		return value:ToString()
	elseif wrapper == "TArray" then
		local count = value:GetArrayNum()
		local entries = {}
		for index = 1, math.min(count, 256) do
			local entry = Copy.copy(read(value, index), depth + 1)
			entries[#entries + 1] = entry == nil and { unavailable = true } or entry
		end
		return { count = count, entries = entries, truncated = count > 256 }
	elseif wrapper ~= nil and wrapper ~= "UScriptStruct" then
		return { unavailable = true, type = tostring(wrapper) }
	end
	local members = struct_fields
	if wrapper == "UScriptStruct" then
		local address = value:GetPropertyAddress()
		members = struct_members[address]
		if members == nil then
			local present = {}
			---@param property CaptureObject
			---@return nil
			local function member_info(property)
				present[property:GetFName():ToString()] = true
			end
			local metadata = value
			for _ = 1, 12 do
				if not metadata:IsValid() then
					break
				end
				metadata:ForEachProperty(member_info)
				metadata = metadata:GetSuperStruct()
			end
			members = {}
			for _, key in ipairs(struct_fields) do
				if present[key] then
					members[#members + 1] = key
				end
			end
			struct_members[address] = members
		end
	end
	local fields = {}
	for _, key in ipairs(members) do
		if wrapper ~= nil or rawget(value, key) ~= nil then
			local member = Copy.copy(read(value, key), depth + 1)
			if member ~= nil then
				fields[key] = member
			end
		end
	end
	return next(fields) and fields or nil
end

return Copy
