using UnrealBuildTool;
using System.Collections.Generic;

public class __PROJECT__EditorTarget : TargetRules
{
	public __PROJECT__EditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.V6;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_7;

		ExtraModuleNames.Add("__PROJECT__");
	}
}
