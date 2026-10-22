using UnrealBuildTool;

public class __PROJECT__ : ModuleRules
{
	public __PROJECT__(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		// flat module layout: "AutoPlay/AutoPlaySubsystem.h" and sub-folders include each other by file name
		PrivateIncludePaths.Add(ModuleDirectory);
		PrivateIncludePaths.Add(System.IO.Path.Combine(ModuleDirectory, "AutoPlay"));

		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "InputCore", "EnhancedInput", "UMG" });
		// AutoPlay drop-in (AutoPlay/AutoPlaySubsystem.h/.cpp, contract v1.4)
		PrivateDependencyModuleNames.AddRange(new string[] { "Slate", "SlateCore", "AudioMixer" });
	}
}
