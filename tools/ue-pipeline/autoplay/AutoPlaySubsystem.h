// AutoPlay: command-line driven self-play. A bot drives the game through Enhanced Input while this subsystem
// handles the flags, the clock, per-run log files, audio capture, the start handshake, blocking hardware input and
// quitting when the run ends. A run plays one scenario: a defined start state plus a win/lose condition (a level, a
// chapter, a race stage or an open-world start setup). The game supplies StartScenario, ScenarioStarted and the bot.
//
// Module dependencies: "EnhancedInput", "AudioMixer", "Slate", "SlateCore", "InputCore".
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
namespace AutoPlay { class FAudioCapture; }

UCLASS()
class UAutoPlaySubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	static constexpr int32 ContractVersion = 4;

	static UAutoPlaySubsystem* Get(const UObject* WorldContextObject);

	// ---- Flags (valid from Initialize on) ----
	bool IsAutoPlay() const { return bEnabled; }
	int32 GetScenario() const { return Scenario; }
	const FString& GetScenarioName() const { return ScenarioName; }
	int32 GetLevel() const { return Scenario; } // deprecated (v1.2 name)
	int32 GetSeed() const { return Seed; }
	float GetSkill() const { return Skill; }
	const FString& GetOutputDir() const { return OutputDir; }
	const FString& GetRecordDir() const { return OutputDir; } // v1 name
	/** True between "go" and FinishRun: the only time the bot may inject. */
	bool IsRunning() const { return Phase == EPhase::Running; }

	// ---- Game hooks ----
	/** Required. Called once at "go" with the scenario number; set up that scenario (open its map, apply its start state). */
	TFunction<void(int32 /*Scenario*/)> StartScenario;
	/** Deprecated v1.2 hook, used only when StartScenario is not set. */
	TFunction<void(int32 /*Scenario*/)> StartLevel;
	/** Optional. Called when MaxSeconds has passed; must call FinishRun. Default: FinishRun("timeout", last SetScore). */
	TFunction<void()> OnTimeout;

	/** Call when the scenario's gameplay starts (map loaded, player has control or the countdown begins). Name: e.g. "First Night". */
	void ScenarioStarted(const FString& InScenarioName);
	/** Deprecated v1.2 name. */
	void LevelStarted(const FString& Name) { ScenarioStarted(Name); }
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
	int32 Scenario = 1;
	FString ScenarioName;
	int32 Seed = 0;
	float Skill = 1.f;
	double MaxSeconds = 600.0;
	double GoTimeout = 60.0;
	FString OutputDir;
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
	uint64 ScenarioStartQpc = 0;
	uint64 ScenarioEndQpc = 0;
	uint64 ScenarioStartFrame = 0;
	uint64 ScenarioEndFrame = 0;
	double Score = 0.0;
	FString Result;
	FString ResultExtra;
	int64 InjectCount = 0;

	TMap<const UInputAction*, FActiveInput> ActiveInputs;
	TSet<const UInputAction*> DescribedActions;
	bool bHasVirtualCursor = false;
	FVector2D VirtualCursor = FVector2D::ZeroVector;

	TMap<FString, IConsoleVariable*> CVarCache;
	// Master-submix capture (audio render thread). Never deleted: the audio thread may still call it after unregistering.
	AutoPlay::FAudioCapture* AudioCapture = nullptr;
	int64 LastAudioSize = -1;
	double AudioStableSince = 0.0;
};
