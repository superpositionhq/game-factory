using UnrealBuildTool;
using System.Collections.Generic;

public class __PROJECT__Target : TargetRules
{
	public __PROJECT__Target(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.V6;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_7;

		// Shipping recording builds: do NOT set bUseLoggingInShipping (the launcher engine's precompiled Shipping
		// libraries have no log support and the link fails). No bOverrideBuildEnvironment either: the installed
		// engine refuses a target that changes the shared build environment.
		ExtraModuleNames.Add("__PROJECT__");
	}
}
