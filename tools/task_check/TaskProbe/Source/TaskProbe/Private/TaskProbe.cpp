#include "TaskProbe.h"

#include "TaskProbeQueries.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/Button.h"
#include "Framework/Application/SlateApplication.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "HAL/PlatformMisc.h"
#include "InputKeyEventArgs.h"
#include "Misc/App.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Modules/ModuleManager.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "UnrealClient.h"

IMPLEMENT_MODULE(FDefaultModuleImpl, TaskProbe)

DEFINE_LOG_CATEGORY_STATIC(LogTaskProbe, Log, All);

/** A play with sound (-TaskProbeSound) runs without -benchmark, which would turn the engine's audio off: the application
 *  counts as focused throughout, as -benchmark has it, so a game sees the same focus either way. */
static bool AlwaysFocused() { return true; }

/** The player pawn placed at Location (a free spot near it, as the engine's teleport finds one), facing Yaw when set. */
static void PlacePawn(APlayerController* PC, const FVector& Location, bool bHasYaw, double Yaw)
{
	APawn* Pawn = PC->GetPawn();
	if (!Pawn)
	{
		return;
	}
	FRotator Rot = Pawn->GetActorRotation();
	if (bHasYaw)
	{
		Rot.Yaw = Yaw;
	}
	if (!Pawn->TeleportTo(Location, Rot))
	{
		Pawn->SetActorLocationAndRotation(Location, Rot, false, nullptr, ETeleportType::TeleportPhysics);
	}
	if (bHasYaw)
	{
		FRotator Control = PC->GetControlRotation();
		Control.Yaw = Yaw;
		PC->SetControlRotation(Control);
	}
}

bool UTaskProbe::ShouldCreateSubsystem(UObject* Outer) const
{
	return FParse::Param(FCommandLine::Get(), TEXT("TaskProbe"));
}

void UTaskProbe::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	FParse::Value(FCommandLine::Get(), TEXT("-TaskProbeOut="), OutDir);
	if (OutDir.IsEmpty())
	{
		OutDir = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("TaskProbe"));
	}
	FParse::Value(FCommandLine::Get(), TEXT("-TaskProbeSeconds="), Seconds);
	FParse::Value(FCommandLine::Get(), TEXT("-TaskProbeShots="), Shots);
	FParse::Value(FCommandLine::Get(), TEXT("-TaskProbeEvery="), Every);
	Seconds = FMath::Clamp(Seconds, 1.0, 600.0);
	Every = FMath::Clamp(Every, 0.1, 1.0);
	Shots = FMath::Clamp(Shots, 0, 64);
	if (FParse::Param(FCommandLine::Get(), TEXT("TaskProbeSound")))
	{
		FApp::SetHasFocusFunction(&AlwaysFocused);
	}
	FString InputsPath;
	if (FParse::Value(FCommandLine::Get(), TEXT("-TaskProbeInputs="), InputsPath))
	{
		LoadInputs(InputsPath);
	}
	FString QueriesPath;
	if (FParse::Value(FCommandLine::Get(), TEXT("-TaskProbeQueries="), QueriesPath))
	{
		Queries = MakeShared<FTaskProbeQueries>();
		Queries->Load(QueriesPath);
	}
	IFileManager::Get().MakeDirectory(*OutDir, true);
	TickHandle = FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateUObject(this, &UTaskProbe::Tick));
}

void UTaskProbe::Deinitialize()
{
	if (!bDone)
	{
		Finish(TEXT("shutdown"));
	}
	FTSTicker::GetCoreTicker().RemoveTicker(TickHandle);
	Queries.Reset();
	Super::Deinitialize();
}

void UTaskProbe::LoadInputs(const FString& Path)
{
	// [{"t": 1.5, "key": "SpaceBar", "press": true}, ...] in key-name form FKey understands (W, A, SpaceBar, LeftMouseButton);
	// also {"t", "key": "MouseX", "axis": 4.0} (an axis event), {"t", "widget": "RetryButton", "click": true} (click a
	// button), {"t", "cursor": [fx, fy]} (move the mouse cursor to a viewport point, fractions 0-1),
	// {"t", "teleport": [x, y, z], "yaw": deg} (place the player pawn) and {"t", "teleport_to": <actor select>,
	// "distance": cm, "offset": [x, y, z], "face": <point>} (place it next to the nearest actor the select matches,
	// facing that actor or the point)
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *Path))
	{
		return;
	}
	TArray<TSharedPtr<FJsonValue>> Rows;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
	if (!FJsonSerializer::Deserialize(Reader, Rows))
	{
		return;
	}
	auto ReadNumbers = [](const TSharedPtr<FJsonObject>& O, const TCHAR* Key, int32 Count, TArray<double>& Out)
	{
		const TArray<TSharedPtr<FJsonValue>>* A = nullptr;
		if (!O->TryGetArrayField(Key, A) || A->Num() < Count)
		{
			return false;
		}
		for (int32 i = 0; i < Count; ++i)
		{
			double V = 0.0;
			if (!(*A)[i].IsValid() || !(*A)[i]->TryGetNumber(V))
			{
				return false;
			}
			Out.Add(V);
		}
		return true;
	};
	for (const TSharedPtr<FJsonValue>& Row : Rows)
	{
		const TSharedPtr<FJsonObject>* Obj = nullptr;
		if (!Row.IsValid() || !Row->TryGetObject(Obj))
		{
			continue;
		}
		FScriptedKey K;
		(*Obj)->TryGetNumberField(TEXT("t"), K.Time);
		FString Name;
		TArray<double> Numbers;
		bool bClick = false;
		const TSharedPtr<FJsonObject>* Target = nullptr;
		if ((*Obj)->TryGetStringField(TEXT("widget"), K.Widget) && (*Obj)->TryGetBoolField(TEXT("click"), bClick) && bClick && !K.Widget.IsEmpty())
		{
			K.Kind = EScriptedKind::Click;
		}
		else if (ReadNumbers(*Obj, TEXT("cursor"), 2, Numbers))
		{
			K.Kind = EScriptedKind::Cursor;
			K.Cursor = FVector2D(Numbers[0], Numbers[1]);
		}
		else if ((*Obj)->TryGetObjectField(TEXT("teleport_to"), Target) && Target->IsValid())
		{
			K.Kind = EScriptedKind::TeleportTo;
			K.Target = *Target;
			(*Obj)->TryGetNumberField(TEXT("distance"), K.Distance);
			K.Distance = FMath::Clamp(K.Distance, 0.0, 100000.0);
			if (ReadNumbers(*Obj, TEXT("offset"), 3, Numbers))
			{
				K.Offset = FVector(Numbers[0], Numbers[1], Numbers[2]);
			}
			const TSharedPtr<FJsonObject>* Face = nullptr;
			if ((*Obj)->TryGetObjectField(TEXT("face"), Face) && Face->IsValid())
			{
				K.Face = *Face;
			}
		}
		else if (ReadNumbers(*Obj, TEXT("teleport"), 3, Numbers))
		{
			K.Kind = EScriptedKind::Teleport;
			K.Teleport = FVector(Numbers[0], Numbers[1], Numbers[2]);
			K.bHasYaw = (*Obj)->TryGetNumberField(TEXT("yaw"), K.Yaw);
		}
		else if ((*Obj)->TryGetStringField(TEXT("key"), Name))
		{
			K.Key = FKey(*Name);
			if (!K.Key.IsValid())
			{
				continue;
			}
			double Axis = 0.0;
			if ((*Obj)->TryGetNumberField(TEXT("axis"), Axis))
			{
				K.Kind = EScriptedKind::Axis;
				K.Axis = Axis;
			}
			else
			{
				(*Obj)->TryGetBoolField(TEXT("press"), K.bPress);
			}
		}
		else
		{
			continue;
		}
		Inputs.Add(K);
	}
	Inputs.StableSort([](const FScriptedKey& A, const FScriptedKey& B) { return A.Time < B.Time; });
}

void UTaskProbe::SendInput(const FScriptedKey& K, UWorld* World, APlayerController* PC)
{
	switch (K.Kind)
	{
	case EScriptedKind::Key:
		if (bCursorSet && K.Key.IsMouseButton() && FSlateApplication::IsInitialized())
		{
			// after a cursor move a mouse button goes through Slate at the cursor, as a player's click: the UI under
			// it hit-tests, else the viewport passes it to the player controller
			TSet<FKey> Pressed;
			if (K.bPress)
			{
				Pressed.Add(K.Key);
			}
			const FPointerEvent Event(FSlateApplication::CursorPointerIndex, CursorAbsolute, CursorAbsolute, Pressed, K.Key, 0.f, FModifierKeysState());
			const bool bHandled = K.bPress ? FSlateApplication::Get().ProcessMouseButtonDownEvent(TSharedPtr<FGenericWindow>(), Event)
				: FSlateApplication::Get().ProcessMouseButtonUpEvent(Event);
			UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: %s %s at the cursor through Slate: %s"), *K.Key.ToString(),
				K.bPress ? TEXT("press") : TEXT("release"), bHandled ? TEXT("handled") : TEXT("unhandled, sent to the player controller"));
			if (bHandled)
			{
				break;
			}
		}
		PC->InputKey(FInputKeyEventArgs::CreateSimulated(K.Key, K.bPress ? IE_Pressed : IE_Released, K.bPress ? 1.f : 0.f));
		break;
	case EScriptedKind::Axis:
		PC->InputKey(FInputKeyEventArgs::CreateSimulated(K.Key, IE_Axis, (float)K.Axis, 1));
		break;
	case EScriptedKind::Click:
		if (UButton* Button = TaskProbe::FindButton(World, K.Widget))
		{
			// what a player's click on the button fires: pressed, released, clicked
			Button->OnPressed.Broadcast();
			Button->OnReleased.Broadcast();
			Button->OnClicked.Broadcast();
			UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: clicked button %s (%s)"), *Button->GetName(), *Button->GetClass()->GetName());
		}
		else
		{
			UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: no visible button matches '%s'"), *K.Widget);
		}
		break;
	case EScriptedKind::Cursor:
	{
		FVector2D Absolute;
		if (!TaskProbe::ViewportPoint(K.Cursor.X, K.Cursor.Y, Absolute) || !FSlateApplication::IsInitialized())
		{
			UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: cursor move skipped (no game viewport)"));
			break;
		}
		// a synthetic mouse move at that point: Slate's pointer position and the viewport's mouse position follow it
		// (the OS cursor is not moved)
		const FVector2D Last = bCursorSet ? CursorAbsolute : Absolute;
		const TSet<FKey> NoButtons;
		const FPointerEvent Move(FSlateApplication::CursorPointerIndex, Absolute, Last, NoButtons, EKeys::Invalid, 0.f, FModifierKeysState());
		const bool bHandled = FSlateApplication::Get().ProcessMouseMoveEvent(Move);
		CursorAbsolute = Absolute;
		bCursorSet = true;
		float MX = -1.f, MY = -1.f;
		const bool bMouse = PC->GetMousePosition(MX, MY);
		UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: cursor to (%.3f, %.3f) = absolute (%.0f, %.0f), Slate %s, player mouse %s (%.0f, %.0f)"),
			K.Cursor.X, K.Cursor.Y, Absolute.X, Absolute.Y, bHandled ? TEXT("handled") : TEXT("unhandled"), bMouse ? TEXT("at") : TEXT("unknown"), MX, MY);
		break;
	}
	case EScriptedKind::Teleport:
		PlacePawn(PC, K.Teleport, K.bHasYaw, K.Yaw);
		break;
	case EScriptedKind::TeleportTo:
	{
		FVector Location;
		double Yaw = 0.0;
		FString Name;
		if (!PC->GetPawn() || !TaskProbe::TeleportSpot(World, PC, K.Target, K.Distance, K.Offset, K.Face, Location, Yaw, Name))
		{
			UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: teleport_to skipped (%s)"), PC->GetPawn() ? TEXT("no actor matches") : TEXT("no pawn"));
			break;
		}
		PlacePawn(PC, Location, true, Yaw);
		const FVector At = PC->GetPawn()->GetActorLocation();
		UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: teleported next to %s: asked (%.0f, %.0f, %.0f) yaw %.1f, now at (%.0f, %.0f, %.0f)"), *Name,
			Location.X, Location.Y, Location.Z, Yaw, At.X, At.Y, At.Z);
		break;
	}
	}
	++InputsSent;
}

bool UTaskProbe::Tick(float DeltaTime)
{
	if (bDone)
	{
		return false;
	}
	// The world and the player controller are fetched every tick: a map travel replaces both, and the play's clock keeps
	// counting through it once the first world has begun play.
	UGameInstance* GI = GetGameInstance();
	UWorld* World = GI ? GI->GetWorld() : nullptr;
	if (!bStarted)
	{
		if (!World || !World->HasBegunPlay())
		{
			return true;
		}
		bStarted = true;
	}
	Elapsed += DeltaTime;
	APlayerController* PC = World && World->HasBegunPlay() ? World->GetFirstPlayerController() : nullptr;

	// inputs wait for a player controller (e.g. during a map travel)
	while (PC && NextInput < Inputs.Num() && Inputs[NextInput].Time <= Elapsed)
	{
		SendInput(Inputs[NextInput++], World, PC);
	}

	if (Elapsed >= NextTrack)
	{
		NextTrack += Every;
		const APawn* Pawn = PC ? PC->GetPawn() : nullptr;
		TArray<TSharedPtr<FJsonValue>> Row;
		Row.Add(MakeShared<FJsonValueNumber>(Elapsed));
		if (Pawn)
		{
			const FVector L = Pawn->GetActorLocation();
			Row.Add(MakeShared<FJsonValueNumber>(L.X));
			Row.Add(MakeShared<FJsonValueNumber>(L.Y));
			Row.Add(MakeShared<FJsonValueNumber>(L.Z));
		}
		Track.Add(MakeShared<FJsonValueArray>(Row));
		// the view the player sees: [t, x, y, z, pitch, yaw, fov], the camera's world location in cm, degrees
		if (const APlayerCameraManager* View = PC ? PC->PlayerCameraManager.Get() : nullptr)
		{
			const FVector C = View->GetCameraLocation();
			const FRotator R = View->GetCameraRotation();
			TArray<TSharedPtr<FJsonValue>> Seen;
			for (const double V : {Elapsed, C.X, C.Y, C.Z, R.Pitch, R.Yaw, (double)View->GetFOVAngle()})
			{
				Seen.Add(MakeShared<FJsonValueNumber>(V));
			}
			Camera.Add(MakeShared<FJsonValueArray>(Seen));
		}
		if (Queries)
		{
			Queries->Sample(World, PC, Elapsed);
		}
	}

	// Screenshots evenly over the run, the first a little after the start (the first frames are often still loading).
	if (Shots > 0 && ShotsTaken < Shots && Elapsed >= Seconds * (ShotsTaken + 0.5) / Shots)
	{
		const FString Name = FString::Printf(TEXT("shot_%02d.png"), ShotsTaken);
		// with the UI (the HUD, menus): what the player sees, so a HUD change shows in the screenshots
		FScreenshotRequest::RequestScreenshot(FPaths::Combine(OutDir, Name), true, false);
		ShotNames.Add(MakeShared<FJsonValueString>(Name));
		++ShotsTaken;
	}

	if (Elapsed >= Seconds + 0.5)
	{
		// a screen sample reads the frame drawn after it: the last one waits for that frame (a few frames at most)
		if (Queries && Queries->WaitsForFrame() && FramesWaited++ < 5)
		{
			return true;
		}
		Finish(TEXT("time"));
		FPlatformMisc::RequestExit(false);
		return false;
	}
	return true;
}

void UTaskProbe::Finish(const FString& Reason)
{
	bDone = true;
	UGameInstance* GI = GetGameInstance();
	UWorld* World = GI ? GI->GetWorld() : nullptr;
	const TSharedRef<FJsonObject> Out = MakeShared<FJsonObject>();
	Out->SetStringField(TEXT("format"), TEXT("game-probe/1"));
	Out->SetStringField(TEXT("ended"), Reason);
	Out->SetNumberField(TEXT("seconds"), Elapsed);
	Out->SetStringField(TEXT("map"), World ? World->GetMapName() : FString());
	Out->SetNumberField(TEXT("inputs_sent"), InputsSent);
	Out->SetArrayField(TEXT("screenshots"), ShotNames);
	Out->SetArrayField(TEXT("track"), Track);
	Out->SetArrayField(TEXT("camera"), Camera);
	if (Queries)
	{
		Out->SetObjectField(TEXT("measures"), Queries->MeasuresJson());
		if (Queries->Errors().Num() > 0)
		{
			TArray<TSharedPtr<FJsonValue>> Errors;
			for (const FString& E : Queries->Errors())
			{
				Errors.Add(MakeShared<FJsonValueString>(E));
			}
			Out->SetArrayField(TEXT("query_errors"), Errors);
		}
	}
	FString Text;
	const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Text);
	FJsonSerializer::Serialize(Out, Writer);
	// UTF-8 always: the default writes UTF-16 as soon as the text has a non-ASCII character (a HUD text in measures)
	FFileHelper::SaveStringToFile(Text, *FPaths::Combine(OutDir, TEXT("probe.json")), FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
}
