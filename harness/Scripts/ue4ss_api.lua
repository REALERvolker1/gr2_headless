---@meta
-- Type declarations for the UE4SS v3.0.1 calls used here, not a runtime module.
---@class LabName
---@field ToString fun(self: LabName): string
---@class CaptureObject
---@field GetFName fun(self: CaptureObject): LabName
---@class LabObject: CaptureObject
---@field Pawn LabObject|nil
---@field CurrentCoreLevel integer
---@field MotherboardInfo table
---@field GetTimeSeconds fun(self: LabObject, context: table): number
---@field GetAudioTimeSeconds fun(self: LabObject, context: table): number
---@field OpenLevel fun(self: LabObject, context: LabObject, level: LabName, absolute: boolean, options: string)
---@field IsValid fun(self: LabObject): boolean
---@field IsA fun(self: LabObject, path: string): boolean
---@field GetClass fun(self: LabObject): LabObject
---@field GetWorld fun(self: LabObject): LabObject
---@field GetOuter fun(self: LabObject): LabObject
---@field GetAddress fun(self: LabObject): integer
---@field GetFullName fun(self: LabObject): string
---@field GetSuperStruct fun(self: LabObject): LabObject
---@field ForEachProperty fun(self: LabObject, callback: fun(property: CaptureObject))
---@field ForEachFunction fun(self: LabObject, callback: fun(func: LabObject))
---@type fun(name: string): LabObject
StaticFindObject = nil
---@type fun(name: string): LabObject[]|nil
FindAllOf = nil
---@type fun(name: string): LabObject
LoadAsset = nil
---@type fun(name: string): LabName
FName = nil
---@type fun(callback: fun())
ExecuteInGameThread = nil
---@type fun(milliseconds: integer, callback: fun(): boolean)
LoopAsync = nil
