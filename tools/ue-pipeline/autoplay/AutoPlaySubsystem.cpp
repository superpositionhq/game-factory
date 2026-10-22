// AutoPlay: see AutoPlaySubsystem.h.
#include "AutoPlaySubsystem.h"

#include "AudioDevice.h"
#include "ISubmixBufferListener.h"
#include "EnhancedInputSubsystems.h"
#include "InputAction.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "Framework/Application/IInputProcessor.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/GameUserSettings.h"
#include "GameFramework/PlayerController.h"
#include "Scalability.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "HAL/PlatformMisc.h"
#include "HAL/PlatformProcess.h"
#include "HAL/PlatformTime.h"
#include "Misc/App.h"
#include "Misc/CommandLine.h"
#include "Misc/EngineVersion.h"
#include "Runtime/Launch/Resources/Version.h"

// UE 5.4+ registers submix buffer listeners by TSharedRef (ISubmixBufferListener is TSharedFromThis there); the old
// raw-pointer overloads assert on 5.7. UE 5.3 has only the raw-pointer ones.
#define AUTOPLAY_SHARED_SUBMIX_LISTENER (ENGINE_MAJOR_VERSION > 5 || (ENGINE_MAJOR_VERSION == 5 && ENGINE_MINOR_VERSION >= 4))
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "UnrealClient.h"
#include "Widgets/SWindow.h"
#include <thread>
#if PLATFORM_WINDOWS
#include "Windows/WindowsHWrapper.h"
#endif

namespace AutoPlay
{
	/** Swallows every hardware key, mouse and gamepad event so only injected input reaches the game. */
	class FInputBlocker : public IInputProcessor
	{
	public:
		virtual void Tick(const float, FSlateApplication&, TSharedRef<ICursor>) override {}
		virtual bool HandleKeyDownEvent(FSlateApplication&, const FKeyEvent&) override { return true; }
		virtual bool HandleKeyUpEvent(FSlateApplication&, const FKeyEvent&) override { return true; }
		virtual bool HandleAnalogInputEvent(FSlateApplication&, const FAnalogInputEvent&) override { return true; }
		virtual bool HandleMouseMoveEvent(FSlateApplication&, const FPointerEvent&) override { return true; }
		virtual bool HandleMouseButtonDownEvent(FSlateApplication&, const FPointerEvent&) override { return true; }
		virtual bool HandleMouseButtonUpEvent(FSlateApplication&, const FPointerEvent&) override { return true; }
		virtual bool HandleMouseButtonDoubleClickEvent(FSlateApplication&, const FPointerEvent&) override { return true; }
		virtual bool HandleMouseWheelOrGestureEvent(FSlateApplication&, const FPointerEvent&, const FPointerEvent*) override { return true; }
		virtual const TCHAR* GetDebugName() const override { return TEXT("AutoPlayInputBlocker"); }
	};

	static const TCHAR* ValueTypeName(EInputActionValueType Type)
	{
		switch (Type)
		{
		case EInputActionValueType::Boolean: return TEXT("Boolean");
		case EInputActionValueType::Axis1D: return TEXT("Axis1D");
		case EInputActionValueType::Axis2D: return TEXT("Axis2D");
		default: return TEXT("Axis3D");
		}
	}

	static FString ValueJson(const FInputActionValue& Value)
	{
		switch (Value.GetValueType())
		{
		case EInputActionValueType::Boolean:
			return Value.Get<bool>() ? TEXT("true") : TEXT("false");
		case EInputActionValueType::Axis1D:
			return UAutoPlaySubsystem::JsonNum(Value.Get<float>());
		case EInputActionValueType::Axis2D:
		{
			const FVector2D V = Value.Get<FVector2D>();
			return FString::Printf(TEXT("[%s,%s]"), *UAutoPlaySubsystem::JsonNum(V.X), *UAutoPlaySubsystem::JsonNum(V.Y));
		}
		default:
			return UAutoPlaySubsystem::JsonVec(Value.Get<FVector>());
		}
	}

	static FString ZeroJson(EInputActionValueType Type)
	{
		switch (Type)
		{
		case EInputActionValueType::Boolean: return TEXT("false");
		case EInputActionValueType::Axis1D: return TEXT("0");
		case EInputActionValueType::Axis2D: return TEXT("[0,0]");
		default: return TEXT("[0,0,0]");
		}
	}

	/**
	 * Master-submix capture. OnNewSubmixBuffer runs on the audio render thread: it converts the buffer to int16 and
	 * timestamps it with QPC. If a buffer arrives later than wall time allows (the renderer stalled, e.g. on a busy
	 * machine), silence is inserted first, so WAV position == time since the first buffer (within ~2 buffers).
	 * The game thread writes audio.wav and audio_clock.jsonl (one row per buffer: frame index -> QPC) in Flush().
	 */
	class FAudioCapture : public ISubmixBufferListener
	{
	public:
		bool Open(const FString& WavPath, const FString& ClockPath)
		{
			Wav.Reset(IFileManager::Get().CreateFileWriter(*WavPath));
			Clock.Reset(IFileManager::Get().CreateFileWriter(*ClockPath));
			if (!Wav || !Clock) { return false; }
			uint8 Placeholder[44] = {};
			Wav->Serialize(Placeholder, sizeof(Placeholder)); // header written in Close() once the format is known
			return true;
		}

		void Start() { FScopeLock L(&Lock); bActive = true; }

		virtual void OnNewSubmixBuffer(const USoundSubmix*, float* AudioData, int32 NumSamples, int32 NumChannels, const int32 SampleRate, double AudioClock) override
		{
			const uint64 Now = UAutoPlaySubsystem::Qpc();
			FScopeLock L(&Lock);
			if (!bActive || !AudioData || NumChannels <= 0 || SampleRate <= 0 || NumSamples <= 0) { return; }
			const int32 Frames = NumSamples / NumChannels;
			const double Freq = (double)UAutoPlaySubsystem::QpcFrequency();
			if (OutChannels == 0)
			{
				OutChannels = NumChannels;
				OutRate = SampleRate;
				StartQpc = Now - (uint64)((double)Frames / OutRate * Freq); // frame 0 = start of the first buffer
			}
			// Where this buffer should end on the wall clock vs where the WAV would put it.
			const int64 ExpectedEnd = (int64)((double)(Now - StartQpc) / Freq * OutRate);
			const int64 Late = ExpectedEnd - (Written + Frames);
			const int64 Tolerance = FMath::Max<int64>(2048, 2 * Frames);
			int64 Silence = 0;
			if (Late > Tolerance)
			{
				Silence = Late;
				Pending.AddZeroed((int32)(Silence * OutChannels));
				Written += Silence; SilenceFrames += Silence; ++Gaps;
			}
			const uint64 BufferStartQpc = Now - (uint64)((double)Frames / OutRate * Freq);
			Rows.Add(FString::Printf(TEXT("{\"frame\":%lld,\"frames\":%d,\"qpc\":%llu,\"t_ns\":%llu,\"silence_before\":%lld,\"audio_clock\":%s,\"channels\":%d,\"rate\":%d}"),
				Written, Frames, BufferStartQpc, UAutoPlaySubsystem::QpcToNs(BufferStartQpc), Silence, *UAutoPlaySubsystem::JsonNum(AudioClock), NumChannels, SampleRate));
			const int32 Base = Pending.AddUninitialized(Frames * OutChannels);
			for (int32 F = 0; F < Frames; ++F)
			{
				for (int32 C = 0; C < OutChannels; ++C)
				{
					// Channel count can change on an output-device swap: map to the first layout.
					const float S = AudioData[F * NumChannels + FMath::Min(C, NumChannels - 1)];
					Pending[Base + F * OutChannels + C] = (int16)FMath::Clamp(FMath::RoundToInt(S * 32767.f), -32768, 32767);
				}
			}
			Written += Frames;
		}

		virtual bool IsRenderingAudio() const override { return true; }

		/** Game thread: write what the audio thread produced. */
		void Flush()
		{
			TArray<int16> Samples; TArray<FString> NewRows;
			{
				FScopeLock L(&Lock);
				Swap(Samples, Pending); Swap(NewRows, Rows);
			}
			if (Wav && Samples.Num()) { Wav->Serialize(Samples.GetData(), Samples.Num() * sizeof(int16)); DataBytes += Samples.Num() * sizeof(int16); }
			if (Clock)
			{
				for (const FString& Row : NewRows)
				{
					FTCHARToUTF8 Utf8(*Row);
					Clock->Serialize((void*)Utf8.Get(), Utf8.Length());
					char NewLine = '\n';
					Clock->Serialize(&NewLine, 1);
				}
			}
		}

		/** Game thread: stop accepting buffers, write the rest, patch the WAV header, close both files. */
		void Close()
		{
			{ FScopeLock L(&Lock); bActive = false; }
			Flush();
			if (Wav)
			{
				const int32 Channels = OutChannels > 0 ? OutChannels : 2;
				const int32 Rate = OutRate > 0 ? OutRate : 48000;
				uint8 H[44];
				auto Put32 = [&H](int32 At, uint32 V) { H[At] = V & 0xFF; H[At + 1] = (V >> 8) & 0xFF; H[At + 2] = (V >> 16) & 0xFF; H[At + 3] = (V >> 24) & 0xFF; };
				auto Put16 = [&H](int32 At, uint16 V) { H[At] = V & 0xFF; H[At + 1] = (V >> 8) & 0xFF; };
				FMemory::Memcpy(H + 0, "RIFF", 4); Put32(4, (uint32)(36 + DataBytes)); FMemory::Memcpy(H + 8, "WAVE", 4);
				FMemory::Memcpy(H + 12, "fmt ", 4); Put32(16, 16); Put16(20, 1); Put16(22, (uint16)Channels); Put32(24, (uint32)Rate);
				Put32(28, (uint32)(Rate * Channels * 2)); Put16(32, (uint16)(Channels * 2)); Put16(34, 16);
				FMemory::Memcpy(H + 36, "data", 4); Put32(40, (uint32)DataBytes);
				Wav->Seek(0);
				Wav->Serialize(H, sizeof(H));
				Wav->Close();
				Wav.Reset();
			}
			if (Clock) { Clock->Close(); Clock.Reset(); }
		}

		int64 GetWrittenFrames() const { FScopeLock L(&Lock); return Written; }
		int64 GetSilenceFrames() const { FScopeLock L(&Lock); return SilenceFrames; }
		int32 GetGaps() const { FScopeLock L(&Lock); return Gaps; }

	private:
		mutable FCriticalSection Lock;
		bool bActive = false;
		int32 OutChannels = 0;
		int32 OutRate = 0;
		uint64 StartQpc = 0;
		int64 Written = 0;
		int64 SilenceFrames = 0;
		int32 Gaps = 0;
		int64 DataBytes = 0;
		TArray<int16> Pending;
		TArray<FString> Rows;
		TUniquePtr<FArchive> Wav;
		TUniquePtr<FArchive> Clock;
	};
}

// Stop the master-submix capture: by shared reference on UE 5.4+, by pointer on 5.3 (AUTOPLAY_SHARED_SUBMIX_LISTENER).
static void AutoPlayUnregisterCapture(FAudioDevice* AudioDevice, AutoPlay::FAudioCapture* Raw,
	const TSharedPtr<AutoPlay::FAudioCapture, ESPMode::ThreadSafe>& Ref)
{
#if AUTOPLAY_SHARED_SUBMIX_LISTENER
	if (Ref.IsValid()) { AudioDevice->UnregisterSubmixBufferListener(Ref.ToSharedRef(), AudioDevice->GetMainSubmixObject()); }
#else
	if (Raw) { AudioDevice->UnregisterSubmixBufferListener(Raw, nullptr); }
#endif
}

namespace AutoPlay
{
	/**
	 * Exit watchdog: ends the process when it is still alive past a deadline, so a hang in gameplay or in engine
	 * shutdown after run_end cannot hold the GPU until the caller's own timeout. A detached thread, independent of the
	 * game thread and of engine shutdown: at the deadline it writes watchdog.json (prepared when armed, so nothing is
	 * formatted or allocated then) and terminates the process with exit code 124. Deadlines only ever move earlier.
	 */
	class FExitWatchdog
	{
	public:
		static constexpr uint32 ExitCode = 124;

		static void Arm(double DeadlineSeconds, const TCHAR* Reason, const FString& NoteFile)
		{
			FState& S = State();
			FScopeLock L(&S.Lock);
			if (S.Deadline > 0.0 && S.Deadline <= DeadlineSeconds) { return; }
			S.Deadline = DeadlineSeconds;
			S.NoteFile = NoteFile;
			const FString Note = FString::Printf(TEXT("{\"schema\":\"autoplay-watchdog/1\",\"reason\":\"%s\",\"armed_t_ns\":%llu,\"after_s\":%s,\"exit_code\":%u}\n"),
				Reason, UAutoPlaySubsystem::QpcToNs(UAutoPlaySubsystem::Qpc()), *UAutoPlaySubsystem::JsonNum(DeadlineSeconds - FPlatformTime::Seconds()), ExitCode);
			const FTCHARToUTF8 Utf8(*Note);
			S.Note.Reset();
			S.Note.Append((const uint8*)Utf8.Get(), Utf8.Length());
			if (!S.bStarted) { S.bStarted = true; std::thread(&FExitWatchdog::Loop).detach(); }
		}

		static void Disarm() { FState& S = State(); FScopeLock L(&S.Lock); S.Deadline = 0.0; }

	private:
		struct FState
		{
			FCriticalSection Lock;
			double Deadline = 0.0;
			FString NoteFile;
			TArray<uint8> Note;
			bool bStarted = false;
		};
		static FState& State() { static FState* S = new FState(); return *S; } // never destroyed: the thread outlives statics

		static void Loop()
		{
			for (;;)
			{
				FPlatformProcess::Sleep(1.0f);
				FState& S = State();
				FScopeLock L(&S.Lock);
				if (S.Deadline <= 0.0 || FPlatformTime::Seconds() < S.Deadline) { continue; }
#if PLATFORM_WINDOWS
				HANDLE File = ::CreateFileW(*S.NoteFile, GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
				if (File != INVALID_HANDLE_VALUE) { DWORD Done = 0; ::WriteFile(File, S.Note.GetData(), (DWORD)S.Note.Num(), &Done, nullptr); ::CloseHandle(File); }
				::TerminateProcess(::GetCurrentProcess(), ExitCode);
#else
				FFileHelper::SaveArrayToFile(S.Note, *S.NoteFile);
				FPlatformMisc::RequestExitWithStatus(true, (uint8)ExitCode);
#endif
			}
		}
	};
}

// ---------------------------------------------------------------------------------------------------------------------
// Clock and JSON helpers

uint64 UAutoPlaySubsystem::Qpc()
{
	return FPlatformTime::Cycles64(); // QueryPerformanceCounter on Windows
}

uint64 UAutoPlaySubsystem::QpcFrequency()
{
	static const uint64 Frequency = (uint64)FMath::RoundToDouble(1.0 / FPlatformTime::GetSecondsPerCycle64());
	return Frequency;
}

uint64 UAutoPlaySubsystem::QpcToNs(uint64 InQpc)
{
	const uint64 F = QpcFrequency();
	return (InQpc / F) * 1000000000ull + (InQpc % F) * 1000000000ull / F;
}

FString UAutoPlaySubsystem::JsonStr(const FString& S)
{
	FString Out;
	Out.Reserve(S.Len() + 2);
	Out.AppendChar(TEXT('"'));
	for (const TCHAR C : S)
	{
		switch (C)
		{
		case TEXT('"'): Out += TEXT("\\\""); break;
		case TEXT('\\'): Out += TEXT("\\\\"); break;
		case TEXT('\n'): Out += TEXT("\\n"); break;
		case TEXT('\r'): Out += TEXT("\\r"); break;
		case TEXT('\t'): Out += TEXT("\\t"); break;
		default:
			if (C < 0x20) { Out += FString::Printf(TEXT("\\u%04x"), (int32)C); }
			else { Out.AppendChar(C); }
		}
	}
	Out.AppendChar(TEXT('"'));
	return Out;
}

FString UAutoPlaySubsystem::JsonNum(double V)
{
	if (!FMath::IsFinite(V)) { return TEXT("null"); }
	return FString::Printf(TEXT("%.9g"), V);
}

FString UAutoPlaySubsystem::JsonVec(const FVector& V)
{
	return FString::Printf(TEXT("[%s,%s,%s]"), *JsonNum(V.X), *JsonNum(V.Y), *JsonNum(V.Z));
}

FString UAutoPlaySubsystem::Stamp() const
{
	const uint64 Q = Qpc();
	return FString::Printf(TEXT("\"t_ns\":%llu,\"qpc\":%llu,\"frame\":%llu"), QpcToNs(Q), Q, (uint64)GFrameCounter);
}

FString UAutoPlaySubsystem::ClockSample(const TCHAR* Label) const
{
	const uint64 Q0 = Qpc();
	const FDateTime Utc = FDateTime::UtcNow();
	const uint64 Q1 = Qpc();
	const int64 UnixNs = (Utc - FDateTime(1970, 1, 1)).GetTicks() * 100;
	return FString::Printf(TEXT("{\"label\":%s,\"qpc\":%llu,\"qpc_after\":%llu,\"t_ns\":%llu,\"unix_ns\":%lld,\"utc\":%s,\"frame\":%llu}"),
		*JsonStr(Label), Q0, Q1, QpcToNs(Q0), UnixNs, *JsonStr(Utc.ToIso8601()), (uint64)GFrameCounter);
}

FString UAutoPlaySubsystem::HeaderFields() const
{
	return FString::Printf(TEXT("\"autoplay_version\":%d,\"game\":%s,\"run_id\":%s,\"scenario\":%d,\"scenario_name\":%s,\"seed\":%d,\"skill\":%s,\"max_seconds\":%s,\"qpc_frequency\":%llu,\"build_commit\":%s"),
		ContractVersion, *JsonStr(FApp::GetProjectName()), *JsonStr(RunId), Scenario, *JsonStr(ScenarioName), Seed, *JsonNum(Skill), *JsonNum(MaxSeconds),
		QpcFrequency(), *JsonStr(BuildCommit));
}

void UAutoPlaySubsystem::WriteLine(FArchive* Ar, const FString& Line)
{
	if (!Ar) { return; }
	FTCHARToUTF8 Utf8(*Line);
	Ar->Serialize((void*)Utf8.Get(), Utf8.Length());
	char NewLine = '\n';
	Ar->Serialize(&NewLine, 1);
}

void UAutoPlaySubsystem::WriteTextFile(const TCHAR* Name, const FString& Text) const
{
	FFileHelper::SaveStringToFile(Text, *(OutputDir / Name), FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
}

void UAutoPlaySubsystem::SetCVar(const TCHAR* Name, const TCHAR* Value)
{
	IConsoleVariable*& Cached = CVarCache.FindOrAdd(Name);
	if (!Cached) { Cached = IConsoleManager::Get().FindConsoleVariable(Name); }
	if (IConsoleVariable* CVar = Cached)
	{
		if (!FMath::IsNearlyEqual(CVar->GetFloat(), FCString::Atof(Value)))
		{
			CVar->Set(Value, ECVF_SetByCode);
		}
	}
}

// ---------------------------------------------------------------------------------------------------------------------
// Lifecycle

UAutoPlaySubsystem* UAutoPlaySubsystem::Get(const UObject* WorldContextObject)
{
	const UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(WorldContextObject, EGetWorldErrorMode::ReturnNull) : nullptr;
	const UGameInstance* GI = World ? World->GetGameInstance() : nullptr;
	return GI ? GI->GetSubsystem<UAutoPlaySubsystem>() : nullptr;
}

UWorld* UAutoPlaySubsystem::GetGameWorld() const
{
	const UGameInstance* GI = GetGameInstance();
	return GI ? GI->GetWorld() : nullptr;
}

void UAutoPlaySubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);

	const TCHAR* Cmd = FCommandLine::Get();
	bEnabled = !GIsEditor && FParse::Param(Cmd, TEXT("AutoPlay"));
	if (!bEnabled)
	{
		return;
	}

	if (!FParse::Value(Cmd, TEXT("Scenario="), Scenario))
	{
		FParse::Value(Cmd, TEXT("Level="), Scenario); // v1.2 name, still accepted
	}
	FParse::Value(Cmd, TEXT("ScenarioName="), ScenarioName); // optional; ScenarioStarted() sets it otherwise
	FParse::Value(Cmd, TEXT("Seed="), Seed);
	FParse::Value(Cmd, TEXT("Skill="), Skill);
	Skill = FMath::Clamp(Skill, 0.f, 1.f);
	float Seconds = 0.f;
	if (FParse::Value(Cmd, TEXT("MaxSeconds="), Seconds)) { MaxSeconds = Seconds; }
	if (FParse::Value(Cmd, TEXT("GoTimeout="), Seconds)) { GoTimeout = Seconds; }
	if (FParse::Value(Cmd, TEXT("AutoPlayWatchdog="), Seconds)) { WatchdogSeconds = Seconds; }
	if (!FParse::Value(Cmd, TEXT("OutputDir="), OutputDir))
	{
		FParse::Value(Cmd, TEXT("RecordDir="), OutputDir); // v1 name, still accepted
	}
	FParse::Value(Cmd, TEXT("BuildCommit="), BuildCommit);
	FParse::Value(Cmd, TEXT("RunId="), RunId);
	bAllowHardwareInput = FParse::Param(Cmd, TEXT("AutoPlayAllowInput"));

	if (OutputDir.IsEmpty())
	{
		OutputDir = FPaths::ProjectSavedDir() / TEXT("AutoPlay") / FDateTime::Now().ToString(TEXT("%Y%m%d-%H%M%S"));
	}
	OutputDir = FPaths::ConvertRelativePathToFull(OutputDir);
	IFileManager::Get().MakeDirectory(*OutputDir, true);

	InputsAr.Reset(IFileManager::Get().CreateFileWriter(*(OutputDir / TEXT("inputs.jsonl"))));
	TelemetryAr.Reset(IFileManager::Get().CreateFileWriter(*(OutputDir / TEXT("telemetry.jsonl"))));
	WriteLine(InputsAr.Get(), FString::Printf(TEXT("{%s,\"type\":\"header\",\"schema\":\"autoplay-inputs/2\",%s}"), *Stamp(), *HeaderFields()));
	WriteLine(TelemetryAr.Get(), FString::Printf(TEXT("{%s,\"event\":\"header\",\"schema\":\"autoplay-telemetry/2\",%s}"), *Stamp(), *HeaderFields()));
	ClockSamples.Add(ClockSample(TEXT("start")));

	FMath::RandInit(Seed);
	FMath::SRandInit(Seed);

	Phase = EPhase::Boot;
	TickHandle = FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateUObject(this, &UAutoPlaySubsystem::CoreTick));
	PostTickHandle = FWorldDelegates::OnWorldPostActorTick.AddUObject(this, &UAutoPlaySubsystem::OnPostActorTick);
	UE_LOG(LogTemp, Display, TEXT("AutoPlay: scenario %d seed %d skill %.2f max %.0fs dir %s"), Scenario, Seed, Skill, MaxSeconds, *OutputDir);
}

void UAutoPlaySubsystem::Deinitialize()
{
	if (bEnabled)
	{
		// Engine shutdown: the process must be gone soon (a hang here would hold the GPU); otherwise stand down.
		if (IsEngineExitRequested() && WatchdogSeconds > 0.0) { AutoPlay::FExitWatchdog::Arm(FPlatformTime::Seconds() + ShutdownWatchdogSeconds, TEXT("shutdown"), OutputDir / TEXT("watchdog.json")); }
		else if (!IsEngineExitRequested()) { AutoPlay::FExitWatchdog::Disarm(); }
		FTSTicker::GetCoreTicker().RemoveTicker(TickHandle);
		FWorldDelegates::OnWorldPostActorTick.Remove(PostTickHandle);
		if (InputBlocker.IsValid() && FSlateApplication::IsInitialized())
		{
			FSlateApplication::Get().UnregisterInputPreProcessor(InputBlocker);
		}
		if (AudioCapture && Phase < EPhase::Exporting)
		{
			// Quit mid-run: keep the audio captured so far.
			if (FAudioDevice* AudioDevice = GetGameWorld() ? GetGameWorld()->GetAudioDeviceRaw() : nullptr) { AutoPlayUnregisterCapture(AudioDevice, AudioCapture, AudioCaptureRef); }
			AudioCapture->Close();
		}
		AudioCapture = nullptr;
		AudioCaptureRef.Reset(); // before the audio device shuts down; the mixer keeps its own reference while it needs one
		if (Phase != EPhase::Done)
		{
			// Quit before the run finished (crash path, window closed): keep what we have.
			Telemetry(TEXT("run_aborted"), FString::Printf(TEXT("\"phase\":%d"), (int32)Phase));
			ClockSamples.Add(ClockSample(TEXT("end")));
			WriteTextFile(TEXT("clock.json"), FString::Printf(TEXT("{\"schema\":\"autoplay-clock/2\",\"scenario\":%d,\"scenario_name\":%s,\"qpc_frequency\":%llu,\"t_ns_definition\":\"qpc * 1e9 / qpc_frequency\",\"samples\":[%s]}\n"),
				Scenario, *JsonStr(ScenarioName), QpcFrequency(), *FString::Join(ClockSamples, TEXT(","))));
		}
		InputsAr.Reset();
		TelemetryAr.Reset();
	}
	Super::Deinitialize();
}

// ---------------------------------------------------------------------------------------------------------------------
// Per-frame state machine

void UAutoPlaySubsystem::EnforceWindowAndInput()
{
	SetCVar(TEXT("t.MaxFPS"), TEXT("60"));
	SetCVar(TEXT("r.VSync"), TEXT("0"));
	SetCVar(TEXT("au.DisableAppVolume"), TEXT("1")); // otherwise audio (and audio.wav) goes silent when the window loses focus
	SetCVar(TEXT("t.IdleWhenNotForeground"), TEXT("0"));

	if (!bAllowHardwareInput && !InputBlocker.IsValid() && FSlateApplication::IsInitialized())
	{
		InputBlocker = MakeShared<AutoPlay::FInputBlocker>();
		FSlateApplication::Get().RegisterInputPreProcessor(InputBlocker);
	}

	UGameViewportClient* VC = GEngine ? GEngine->GameViewport : nullptr;
	if (!VC)
	{
		return;
	}
	if (!bAllowHardwareInput && VC->GetMouseCaptureMode() != EMouseCaptureMode::NoCapture)
	{
		// Never trap the desktop cursor while the bot plays.
		VC->SetMouseCaptureMode(EMouseCaptureMode::NoCapture);
		VC->SetMouseLockMode(EMouseLockMode::DoNotLock);
		if (FSlateApplication::IsInitialized())
		{
			FSlateApplication::Get().ReleaseAllPointerCapture();
			if (TSharedPtr<ICursor> Cursor = FSlateApplication::Get().GetPlatformCursor())
			{
				Cursor->Lock(nullptr);
			}
		}
	}
	if (TSharedPtr<SWindow> Window = VC->GetWindow())
	{
		const FString Title = FString::Printf(TEXT("%s [AutoPlay]"), FApp::GetProjectName());
		if (Window->GetTitle().ToString() != Title)
		{
			Window->SetTitle(FText::FromString(Title));
		}
	}
}

bool UAutoPlaySubsystem::CoreTick(float DeltaTime)
{
	const double Now = FPlatformTime::Seconds();
	EnforceWindowAndInput();

	switch (Phase)
	{
	case EPhase::Boot:
	{
		UWorld* World = GetGameWorld();
		UGameViewportClient* VC = GEngine ? GEngine->GameViewport : nullptr;
		if (!World || !World->HasBegunPlay() || !VC || !VC->GetWindow().IsValid())
		{
			break;
		}
		if (!bSettingsApplied)
		{
			bSettingsApplied = true;
			if (UGameUserSettings* Settings = GEngine->GetGameUserSettings())
			{
				// Applied, never saved: the player's own settings stay untouched.
				Settings->SetFullscreenMode(EWindowMode::Windowed);
				Settings->SetScreenResolution(FIntPoint(1920, 1080));
				Settings->ApplyResolutionSettings(false);
			}
			Scalability::FQualityLevels Quality;
			Quality.SetFromSingleQualityLevel(3); // High, fixed (works in Shipping, unlike console commands)
			Scalability::SetQualityLevels(Quality);
			ReadyAt = Now + 1.0; // let the window settle before ready.json is written
		}
		else if (Now >= ReadyAt)
		{
			FIntPoint Size(0, 0);
			if (VC->Viewport) { Size = VC->Viewport->GetSizeXY(); }
			WriteTextFile(TEXT("ready.json"), FString::Printf(TEXT("{\"pid\":%u,\"title\":%s,\"viewport\":[%d,%d],\"scenario\":%d,\"scenario_name\":%s,%s}\n"),
				FPlatformProcess::GetCurrentProcessId(), *JsonStr(VC->GetWindow()->GetTitle().ToString()), Size.X, Size.Y,
				Scenario, *JsonStr(ScenarioName), *Stamp()));
			Telemetry(TEXT("autoplay_ready"), FString::Printf(TEXT("\"viewport\":[%d,%d]"), Size.X, Size.Y));
			Phase = EPhase::WaitingForGo;
			PhaseDeadline = Now + GoTimeout;
		}
		break;
	}
	case EPhase::WaitingForGo:
		if (Now >= NextGoPoll)
		{
			NextGoPoll = Now + 0.05;
			const bool bGo = FPaths::FileExists(OutputDir / TEXT("go"));
			if (bGo || Now >= PhaseDeadline)
			{
				BeginRun(!bGo);
			}
		}
		break;
	case EPhase::Running:
		if (MaxSeconds > 0.0 && (double)(Qpc() - GoQpc) / (double)QpcFrequency() >= MaxSeconds)
		{
			if (OnTimeout) { OnTimeout(); }
			if (Phase == EPhase::Running) { FinishRun(TEXT("timeout"), Score); }
		}
		break;
	case EPhase::Holding:
		if (Now >= PhaseDeadline) { StartExport(); }
		break;
	case EPhase::Exporting:
	{
		const int64 Size = IFileManager::Get().FileSize(*(OutputDir / TEXT("audio.wav")));
		if (Size != LastAudioSize) { LastAudioSize = Size; AudioStableSince = Now; }
		if (Size > 44 && Now - AudioStableSince >= 0.5) { FinalizeAndQuit(true); }
		else if (Now >= PhaseDeadline) { FinalizeAndQuit(Size > 44); }
		break;
	}
	default:
		break;
	}

	if (AudioCapture) { AudioCapture->Flush(); }
	if (Now - LastFlush >= 1.0)
	{
		LastFlush = Now;
		if (InputsAr) { InputsAr->Flush(); }
		if (TelemetryAr) { TelemetryAr->Flush(); }
	}
	return true;
}

void UAutoPlaySubsystem::BeginRun(bool bTimedOut)
{
	bGoTimedOut = bTimedOut;
	GoQpc = Qpc();
	GoFrame = GFrameCounter;
	ClockSamples.Add(ClockSample(TEXT("go")));
	FMath::RandInit(Seed);
	FMath::SRandInit(Seed);
	// Master-submix capture with a per-buffer clock (replaces StartRecordingOutput, which silently drops render stalls).
	if (FAudioDevice* AudioDevice = GetGameWorld() ? GetGameWorld()->GetAudioDeviceRaw() : nullptr)
	{
#if AUTOPLAY_SHARED_SUBMIX_LISTENER
		AudioCaptureRef = MakeShared<AutoPlay::FAudioCapture, ESPMode::ThreadSafe>();
		AudioCapture = AudioCaptureRef.Get();
#else
		AudioCapture = new AutoPlay::FAudioCapture();
#endif
		if (AudioCapture->Open(OutputDir / TEXT("audio.wav"), OutputDir / TEXT("audio_clock.jsonl")))
		{
			AudioCapture->Start();
#if AUTOPLAY_SHARED_SUBMIX_LISTENER
			AudioDevice->RegisterSubmixBufferListener(AudioCaptureRef.ToSharedRef(), AudioDevice->GetMainSubmixObject());
#else
			AudioDevice->RegisterSubmixBufferListener(AudioCapture, nullptr);
#endif
		}
	}
	ClockSamples.Add(ClockSample(TEXT("audio_start")));
	if (MaxSeconds > 0.0 && WatchdogSeconds > 0.0) { AutoPlay::FExitWatchdog::Arm(FPlatformTime::Seconds() + MaxSeconds + WatchdogSeconds, TEXT("run"), OutputDir / TEXT("watchdog.json")); }
	Phase = EPhase::Running;
	Telemetry(TEXT("run_start"), FString::Printf(TEXT("\"scenario\":%d,\"seed\":%d,\"skill\":%s,\"go_timed_out\":%s"),
		Scenario, Seed, *JsonNum(Skill), bTimedOut ? TEXT("true") : TEXT("false")));
	if (StartScenario)
	{
		StartScenario(Scenario);
	}
	else if (StartLevel)
	{
		StartLevel(Scenario); // v1.2 hook
	}
	else
	{
		Telemetry(TEXT("error"), TEXT("\"message\":\"game did not set UAutoPlaySubsystem::StartScenario\""));
		FinishRun(TEXT("abort"), 0.0);
	}
}

void UAutoPlaySubsystem::ScenarioStarted(const FString& InScenarioName)
{
	if (!bEnabled) { return; }
	ScenarioStartQpc = Qpc();
	ScenarioStartFrame = GFrameCounter;
	if (!InScenarioName.IsEmpty()) { ScenarioName = InScenarioName; }
	const UWorld* World = GetGameWorld();
	Telemetry(TEXT("scenario_start"), FString::Printf(TEXT("\"scenario\":%d,\"scenario_name\":%s,\"map\":%s"),
		Scenario, *JsonStr(ScenarioName), *JsonStr(World ? World->GetMapName() : FString())));
}

void UAutoPlaySubsystem::FinishRun(const FString& InResult, double FinalScore, const FString& ExtraJson)
{
	if (!bEnabled || Phase != EPhase::Running) { return; }
	ScenarioEndQpc = Qpc();
	ScenarioEndFrame = GFrameCounter;
	Result = InResult;
	Score = FinalScore;
	ResultExtra = ExtraJson;
	// Release everything the bot was holding.
	for (const TPair<const UInputAction*, FActiveInput>& Pair : ActiveInputs)
	{
		WriteLine(InputsAr.Get(), FString::Printf(TEXT("{%s,\"type\":\"release\",\"action\":%s,\"value_type\":\"%s\",\"value\":%s,\"key\":%s,\"edge\":\"up\"}"),
			*Stamp(), *JsonStr(Pair.Value.Name), AutoPlay::ValueTypeName(Pair.Value.Type), *AutoPlay::ZeroJson(Pair.Value.Type), *JsonStr(Pair.Value.Key)));
	}
	ActiveInputs.Reset();
	Telemetry(TEXT("scenario_end"), FString::Printf(TEXT("\"result\":%s,\"score\":%s%s%s"),
		*JsonStr(Result), *JsonNum(Score), ExtraJson.IsEmpty() ? TEXT("") : TEXT(","), *ExtraJson));
	Phase = EPhase::Holding;
	PhaseDeadline = FPlatformTime::Seconds() + 2.0; // keep the result screen on video
}

void UAutoPlaySubsystem::StartExport()
{
	int64 AudioFrames = 0, AudioSilence = 0; int32 AudioGaps = 0;
	if (AudioCapture)
	{
		if (FAudioDevice* AudioDevice = GetGameWorld() ? GetGameWorld()->GetAudioDeviceRaw() : nullptr)
		{
			AutoPlayUnregisterCapture(AudioDevice, AudioCapture, AudioCaptureRef);
		}
		AudioCapture->Close(); // stops accepting buffers first; the object stays alive for late audio-thread calls
		AudioFrames = AudioCapture->GetWrittenFrames(); AudioSilence = AudioCapture->GetSilenceFrames(); AudioGaps = AudioCapture->GetGaps();
		// Drop our reference now rather than at subsystem teardown (UE 5.4+: the mixer holds its own while it needs one;
		// UE 5.3: the object is left alive for late audio-thread calls).
		AudioCapture = nullptr;
		AudioCaptureRef.Reset();
	}
	ClockSamples.Add(ClockSample(TEXT("audio_stop")));

	const uint64 EndQpc = ScenarioEndQpc ? ScenarioEndQpc : Qpc();
	const uint64 StartQpc = ScenarioStartQpc ? ScenarioStartQpc : GoQpc;
	const double Duration = (double)(EndQpc - StartQpc) / (double)QpcFrequency();
	const double RunDuration = (double)(EndQpc - GoQpc) / (double)QpcFrequency();
	WriteTextFile(TEXT("outcome.json"), FString::Printf(
		TEXT("{\"schema\":\"autoplay-outcome/2\",%s,\"result\":%s,\"score\":%s,")
		TEXT("\"duration_s\":%s,\"run_duration_s\":%s,\"go_qpc\":%llu,\"scenario_start_qpc\":%llu,\"scenario_end_qpc\":%llu,")
		TEXT("\"frames\":%llu,\"inputs_injected\":%lld,\"audio_frames\":%lld,\"audio_silence_frames\":%lld,\"audio_gaps\":%d,\"go_timed_out\":%s,\"build_config\":%s,\"engine_version\":%s,\"extra\":{%s}}\n"),
		*HeaderFields(), *JsonStr(Result), *JsonNum(Score),
		*JsonNum(Duration), *JsonNum(RunDuration), GoQpc, ScenarioStartQpc, ScenarioEndQpc,
		ScenarioEndFrame - (ScenarioStartFrame ? ScenarioStartFrame : GoFrame), InjectCount, AudioFrames, AudioSilence, AudioGaps, bGoTimedOut ? TEXT("true") : TEXT("false"),
		*JsonStr(LexToString(FApp::GetBuildConfiguration())), *JsonStr(FEngineVersion::Current().ToString()), *ResultExtra));

	Phase = EPhase::Exporting;
	LastAudioSize = -1;
	AudioStableSince = FPlatformTime::Seconds();
	PhaseDeadline = FPlatformTime::Seconds() + 20.0; // the WAV is written on a background thread
}

void UAutoPlaySubsystem::FinalizeAndQuit(bool bAudioOk)
{
	ClockSamples.Add(ClockSample(TEXT("end")));
	WriteTextFile(TEXT("clock.json"), FString::Printf(TEXT("{\"schema\":\"autoplay-clock/2\",\"scenario\":%d,\"scenario_name\":%s,\"qpc_frequency\":%llu,\"t_ns_definition\":\"qpc * 1e9 / qpc_frequency\",\"samples\":[%s]}\n"),
		Scenario, *JsonStr(ScenarioName), QpcFrequency(), *FString::Join(ClockSamples, TEXT(","))));
	Telemetry(TEXT("run_end"), FString::Printf(TEXT("\"audio_ok\":%s"), bAudioOk ? TEXT("true") : TEXT("false")));
	InputsAr.Reset();
	TelemetryAr.Reset();
	Phase = EPhase::Done;
	if (WatchdogSeconds > 0.0) { AutoPlay::FExitWatchdog::Arm(FPlatformTime::Seconds() + ShutdownWatchdogSeconds, TEXT("shutdown"), OutputDir / TEXT("watchdog.json")); }
	FPlatformMisc::RequestExit(false);
}

// ---------------------------------------------------------------------------------------------------------------------
// Input

void UAutoPlaySubsystem::Inject(APlayerController* PC, const UInputAction* Action, FInputActionValue Value, const FString& Key)
{
	if (!bEnabled || Phase != EPhase::Running || !PC || !Action) { return; }
	UEnhancedInputLocalPlayerSubsystem* EIS = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PC->GetLocalPlayer());
	if (!EIS) { return; }

	EIS->InjectInputForAction(Action, Value, TArray<UInputModifier*>(), TArray<UInputTrigger*>());
	++InjectCount;

	if (!DescribedActions.Contains(Action))
	{
		DescribedActions.Add(Action);
		TArray<FString> Keys;
		for (const FKey& Mapped : EIS->QueryKeysMappedToAction(Action)) { Keys.Add(JsonStr(Mapped.ToString())); }
		WriteLine(InputsAr.Get(), FString::Printf(TEXT("{%s,\"type\":\"action_info\",\"action\":%s,\"value_type\":\"%s\",\"mapped_keys\":[%s]}"),
			*Stamp(), *JsonStr(Action->GetName()), AutoPlay::ValueTypeName(Action->ValueType), *FString::Join(Keys, TEXT(","))));
	}

	const TCHAR* Edge;
	FActiveInput* Active = ActiveInputs.Find(Action);
	if (Value.IsNonZero())
	{
		Edge = Active ? TEXT("hold") : TEXT("down");
		if (!Active) { Active = &ActiveInputs.Add(Action); }
		Active->LastFrame = GFrameCounter;
		Active->Key = Key;
		Active->Type = Value.GetValueType();
		Active->Name = Action->GetName();
	}
	else
	{
		Edge = Active ? TEXT("up") : TEXT("zero");
		ActiveInputs.Remove(Action);
	}
	WriteLine(InputsAr.Get(), FString::Printf(TEXT("{%s,\"type\":\"inject\",\"action\":%s,\"value_type\":\"%s\",\"value\":%s,\"key\":%s,\"edge\":\"%s\"}"),
		*Stamp(), *JsonStr(Action->GetName()), AutoPlay::ValueTypeName(Value.GetValueType()), *AutoPlay::ValueJson(Value), *JsonStr(Key), Edge));
}

void UAutoPlaySubsystem::OnPostActorTick(UWorld* World, ELevelTick TickType, float DeltaSeconds)
{
	if (!bEnabled || World != GetGameWorld() || ActiveInputs.Num() == 0) { return; }
	// An input not injected this frame was released this frame.
	for (auto It = ActiveInputs.CreateIterator(); It; ++It)
	{
		if (It.Value().LastFrame != (uint64)GFrameCounter)
		{
			WriteLine(InputsAr.Get(), FString::Printf(TEXT("{%s,\"type\":\"release\",\"action\":%s,\"value_type\":\"%s\",\"value\":%s,\"key\":%s,\"edge\":\"up\"}"),
				*Stamp(), *JsonStr(It.Value().Name), AutoPlay::ValueTypeName(It.Value().Type), *AutoPlay::ZeroJson(It.Value().Type), *JsonStr(It.Value().Key)));
			It.RemoveCurrent();
		}
	}
}

void UAutoPlaySubsystem::SetVirtualCursor(const FVector2D& ViewportPos)
{
	if (!bEnabled || Phase != EPhase::Running) { return; }
	if (bHasVirtualCursor && ViewportPos.Equals(VirtualCursor, 0.01)) { return; }
	bHasVirtualCursor = true;
	VirtualCursor = ViewportPos;
	WriteLine(InputsAr.Get(), FString::Printf(TEXT("{%s,\"type\":\"cursor\",\"key\":\"MousePosition\",\"value\":[%s,%s]}"),
		*Stamp(), *JsonNum(ViewportPos.X), *JsonNum(ViewportPos.Y)));
}

bool UAutoPlaySubsystem::GetCursorPosition(const APlayerController* PC, FVector2D& OutViewportPos) const
{
	if (bEnabled && bHasVirtualCursor)
	{
		OutViewportPos = VirtualCursor;
		return true;
	}
	float X = 0.f, Y = 0.f;
	if (PC && PC->GetMousePosition(X, Y))
	{
		OutViewportPos = FVector2D(X, Y);
		return true;
	}
	return false;
}

// ---------------------------------------------------------------------------------------------------------------------
// Telemetry

void UAutoPlaySubsystem::Telemetry(const FString& Event, const FString& FieldsJson)
{
	if (!bEnabled || !TelemetryAr) { return; }
	WriteLine(TelemetryAr.Get(), FString::Printf(TEXT("{%s,\"event\":%s%s%s}"),
		*Stamp(), *JsonStr(Event), FieldsJson.IsEmpty() ? TEXT("") : TEXT(","), *FieldsJson));
}
