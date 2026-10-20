using UnrealBuildTool;

public class TaskProbe : ModuleRules
{
	public TaskProbe(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "InputCore" });
		PrivateDependencyModuleNames.AddRange(new string[] { "AIModule", "ApplicationCore", "Json", "RenderCore", "Slate", "SlateCore", "UMG" });
	}
}
