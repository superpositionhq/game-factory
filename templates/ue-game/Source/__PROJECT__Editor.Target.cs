using UnrealBuildTool;
using System.Collections.Generic;

public class __PROJECT__EditorTarget : TargetRules
{
	public __PROJECT__EditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.V4;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_3;

		// UE 5.3 + MSVC 14.4x: <sanitizer/asan_interface.h> exists, so ConcurrentLinearAllocator.h reaches
		// "#elif __has_feature(...)", which MSVC rejects (C4668/C4067). We never build with ASan.
		bOverrideBuildEnvironment = true;
		GlobalDefinitions.Add("PLATFORM_HAS_ASAN_INCLUDE=0");

		ExtraModuleNames.Add("__PROJECT__");
	}
}
