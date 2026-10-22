#include "__PROJECT__GameInstance.h"
#include "AutoPlaySubsystem.h"
#include "Kismet/GameplayStatics.h"

void U__PROJECT__GameInstance::Init()
{
	Super::Init();

	UAutoPlaySubsystem* AP = GetSubsystem<UAutoPlaySubsystem>();
	if (AP && AP->IsAutoPlay())
	{
		AP->StartScenario = [this](int32 Scenario)
		{
			PendingScenario = Scenario;
			if (ScenarioMaps.IsValidIndex(Scenario - 1))
			{
				UGameplayStatics::OpenLevel(this, FName(*ScenarioMaps[Scenario - 1]), true, FString::Printf(TEXT("Scenario=%d"), Scenario));
			}
			else if (UAutoPlaySubsystem* Sub = GetSubsystem<UAutoPlaySubsystem>())
			{
				Sub->FinishRun(TEXT("error"), 0.0, FString::Printf(TEXT("\"reason\":\"no map for scenario %d\""), Scenario));
			}
		};
	}
}
