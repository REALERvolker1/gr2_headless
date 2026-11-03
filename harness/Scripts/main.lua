local Json = require("gr2_json")
local Areas = require("areas")
local actors = {}
local spawned = {}
local platform = nil
local physics_cube = nil
local platform_time = 0
local current = "runway"
local recording = false
local pending = false
local sequence = 0
local previous = nil
---@type string|boolean
local sampling_error = false
-- UE4SS supplies dynamic reflected wrappers. Their complete game-specific types
-- are discovered at runtime; keep wrapper access confined to this module.
---@return table|nil, table|nil
local function player()
	for _, controller in ipairs(FindAllOf("PlayerController") or {}) do
		local pawn = controller.Pawn
		if pawn and pawn:IsValid() and pawn:IsA("/Script/Ghostrunner.PlayerCharacter") then
			return pawn, controller
		end
	end
end
---@return table
local function context()
	local pawn, controller = player()
	assert(pawn and controller, "Real GR2 player not possessed; travel to Levels_Zoo first")
	return { pawn = pawn, controller = controller, world = pawn:GetWorld() }
end
---@param value table
---@return table
local function vector(value)
	return { x = value.X, y = value.Y, z = value.Z }
end
---@param values number[]
---@return table
local function unreal_vector(values)
	return { X = values[1], Y = values[2], Z = values[3] }
end
---@return table|nil
local function stamina()
	local c = context()
	for _, object in ipairs(FindAllOf("StaminaWorldSubsystem") or {}) do
		if object:GetOuter():GetAddress() == c.world:GetAddress() then
			return object
		end
	end
end
local Fields = require("copy")
-- Selection follows the prior recorder's known declarations.
local Settings = {
	fast_fields = {
		bIsDashing = true,
		bIsInSensoryBoost = true,
		bIsDashingInAir = true,
		bIsDashReady = true,
		bIsAirDashReady = true,
		CurrentDashCooldown = true,
		DashCharges = true,
		bOnWall = true,
		bWallOnRight = true,
		bWallOnLeft = true,
		bCanWallrun = true,
		bIsClimbingWall = true,
		bIsCrouched = true,
		bPressedJump = true,
		JumpCurrentCount = true,
		JustUsedSlide = true,
		bCanStartSlide = true,
		CurrentJumpType = true,
		MoveRightInput = true,
		MoveForwardInput = true,
		DashLastTimeUsed = true,
		DashCooldown = true,
		DashStaminaCost = true,
		AirDashStaminaCost = true,
		SensoryBoostStaminaUsed = true,
	},
}
local plans = {}
---@param object table
---@return table
local function states(object)
	local class = object:GetClass()
	local name = class:GetFullName()
	local plan = plans[name]
	if not plan then
		plan = {}
		while class and class:IsValid() do
			class:ForEachProperty(function(property)
				local field = property:GetFName():ToString()
				if Settings.fast_fields[field] then
					plan[field] = true
				end
			end)
			class = class:GetSuperStruct()
		end
		plans[name] = plan
	end
	local values = {}
	for field in pairs(plan) do
		local value = object[field]
		if type(value) == "boolean" or type(value) == "number" then
			values[field] = value
		end
	end
	return values
end
---@return table
local function upgrades()
	local c = context()
	for _, object in ipairs(FindAllOf("UpgradesSubsystem") or {}) do
		if object:GetOuter():GetAddress() == c.world:GetAddress() then
			return {
				object = object:GetFullName(),
				core_level = object.CurrentCoreLevel,
				motherboard = Fields.copy(object.MotherboardInfo, 0),
			}
		end
	end
	return { available = false }
end
---@return table
local function observe()
	local c = context()
	local statics = StaticFindObject("/Script/Engine.Default__GameplayStatics")
	local movement = c.pawn.CharacterMovement
	local look = c.controller:GetControlRotation()
	local resource = stamina()
	return {
		pawn = c.pawn:GetFullName(),
		world = c.world:GetFullName(),
		area = current,
		time = statics:GetTimeSeconds(c.pawn),
		audio_time = statics:GetAudioTimeSeconds(c.pawn),
		position = vector(c.pawn:K2_GetActorLocation()),
		control_rotation = { pitch = look.Pitch, yaw = look.Yaw, roll = look.Roll },
		velocity = vector(c.pawn:GetVelocity()),
		acceleration = vector(movement.Acceleration),
		movement_mode = movement.MovementMode,
		custom_movement_mode = movement.CustomMovementMode,
		stamina = resource and resource:GetStamina() or false,
		player_state = states(c.pawn),
		movement_state = states(movement),
		stamina_state = resource and states(resource) or {},
	}
end
---@param class_path string
---@param position number[]
---@param rotation? table
---@return table
local function spawn(class_path, position, rotation)
	local c = context()
	local class = StaticFindObject(class_path)
	if not class:IsValid() then
		class = LoadAsset(class_path)
	end
	assert(class:IsValid(), "Class unavailable: " .. class_path)
	local actor = c.world:SpawnActor(class, unreal_vector(position), rotation or { Pitch = 0, Yaw = 0, Roll = 0 })
	assert(actor:IsValid(), "Spawn failed: " .. class_path)
	actors[#actors + 1] = actor
	return actor
end
---@param name string
---@return table
local function teleport(name)
	local area = assert(Areas[name], "Unknown area")
	local c = context()
	c.pawn.CharacterMovement:StopMovementImmediately()
	local hit = {}
	c.pawn:K2_SetActorLocation(unreal_vector(area.origin), false, hit, true)
	c.controller:SetControlRotation({ Pitch = 0, Yaw = 0, Roll = 0 })
	current = name
	previous = nil
	return observe()
end
---@return table
local function build()
	sampling_error = false
	for _, actor in ipairs(actors) do
		if actor:IsValid() then
			actor:K2_DestroyActor()
		end
	end
	actors = {}
	spawned = {}
	platform = nil
	local mesh = LoadAsset("/Engine/BasicShapes/Cube.Cube")
	assert(mesh:IsValid(), "Cooked cube unavailable")
	local counts = {}
	for name, area in pairs(Areas) do
		for _, box in ipairs(area.boxes) do
			local actor = spawn(
				"/Script/Engine.StaticMeshActor",
				box.center,
				{ Pitch = box.pitch or 0, Yaw = box.yaw or 0, Roll = 0 }
			)
			local component = actor.StaticMeshComponent
			component:SetMobility(2)
			assert(component:SetStaticMesh(mesh), "SetStaticMesh failed")
			component:SetCollisionEnabled(3)
			component:SetCollisionResponseToAllChannels(2)
			actor:SetActorScale3D({ X = box.size[1] / 100, Y = box.size[2] / 100, Z = box.size[3] / 100 })
		end
		counts[name] = #area.boxes
	end
	-- Fixture targets survive the lighter reset; explicit spawn commands do not.
	spawn(
		"/Game/Blueprints/LD_Blueprints/BP_Grappling_Point.BP_Grappling_Point_C",
		{ 0, Areas.grapple.origin[2], 11000 }
	)
	spawn(
		"/Game/Blueprints/LD_Blueprints/BP_Grappling_Point.BP_Grappling_Point_C",
		{ 2000, Areas.grapple.origin[2], 12000 }
	)
	local physics = Areas.physics
	local dynamic = spawn("/Script/Engine.StaticMeshActor", { 0, physics.origin[2], 10500 })
	dynamic.StaticMeshComponent:SetMobility(2)
	dynamic.StaticMeshComponent:SetStaticMesh(mesh)
	dynamic.StaticMeshComponent:SetCollisionEnabled(3)
	dynamic.StaticMeshComponent:SetCollisionResponseToAllChannels(2)
	dynamic.StaticMeshComponent:SetSimulatePhysics(true)
	physics_cube = dynamic
	platform = spawn("/Script/Engine.StaticMeshActor", { 2000, physics.origin[2], 10300 })
	platform.StaticMeshComponent:SetMobility(2)
	platform.StaticMeshComponent:SetStaticMesh(mesh)
	platform.StaticMeshComponent:SetCollisionEnabled(3)
	platform.StaticMeshComponent:SetCollisionResponseToAllChannels(2)
	platform:SetActorScale3D({ X = 8, Y = 8, Z = 1 })
	platform_time = StaticFindObject("/Script/Engine.Default__GameplayStatics"):GetTimeSeconds(context().pawn)
	teleport("runway")
	return { areas = counts, actors = #actors }
end
---@param parts string[]
---@return table
local function execute(parts)
	local command = parts[2]
	if command == "status" then
		local worlds = {}
		for _, world in ipairs(FindAllOf("World") or {}) do
			worlds[#worlds + 1] = world:GetFullName()
		end
		local pawn = player()
		return {
			worlds = worlds,
			pawn = pawn and pawn:GetFullName() or false,
			actors = #actors,
			recording = recording,
			sampling_error = sampling_error,
		}
	elseif command == "inspect" then
		local objects = {}
		for _, object in ipairs(FindAllOf(parts[3]) or {}) do
			objects[#objects + 1] = object:GetFullName()
			if #objects >= 100 then
				break
			end
		end
		return { objects = objects }
	elseif command == "functions" then
		local object = StaticFindObject(parts[3])
		local names = {}
		object:ForEachFunction(function(func)
			names[#names + 1] = func:GetFullName()
		end)
		return { functions = names }
	elseif command == "travel" then
		local controllers = FindAllOf("PlayerController") or {}
		assert(controllers[1], "No player controller")
		local statics = StaticFindObject("/Script/Engine.Default__GameplayStatics")
		actors = {}
		platform = nil
		recording = false
		statics:OpenLevel(controllers[1], FName(parts[3]), true, "")
		return { travel_requested = parts[3] }
	elseif command == "physics" then
		assert(physics_cube and physics_cube:IsValid() and platform and platform:IsValid(), "Build physics area first")
		return {
			cube = vector(physics_cube:K2_GetActorLocation()),
			platform = vector(platform:K2_GetActorLocation()),
			cube_velocity = vector(physics_cube:GetVelocity()),
		}
	elseif command == "pose" then
		local c = context()
		c.pawn.CharacterMovement:StopMovementImmediately()
		c.pawn:K2_SetActorLocation(
			{ X = assert(tonumber(parts[3])), Y = assert(tonumber(parts[4])), Z = assert(tonumber(parts[5])) },
			false,
			{},
			true
		)
		c.controller:SetControlRotation({ Pitch = tonumber(parts[7]) or 0, Yaw = tonumber(parts[6]) or 0, Roll = 0 })
		previous = nil
		return observe()
	elseif command == "upgrades" then
		return upgrades()
	elseif command == "observe" then
		return observe()
	elseif command == "build" then
		return build()
	elseif command == "teleport" then
		return teleport(parts[3])
	elseif command == "reset" then
		for _, actor in ipairs(spawned) do
			if actor:IsValid() then
				actor:K2_DestroyActor()
			end
		end
		spawned = {}
		teleport(current)
		local resource = stamina()
		if resource then
			-- The qualified native thunk takes float + bool, even though the body ignores bool.
			resource:SetStamina(100, false)
		end
		return observe()
	elseif command == "set_stamina" then
		local resource = assert(stamina(), "Stamina subsystem unavailable")
		resource:SetStamina(assert(tonumber(parts[3]), "Expected stamina number"), false)
		return observe()
	elseif command == "record_start" then
		assert(not sampling_error, "Sampler failed; inspect status and rebuild")
		recording = true
		previous = nil
		return { recording = true }
	elseif command == "record_stop" then
		recording = false
		return { recording = false, sequence = sequence, sampling_error = sampling_error }
	elseif command == "spawn" then
		local paths = {
			pistol = "/Game/ArtificialIntelligence/EnemyPistol/BP_EnemyPistol.BP_EnemyPistol_C",
			shinobi = "/Game/ArtificialIntelligence/EnemyShinobi/BP_EnemyShinobi.BP_EnemyShinobi_C",
			grapple = "/Game/Blueprints/LD_Blueprints/BP_Grappling_Point.BP_Grappling_Point_C",
		}
		local path = assert(paths[parts[3]], "Supported types: pistol, shinobi, grapple")
		local a = Areas[current]
		local actor = spawn(
			path,
			{ tonumber(parts[4]) or 0, a.origin[2] + (tonumber(parts[5]) or 0), tonumber(parts[6]) or 10100 }
		)
		spawned[#spawned + 1] = actor
		return { actor = actor:GetFullName() }
	end
	error("Unknown command: " .. tostring(command))
end
---@return boolean
local function poll()
	if pending then
		return false
	end
	local stream = io.open("gt.request", "r")
	if not stream then
		return false
	end
	local line = stream:read("*l")
	stream:close()
	os.remove("gt.request")
	local parts = {}
	for part in line:gmatch("%S+") do
		parts[#parts + 1] = part
	end
	pending = true
	ExecuteInGameThread(function()
		local ok, result = pcall(execute, parts)
		local reply = io.open("gt.reply.pending", "w")
		if reply then
			reply:write(Json.encode({ id = parts[1], ok = ok, result = ok and result or tostring(result) }))
			reply:close()
			os.remove("gt.reply")
			os.rename("gt.reply.pending", "gt.reply")
		end
		pending = false
	end)
	return false
end
local sample_pending = false
---@return boolean
local function sample()
	if (not recording and not platform) or sample_pending then
		return false
	end
	sample_pending = true
	ExecuteInGameThread(function()
		local success, failure = pcall(function()
			if platform and platform:IsValid() then
				local time = StaticFindObject("/Script/Engine.Default__GameplayStatics"):GetTimeSeconds(context().pawn)
					- platform_time
				platform:K2_SetActorLocation(
					{ X = 2000 + 500 * math.sin(time * math.pi / 2), Y = Areas.physics.origin[2], Z = 10300 },
					false,
					{},
					true
				)
			end
			if not recording then
				sample_pending = false
				return
			end
			local row = observe()
			if not previous or row.time ~= previous.time then
				sequence = sequence + 1
				row.sequence = sequence
				row.kind = "sample"
				if previous and row.time > previous.time then
					local dt = row.time - previous.time
					row.observed_acceleration = {
						x = (row.velocity.x - previous.velocity.x) / dt,
						y = (row.velocity.y - previous.velocity.y) / dt,
						z = (row.velocity.z - previous.velocity.z) / dt,
					}
				end
				previous = row
				local stream = io.open("gt.telemetry.jsonl", "a")
				assert(stream, "Cannot open telemetry file")
				assert(stream:write(Json.encode(row) .. "\n"))
				assert(stream:close())
			end
			sample_pending = false
		end)
		sample_pending = false
		if not success then
			sampling_error = tostring(failure)
			recording = false
			platform = nil
			print("[GroundTruth] sampling failed: " .. sampling_error .. "\n")
		end
	end)
	return false
end
print("[GroundTruth] command bridge loaded\n")
LoopAsync(100, poll)
LoopAsync(50, sample)
