// The task checker's probe (game-factory tools/task_check): a timed run of the game for a task check's plays.
// Started with -TaskProbe -TaskProbeOut=<dir> [-TaskProbeSeconds=S] [-TaskProbeShots=N] [-TaskProbeInputs=<json file>]:
// N screenshots evenly over S seconds of game time, scripted key presses at their times, the player pawn's position
// and the player's camera (its location, rotation and field of view) every half second, then probe.json in <dir> and
// a clean exit. Without -TaskProbe it does nothing. -TaskProbeEvery=<0.1-1.0> sets the sample interval (default 0.5 s);
// the inputs file may also hold axis events, button clicks, cursor moves, wheel steps, mouse movement, pawn teleports
// (held there for a while when asked), real-time waits, named screenshots, map travels and view turns (LoadInputs):
// one launch can visit several places and scenarios and picture each; and the checker's stages of a contact: an actor
// pinned in front of the pawn, the engine's damage call, a reflected property written
// (docs/task-probes.md, section 1.3); and touches, as a phone's screen sends them (a tap, a long press, a drag,
// several fingers at once: docs/task-probes.md, section 1.5). An input that didn't land (a click no button took, a wheel
// step or a mouse movement no game viewport received, a stage nothing took) is listed in probe.json "inputs_missed", as
// is a named screenshot whose file wasn't written; "screenshots" lists only files written.
// -TaskProbeSound: the checker's play that measures audio, launched with sound (muted) and a fixed time step instead of
// -nosound and -benchmark; the application counts as focused throughout, as under -benchmark.
// With -TaskProbeQueries=<json file> (format game-probe-queries/1) it also evaluates the checker's queries on every half
// second sample and adds "measures" (and "query_errors" when a query could not be read) to probe.json; see
// Private/TaskProbeQueries.h and game-factory's docs/task-probes.md and docs/task-check.md.

#pragma once

#include "CoreMinimal.h"
#include "Containers/Ticker.h"
#include "Engine/EngineBaseTypes.h"
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
		Teleport,
		TeleportTo,
		Wait,
		Wheel,
		Move,
		Shot,
		Travel,
		View,
		Pin,
		Damage,
		Set,
		Touch
	};

	/** A place a touch names: a viewport point in fractions 0-1, or the centre of a widget by its name. */
	struct FTouchSpot
	{
		bool bWidget = false;
		FString Widget;
		FVector2D At = FVector2D::ZeroVector;
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
		TSharedPtr<class FJsonObject> Target;  // teleport_to: the actor select whose nearest match the pawn goes next to
		TSharedPtr<class FJsonObject> Face;  // teleport_to: the point it faces (default the target)
		double Distance = 200.0;  // teleport_to: cm from the target, on the pawn's side
		FVector Offset = FVector::ZeroVector;  // teleport_to: added to that place (cm)
		double Hold = 0.0;  // teleport, teleport_to: seconds of play the pawn is held at the spot (put back after every world tick)
		double Wait = 0.0;  // wait: seconds of real time the play's clock holds while the game runs on, paced to real time
		int32 Wheel = 0;  // wheel: notches, positive away from the player (scroll up)
		FVector2D Move = FVector2D::ZeroVector;  // move: pixels right and down
		double Over = 0.0;  // move: seconds it is spread over (0: one event)
		FString Shot;  // shot: the screenshot's name (shot_<name>.png)
		FString Map;  // travel: the map and URL options the play opens
		FRotator View = FRotator::ZeroRotator;  // view: the control rotation (pitch, yaw) the player's view turns to
		bool bFront = false;  // pin: set ahead of the pawn first
		double Front = 0.0;  // pin: cm ahead of the pawn
		TSharedPtr<class FJsonObject> At;  // pin: the point it is set at first (instead of ahead of the pawn)
		double Amount = 0.0;  // damage: points dealt
		TSharedPtr<class FJsonObject> From;  // damage: the select of what strikes (default: the pawn, or the nearest other pawn)
		FString Path;  // set: the property path
		TSharedPtr<class FJsonValue> Value;  // set: the value written
		bool bAll = false;  // set: on every match, not only the nearest
		TArray<FTouchSpot> Spots;  // tap, drag: where the finger goes down, then each place it moves through
		bool bDrag = false;  // drag (a tap otherwise): what a miss is listed as
		int32 Finger = 0;  // tap, drag: the touch index, 0-9 (several fingers at once by their numbers)
		double Press = 0.0;  // tap: seconds the finger stays down; drag: seconds it stays at the last place before it lifts
		bool bScrolled = false;  // click: made again after its scroll areas were scrolled to its control (no second scroll)
		int32 TextFrames = -1;  // click: frames it has waited for the screen's texts (-1: not looked for by its text yet)
		TSharedPtr<class FJsonObject> When;  // shot: its event, as the grader hands it ({query, field, of, match, op, value, within})
	};

	/** A shot waiting for its event (a `shot` input's `when`): read every frame from its time on. */
	struct FWatch
	{
		int32 Input = 0;  // its index in Inputs
		double Start = 0.0;  // play time it began waiting
	};

	/** A finger on the screen: sent a part each tick until it lifts. */
	struct FTouching
	{
		int32 Input = 0;  // its index in Inputs
		double Start = 0.0;  // play time it went down
		TArray<FVector2D> Points;  // its path in Slate's absolute space, resolved when it went down
		FVector2D Last = FVector2D::ZeroVector;  // where it is
		bool bDown = false;
		bool bMissed = false;  // a move Slate didn't take (listed once)
		bool bFinished = false;  // lifted
	};

	/** An actor a pin holds: where, until when (play time). */
	struct FPinned
	{
		TWeakObjectPtr<class AActor> Actor;
		FVector At = FVector::ZeroVector;
		double Until = 0.0;
	};

	/** A mouse movement under way: sent a part each tick until all of it is. */
	struct FMoving
	{
		int32 Input = 0;  // its index in Inputs
		double Start = 0.0;  // play time it began
		FVector2D Sent = FVector2D::ZeroVector;  // pixels sent so far
		bool bMissed = false;  // a part of it didn't reach the game as mouse axes (listed once)
		bool bFinished = false;  // all of it sent
	};

	/** A screenshot asked for, an evenly spaced one or a `shot` input's (AskShot). */
	struct FShotAsked
	{
		FString File;  // shot_NN.png or shot_<name>.png
		FString Source;  // the capture it is: File, or the file of the frame's capture it is a copy of
		int32 Input = INDEX_NONE;  // a `shot` input's index in Inputs; INDEX_NONE for an evenly spaced one
		double At = 0.0;  // the play time it was asked for at
	};

	bool Tick(float DeltaTime);
	void Finish(const FString& Reason);
	void LoadInputs(const FString& Path);
	void SendInput(const FScriptedKey& K, UWorld* World, class APlayerController* PC);
	void HoldInPlace(UWorld* World, ELevelTick TickType, float DeltaSeconds);
	void Stage(const FScriptedKey& K, UWorld* World, class APlayerController* PC);
	void PinActor(const FScriptedKey& K, UWorld* World, class APlayerController* PC);
	bool ClickSlate(const FScriptedKey& K);
	/** A click no button takes, made on its text as shown (game grader 1.18.0): true when it is done with (pressed,
	 *  missed, or made again next frame while the screen's texts are read). */
	bool ClickText(const FScriptedKey& K, class APlayerController* PC);
	/** The pointer moved to a viewport point (fractions) as a cursor input moves it: Slate's and the player's mouse. */
	bool MoveCursor(double Fx, double Fy, class APlayerController* PC, FVector2D& OutAbsolute);
	/** A click's control scrolled into its scroll areas' view, or found covered: true when the click is done with
	 *  (made again next frame, or listed as a miss); false: press it now. */
	bool ScrolledOrCovered(const FScriptedKey& K, const TSharedPtr<class SWidget>& Control, const FString& Label);
	/** The shots waiting for their event: each taken in the first frame it holds, or a miss once it can't come. */
	void Watch(UWorld* World, class APlayerController* PC, bool bEnded);
	void SendWheel(const FScriptedKey& K);
	void MoveMouse(FMoving& M);
	void StartTouch(const FScriptedKey& K, UWorld* World);
	void MoveTouch(FTouching& T);
	void LiftTouches();
	void Missed(const FScriptedKey& K, const TCHAR* Kind, const FString& Target, const FString& Why);
	void AskShot(const FString& File, int32 Input);
	void ShotTaken();
	bool NamedShotWaiting() const;
	bool ShotsWritten() const;
	bool ShotWritten(const FString& File) const;

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
	TArray<FShotAsked> ShotsAsked;  // every screenshot asked for, in order
	FString ShotFrame;  // the file of the capture the engine hasn't taken yet (empty: none pending)
	bool bEnding = false;  // the play's time is up: it waits (ShotsWaitStart) for the screenshots asked for to be on disk
	double ShotsWaitStart = 0.0;  // the real time that wait began
	TArray<TSharedPtr<class FJsonValue>> InputsMissed;  // probe.json "inputs_missed": [{t, kind, target, why}]
	TArray<FMoving> Moving;  // mouse movements under way
	TArray<FTouching> Touching;  // fingers on the screen
	TArray<FScriptedKey> Again;  // clicks made again next frame, their control scrolled into view (the inputs after them wait)
	TArray<FWatch> Watches;  // shots waiting for their event
	TSharedPtr<class FTaskProbeQueries> Watcher;  // reads a shot's event (only with a shot that names one)
	TSharedPtr<class FTaskProbeQueries> Texts;  // reads the texts on screen for a click by its text (only with a click)
	TSharedPtr<class FTaskProbeQueries> Queries;  // only with -TaskProbeQueries
	bool bDone = false;
	bool bStarted = false;  // the first world has begun play: the clock runs from then on
	bool bCursorSet = false;
	int32 FramesWaited = 0;  // at the end, frames waited for a screen sample's frame
	FVector2D CursorAbsolute = FVector2D::ZeroVector;
	FDelegateHandle HoldHandle;  // only with an input that holds the pawn or pins an actor
	TArray<FPinned> Pinned;  // the actors pins hold
	FVector HoldAt = FVector::ZeroVector;  // where the pawn is held
	double HoldUntil = -1.0;  // play time the hold ends at (none before any hold)
	bool bWaiting = false;  // a wait input holds the play's clock
	double WaitFor = 0.0;  // its seconds
	double WaitGame = 0.0;  // game time passed in it
	double WaitStart = 0.0;  // the real time (FPlatformTime::Seconds) it began
};
