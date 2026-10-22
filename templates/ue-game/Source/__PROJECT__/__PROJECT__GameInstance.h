#pragma once

#include "CoreMinimal.h"
#include "Engine/GameInstance.h"
#include "__PROJECT__GameInstance.generated.h"

/**
 * Game instance. Wires the AutoPlay drop-in (AutoPlay/AutoPlaySubsystem.h, contract v1.4): when the game is started
 * with -AutoPlay -Scenario=N, StartScenario opens scenario N's map. The game mode then applies the start state, calls
 * UAutoPlaySubsystem::ScenarioStarted(<display name>) once the player has control, spawns the bot (which acts only
 * through UAutoPlaySubsystem::Inject) and calls FinishRun("win"/"lose", Score) at the end.
 */
UCLASS(Config = Game)
class U__PROJECT__GameInstance : public UGameInstance
{
	GENERATED_BODY()

public:
	virtual void Init() override;

	/** Map per scenario, index 0 = scenario 1 (Config/DefaultGame.ini: +ScenarioMaps=/Game/Maps/L_Example). */
	UPROPERTY(Config, EditDefaultsOnly, Category = "Scenarios")
	TArray<FString> ScenarioMaps;

	/** Scenario the current map was opened for (0 = normal play). */
	UPROPERTY(Transient, BlueprintReadOnly, Category = "Scenarios")
	int32 PendingScenario = 0;
};
