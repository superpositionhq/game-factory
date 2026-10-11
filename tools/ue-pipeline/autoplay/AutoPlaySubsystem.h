// AutoPlay recorder for the Track B games: implements docs/autoplay-contract.md (contract v1).
//
// Copy AutoPlaySubsystem.h / AutoPlaySubsystem.cpp unchanged into Source/<Module>/AutoPlay/ and add
// "EnhancedInput", "AudioMixer", "Slate", "SlateCore", "InputCore" to the module's dependency list.
// The game supplies StartLevel (and its bot); everything else (flags, clock, files, audio, go handshake,
// hardware-input blocking, quitting) lives here so the four games behave the same way.
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "InputActionValue.h"
#include "Containers/Ticker.h"
#include "Engine/EngineBaseTypes.h"
#include "AutoPlaySubsystem.generated.h"

class APlayerController;
class UInputAction;
class IInputProcessor;
class IConsoleVariable;
class UWorld;

UCLASS()
class UAutoPlaySubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	static constexpr int32 ContractVersion = 1;

	static UAutoPlaySubsystem* Get(const UObject* WorldContextObject);

	// ---- Flags (valid from Initialize on) ----
	bool IsAutoPlay() const { return bEnabled; }
	int32 GetLevel() const { return Level; }
	int32 GetSeed() const { return Seed; }
	float GetSkill() const { return Skill; }
	const FString& GetRecordDir() const { return RecordDir; }
	/** True between "go" and FinishRun: the only time the bot may inject. */
	bool IsRunning() const { return Phase == EPhase::Running; }

	// ---- Game hooks ----
	/** Required. Called once at "go"; open the level (OpenLevel or the game's own loader). */
	TFunction<void(int32 /*Level*/)> StartLevel;
	/** Optional. Called when MaxSeconds has passed; must call FinishRun. Default: FinishRun("timeout", last SetScore). */
	TFunction<void()> OnTimeout;

	/** Call when the level's gameplay starts (map loaded, player has control or the countdown begins). */
	void LevelStarted(const FString& LevelName);
	/** Keep the score current (used when the run times out). */
	void SetScore(double InScore) { Score = InScore; }
	/** End the run. Result: win | lose | timeout | abort. ExtraJson: JSON members without braces, e.g. "\"stars\":2". */
	void FinishRun(const FString& Result, double FinalScore, const FString& ExtraJson = FString());
	/** One telemetry row. FieldsJson: JSON members without braces (use the Json* helpers), or empty. */
	void Telemetry(const FString& Event, const FString& FieldsJson = FString());

	// ---- Bot API: the only way the bot acts ----
	/**
	 * Inject one frame of input for Action through Enhanced Input and log it. Call every frame while the input is held;
	 * not calling it in a frame releases it. Value is what the key mapping would produce (after mapping modifiers).
	 * Key names the key/axis the input stands for: "W", "W+D", "SpaceBar", "LeftMouseButton", "Mouse2D", "MouseWheelAxis".
	 */
	void Inject(APlayerController* PC, const UInputAction* Action, FInputActionValue Value, const FString& Key = FString());
	/** Move the virtual cursor (viewport pixels). Logged as a cursor row. */
	void SetVirtualCursor(const FVector2D& ViewportPos);
	/** Virtual cursor in AutoPlay, real mouse position otherwise. Use it wherever the game picks with the cursor. */
	bool GetCursorPosition(const APlayerController* PC, FVector2D& OutViewportPos) const;

	// ---- Clock: QPC on Windows ----
	static uint64 Qpc();
	static uint64 QpcFrequency();
	static uint64 QpcToNs(uint64 InQpc);

	// ---- JSON helpers for FieldsJson / ExtraJson ----
	static FString JsonStr(const FString& S);
	static FString JsonNum(double V);
	static FString JsonVec(const FVector& V);

	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

private:
	enum class EPhase : uint8 { Off, Boot, WaitingForGo, Running, Holding, Exporting, Done };

	struct FActiveInput
	{
		uint64 LastFrame = 0;
		FString Key;
		EInputActionValueType Type = EInputActionValueType::Boolean;
		FString Name;
	};

	bool CoreTick(float DeltaTime);
	void OnPostActorTick(UWorld* World, ELevelTick TickType, float DeltaSeconds);
	void EnforceWindowAndInput();
	void BeginRun(bool bGoTimedOut);
	void StartExport();
	void FinalizeAndQuit(bool bAudioOk);
	UWorld* GetGameWorld() const;
	FString Stamp() const;
	FString ClockSample(const TCHAR* Label) const;
	FString HeaderFields() const;
	void WriteLine(FArchive* Ar, const FString& Line);
	void WriteTextFile(const TCHAR* Name, const FString& Text) const;
	void SetCVar(const TCHAR* Name, const TCHAR* Value);

	bool bEnabled = false;
	bool bAllowHardwareInput = false;
	int32 Level = 1;
	int32 Seed = 0;
	float Skill = 1.f;
	double MaxSeconds = 600.0;
	double GoTimeout = 60.0;
	FString RecordDir;
	FString BuildCommit;
	FString RunId;

	EPhase Phase = EPhase::Off;
	bool bSettingsApplied = false;
	double ReadyAt = 0.0;
	double PhaseDeadline = 0.0;
	double NextGoPoll = 0.0;
	double LastFlush = 0.0;
	bool bGoTimedOut = false;

	TUniquePtr<FArchive> InputsAr;
	TUniquePtr<FArchive> TelemetryAr;
	TSharedPtr<IInputProcessor> InputBlocker;
	FTSTicker::FDelegateHandle TickHandle;
	FDelegateHandle PostTickHandle;
	TArray<FString> ClockSamples;

	uint64 GoQpc = 0;
	uint64 GoFrame = 0;
	uint64 LevelStartQpc = 0;
	uint64 LevelEndQpc = 0;
	uint64 LevelStartFrame = 0;
	uint64 LevelEndFrame = 0;
	double Score = 0.0;
	FString LevelName;
	FString Result;
	FString ResultExtra;
	int64 InjectCount = 0;

	TMap<const UInputAction*, FActiveInput> ActiveInputs;
	TSet<const UInputAction*> DescribedActions;
	bool bHasVirtualCursor = false;
	FVector2D VirtualCursor = FVector2D::ZeroVector;

	TMap<FString, IConsoleVariable*> CVarCache;
	int64 LastAudioSize = -1;
	double AudioStableSince = 0.0;
};
