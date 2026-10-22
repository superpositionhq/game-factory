// The task checker's probe (game-factory tools/task_check): a timed run of the game for a task check's plays.
// Started with -TaskProbe -TaskProbeOut=<dir> [-TaskProbeSeconds=S] [-TaskProbeShots=N] [-TaskProbeInputs=<json file>]:
// N screenshots evenly over S seconds of game time, scripted key presses at their times, the player pawn's position
// and the player's camera (its location, rotation and field of view) every half second, then probe.json in <dir> and
// a clean exit. Without -TaskProbe it does nothing. -TaskProbeEvery=<0.1-1.0> sets the sample interval (default 0.5 s);
// the inputs file may also hold axis events, button clicks, cursor moves and pawn teleports (LoadInputs).
// With -TaskProbeQueries=<json file> (format game-probe-queries/1) it also evaluates the checker's queries on every half
// second sample and adds "measures" (and "query_errors" when a query could not be read) to probe.json; see
// Private/TaskProbeQueries.h and game-factory's docs/task-probes.md and docs/task-check.md.

#pragma once

#include "CoreMinimal.h"
#include "Containers/Ticker.h"
#include "InputCoreTypes.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "TaskProbe.generated.h"

UCLASS()
class TASKPROBE_API UTaskProbe : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	virtual bool ShouldCreateSubsystem(UObject* Outer) const override;
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

private:
	enum class EScriptedKind : uint8
	{
		Key,
		Axis,
		Click,
		Cursor,
		Teleport
	};

	struct FScriptedKey
	{
		double Time = 0.0;
		EScriptedKind Kind = EScriptedKind::Key;
		FKey Key;
		bool bPress = true;
		double Axis = 0.0;
		FString Widget;
		FVector2D Cursor = FVector2D::ZeroVector;
		FVector Teleport = FVector::ZeroVector;
		bool bHasYaw = false;
		double Yaw = 0.0;
	};

	bool Tick(float DeltaTime);
	void Finish(const FString& Reason);
	void LoadInputs(const FString& Path);
	void SendInput(const FScriptedKey& K, UWorld* World, class APlayerController* PC);

	FTSTicker::FDelegateHandle TickHandle;
	FString OutDir;
	double Seconds = 20.0;
	double Every = 0.5;  // -TaskProbeEvery: the sample interval of the track, the camera and the measures
	int32 Shots = 4;
	int32 ShotsTaken = 0;
	double Elapsed = 0.0;
	double NextTrack = 0.0;
	int32 NextInput = 0;
	int32 InputsSent = 0;
	TArray<FScriptedKey> Inputs;
	TArray<TSharedPtr<class FJsonValue>> Track;
	TArray<TSharedPtr<class FJsonValue>> Camera;
	TArray<TSharedPtr<class FJsonValue>> ShotNames;
	TSharedPtr<class FTaskProbeQueries> Queries;  // only with -TaskProbeQueries
	bool bDone = false;
	bool bStarted = false;  // the first world has begun play: the clock runs from then on
	bool bCursorSet = false;
	FVector2D CursorAbsolute = FVector2D::ZeroVector;
};
