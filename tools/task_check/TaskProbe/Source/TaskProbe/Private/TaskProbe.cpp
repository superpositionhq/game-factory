#include "TaskProbe.h"

#include "TaskProbeQueries.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/Button.h"
#include "Framework/Application/SlateApplication.h"
#include "GenericPlatform/GenericPlatformInputDeviceMapper.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "Engine/HitResult.h"
#include "GameFramework/DamageType.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PawnMovementComponent.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "HAL/PlatformProcess.h"
#include "HAL/PlatformTime.h"
#include "InputKeyEventArgs.h"
#include "Kismet/GameplayStatics.h"
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
#include "Widgets/SViewport.h"
#if PLATFORM_LINUX && WITH_EDITOR
#include "ShaderCompiler.h"
#endif

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

/** The game viewport's Slate widget, or null. */
static TSharedPtr<SViewport> GameViewportWidget()
{
	const UGameViewportClient* GVC = GEngine ? GEngine->GameViewport.Get() : nullptr;
	return GVC ? GVC->GetGameViewportWidget() : nullptr;
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
	if (HoldHandle.IsValid())
	{
		FWorldDelegates::OnWorldPostActorTick.Remove(HoldHandle);
	}
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
	// facing that actor or the point); either teleport with "hold": seconds keeps the pawn at the spot that long, put back
	// after every world tick; {"t", "wait": seconds} (the play's clock holds that long in real time while the game runs
	// on); {"t", "wheel": notches} (mouse wheel steps at the cursor, positive away from the player) and {"t", "move":
	// [dx, dy], "over": seconds} (the mouse moved by that many pixels, right and down, spread over the seconds), both
	// through Slate as a device's are; {"t", "shot": "<name>"} (a screenshot with the UI, shot_<name>.png); {"t", "map":
	// "/Game/...?opts"} (the play travels to that map; its clock runs on through the load) and {"t", "view": [pitch,
	// yaw]} (the player's view turns there): one launch visits several places and scenarios and pictures each; and the stages of a contact
	// (docs/task-probes.md, section 1.3): {"t", "pin": <actor select>, "hold": seconds, "front": cm, "at": <point>, "offset": [x, y, z]} (the nearest match
	// held at its place, first set ahead of the pawn with front, or at a point with at), {"t", "damage": points, "to": <select>, "from": <select>} (the
	// engine's damage call), {"t", "set": "<path>", "on": <select>, "value": v, "all": bool} (a reflected property
	// written); and touches, sent through Slate as a touch screen's are: {"t", "tap": <spot>, "hold": seconds, "finger": n}
	// (finger n goes down at the spot and lifts after the hold, the next frame without one) and {"t", "drag": [<spot>,
	// <spot>, ...], "over": seconds, "hold": seconds, "finger": n} (it goes down at the first spot, moves through the
	// others evenly over the seconds, stays at the last for the hold, then lifts); a spot is a viewport point [fx, fy]
	// in fractions 0-1 or {"widget": "<name>"}, the centre of that widget; fingers 0-9 may be down at the same time
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
	auto ReadSpot = [](const TSharedPtr<FJsonValue>& V, FTouchSpot& Out)
	{
		const TArray<TSharedPtr<FJsonValue>>* A = nullptr;
		const TSharedPtr<FJsonObject>* O = nullptr;
		if (V.IsValid() && V->TryGetArray(A) && A->Num() == 2 && (*A)[0].IsValid() && (*A)[1].IsValid() && (*A)[0]->TryGetNumber(Out.At.X)
			&& (*A)[1]->TryGetNumber(Out.At.Y))
		{
			return true;
		}
		Out.bWidget = V.IsValid() && V->TryGetObject(O) && O->IsValid() && (*O)->TryGetStringField(TEXT("widget"), Out.Widget) && !Out.Widget.IsEmpty();
		return Out.bWidget;
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
		const TSharedPtr<FJsonObject>* On = nullptr;
		if ((*Obj)->HasField(TEXT("tap")) || (*Obj)->HasField(TEXT("drag")))
		{
			K.Kind = EScriptedKind::Touch;
			K.bDrag = (*Obj)->HasField(TEXT("drag"));
			const TArray<TSharedPtr<FJsonValue>>* Spots = nullptr;
			FTouchSpot Spot;
			if (!K.bDrag && ReadSpot((*Obj)->TryGetField(TEXT("tap")), Spot))
			{
				K.Spots.Add(Spot);
			}
			else if (K.bDrag && (*Obj)->TryGetArrayField(TEXT("drag"), Spots))
			{
				for (const TSharedPtr<FJsonValue>& V : *Spots)
				{
					FTouchSpot Next;
					if (!ReadSpot(V, Next))
					{
						K.Spots.Reset();
						break;
					}
					K.Spots.Add(Next);
				}
			}
			if (K.Spots.Num() < (K.bDrag ? 2 : 1) || K.Spots.Num() > 16)
			{
				continue;
			}
			double Finger = 0.0;
			(*Obj)->TryGetNumberField(TEXT("finger"), Finger);
			K.Finger = FMath::RoundToInt(Finger);
			if (K.Finger < 0 || K.Finger > 9)
			{
				// never sent as another finger: a touch of a finger the engine doesn't have is a miss the play reports
				Missed(K, K.bDrag ? TEXT("drag") : TEXT("tap"), FString::Printf(TEXT("finger %d"), K.Finger), TEXT("a finger is 0 to 9"));
				continue;
			}
			(*Obj)->TryGetNumberField(TEXT("hold"), K.Press);
			K.Press = FMath::Clamp(K.Press, 0.0, 300.0);
			(*Obj)->TryGetNumberField(TEXT("over"), K.Over);
			K.Over = FMath::Clamp(K.Over, 0.0, 300.0);
		}
		else if ((*Obj)->TryGetObjectField(TEXT("pin"), Target) && Target->IsValid())
		{
			K.Kind = EScriptedKind::Pin;
			K.Target = *Target;
			(*Obj)->TryGetNumberField(TEXT("hold"), K.Hold);
			K.bFront = (*Obj)->TryGetNumberField(TEXT("front"), K.Front);
			K.Front = FMath::Clamp(K.Front, 0.0, 100000.0);
			const TSharedPtr<FJsonObject>* At = nullptr;
			if ((*Obj)->TryGetObjectField(TEXT("at"), At) && At->IsValid())
			{
				K.At = *At;
			}
			if (ReadNumbers(*Obj, TEXT("offset"), 3, Numbers))
			{
				K.Offset = FVector(Numbers[0], Numbers[1], Numbers[2]);
			}
		}
		else if ((*Obj)->TryGetNumberField(TEXT("damage"), K.Amount) && (*Obj)->TryGetObjectField(TEXT("to"), Target) && Target->IsValid())
		{
			K.Kind = EScriptedKind::Damage;
			K.Target = *Target;
			const TSharedPtr<FJsonObject>* From = nullptr;
			if ((*Obj)->TryGetObjectField(TEXT("from"), From) && From->IsValid())
			{
				K.From = *From;
			}
		}
		else if ((*Obj)->TryGetStringField(TEXT("set"), K.Path) && (*Obj)->TryGetObjectField(TEXT("on"), On) && On->IsValid())
		{
			K.Kind = EScriptedKind::Set;
			K.Target = *On;
			K.Value = (*Obj)->TryGetField(TEXT("value"));
			(*Obj)->TryGetBoolField(TEXT("all"), K.bAll);
		}
		else if ((*Obj)->TryGetStringField(TEXT("widget"), K.Widget) && (*Obj)->TryGetBoolField(TEXT("click"), bClick) && bClick && !K.Widget.IsEmpty())
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
			(*Obj)->TryGetNumberField(TEXT("hold"), K.Hold);
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
			(*Obj)->TryGetNumberField(TEXT("hold"), K.Hold);
		}
		else if ((*Obj)->TryGetStringField(TEXT("shot"), K.Shot))
		{
			if (K.Shot.IsEmpty() || K.Shot.Len() > 32 || K.Shot.Contains(TEXT("/")) || K.Shot.Contains(TEXT("\\")) || K.Shot.Contains(TEXT("..")))
			{
				continue;
			}
			K.Kind = EScriptedKind::Shot;
			const TSharedPtr<FJsonObject>* WhenObj = nullptr;
			if ((*Obj)->TryGetObjectField(TEXT("when"), WhenObj) && WhenObj->IsValid())
			{
				K.When = *WhenObj;  // taken in the first frame its event holds (Watch)
				if (!Watcher)
				{
					Watcher = MakeShared<FTaskProbeQueries>();
				}
			}
		}
		else if ((*Obj)->TryGetStringField(TEXT("map"), K.Map))
		{
			if (!K.Map.StartsWith(TEXT("/")))
			{
				continue;
			}
			K.Kind = EScriptedKind::Travel;
		}
		else if (ReadNumbers(*Obj, TEXT("view"), 2, Numbers))
		{
			K.Kind = EScriptedKind::View;
			K.View = FRotator(FMath::Clamp(Numbers[0], -89.0, 89.0), Numbers[1], 0.0);
		}
		else if ((*Obj)->TryGetNumberField(TEXT("wait"), K.Wait))
		{
			K.Kind = EScriptedKind::Wait;
			K.Wait = FMath::Clamp(K.Wait, 0.0, 600.0);
		}
		else if ((*Obj)->HasField(TEXT("wheel")))
		{
			double Notches = 0.0;
			(*Obj)->TryGetNumberField(TEXT("wheel"), Notches);
			K.Wheel = FMath::Clamp(FMath::RoundToInt(Notches), -20, 20);
			if (K.Wheel == 0)
			{
				continue;
			}
			K.Kind = EScriptedKind::Wheel;
		}
		else if ((*Obj)->HasField(TEXT("move")))
		{
			TArray<double> By;
			if (!ReadNumbers(*Obj, TEXT("move"), 2, By))
			{
				continue;
			}
			K.Kind = EScriptedKind::Move;
			K.Move = FVector2D(FMath::Clamp(By[0], -5000.0, 5000.0), FMath::Clamp(By[1], -5000.0, 5000.0));
			(*Obj)->TryGetNumberField(TEXT("over"), K.Over);
			K.Over = FMath::Clamp(K.Over, 0.0, 300.0);
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
		K.Hold = FMath::Clamp(K.Hold, 0.0, 600.0);
		Inputs.Add(K);
	}
	Inputs.StableSort([](const FScriptedKey& A, const FScriptedKey& B) { return A.Time < B.Time; });
	if (Inputs.ContainsByPredicate([](const FScriptedKey& K) { return K.Hold > 0.0; }))
	{
		HoldHandle = FWorldDelegates::OnWorldPostActorTick.AddUObject(this, &UTaskProbe::HoldInPlace);
	}
}

void UTaskProbe::HoldInPlace(UWorld* World, ELevelTick TickType, float DeltaSeconds)
{
	// after every world tick of a hold, the pawn goes back to the spot (still), whatever the game's own tick did with
	// it, and the camera is brought up to date with it; a pinned actor goes back to its spot, its movement stopped (its
	// own logic, turning, animation and attacks run on)
	UGameInstance* GI = GetGameInstance();
	if (bDone || !GI || World != GI->GetWorld() || !World->HasBegunPlay())
	{
		return;
	}
	for (const FPinned& P : Pinned)
	{
		AActor* A = P.Actor.Get();
		if (!A || A->IsActorBeingDestroyed() || Elapsed >= P.Until)
		{
			continue;
		}
		if (FVector::DistSquared(A->GetActorLocation(), P.At) > 0.01)
		{
			A->SetActorLocation(P.At, false, nullptr, ETeleportType::TeleportPhysics);
		}
		if (const APawn* Held = Cast<APawn>(A))
		{
			if (UPawnMovementComponent* Move = Held->GetMovementComponent())
			{
				Move->Velocity = FVector::ZeroVector;
			}
		}
	}
	if (Elapsed >= HoldUntil)
	{
		return;
	}
	APlayerController* PC = World->GetFirstPlayerController();
	APawn* Pawn = PC ? PC->GetPawn() : nullptr;
	if (!Pawn)
	{
		return;
	}
	if (FVector::DistSquared(Pawn->GetActorLocation(), HoldAt) > 0.01)
	{
		Pawn->SetActorLocation(HoldAt, false, nullptr, ETeleportType::TeleportPhysics);
	}
	if (UPawnMovementComponent* Move = Pawn->GetMovementComponent())
	{
		Move->Velocity = FVector::ZeroVector;
	}
	if (PC->PlayerCameraManager)
	{
		PC->PlayerCameraManager->UpdateCamera(0.f);
	}
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
		if (!K.Key.IsMouseButton() && FSlateApplication::IsInitialized())
		{
			// a menu that has the keyboard focus (a Slate or UMG widget, not the game viewport) gets the key first,
			// as a player's keyboard gives it (game grader 1.17.0: a menu that reads keys in OnKeyDown); a
			// key it doesn't take goes on to the player controller, as before
			const TSharedPtr<SWidget> Focused = FSlateApplication::Get().GetKeyboardFocusedWidget();
			const TSharedPtr<SViewport> Viewport = GameViewportWidget();
			if (Focused.IsValid() && Focused != StaticCastSharedPtr<SWidget>(Viewport))
			{
				const FKeyEvent Event(K.Key, FModifierKeysState(), 0, false, 0, 0);
				const bool bHandled = K.bPress ? FSlateApplication::Get().ProcessKeyDownEvent(Event)
					: FSlateApplication::Get().ProcessKeyUpEvent(Event);
				UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: %s %s to the focused %s through Slate: %s"), *K.Key.ToString(),
					K.bPress ? TEXT("press") : TEXT("release"), *Focused->GetTypeAsString(),
					bHandled ? TEXT("handled") : TEXT("unhandled, sent to the player controller"));
				if (bHandled)
				{
					break;
				}
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
			if (ScrolledOrCovered(K, Button->GetCachedWidget(), FString::Printf(TEXT("%s (%s)"), *Button->GetName(), *Button->GetClass()->GetName())))
			{
				break;
			}
			// what a player's click on the button fires: pressed, released, clicked
			Button->OnPressed.Broadcast();
			Button->OnReleased.Broadcast();
			Button->OnClicked.Broadcast();
			UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: clicked button %s (%s)"), *Button->GetName(), *Button->GetClass()->GetName());
		}
		else if (!ClickSlate(K))
		{
			FString Disabled;
			if (TaskProbe::DisabledButtonShown(World, K.Widget, Disabled))
			{
				// a button the game disabled: the click does nothing, as a player's (game grader 1.14.0: a click that
				// says `disabled` has landed on it; any other is a miss, as before)
				UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: button %s matches '%s' but is disabled"), *Disabled, *K.Widget);
				Missed(K, TEXT("click"), K.Widget, FString::Printf(TEXT("a button matches it (%s), shown but disabled: the click does nothing"), *Disabled));
			}
			else
			{
				UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: no visible button matches '%s'"), *K.Widget);
				Missed(K, TEXT("click"), K.Widget, TEXT("no visible button matches it, UMG or Slate"));
			}
		}
		break;
	case EScriptedKind::Cursor:
	{
		FVector2D Absolute;
		if (!TaskProbe::ViewportPoint(K.Cursor.X, K.Cursor.Y, Absolute) || !FSlateApplication::IsInitialized())
		{
			UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: cursor move skipped (no game viewport)"));
			Missed(K, TEXT("cursor"), FString::Printf(TEXT("%.3f, %.3f"), K.Cursor.X, K.Cursor.Y), TEXT("no game viewport"));
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
		// the viewport's own mouse position too (game grader 1.17.0): a game that reads where the mouse is from its
		// player controller (a HUD's hit boxes, a menu painted on a canvas) found it at 0,0 when Slate's move didn't
		// reach the viewport
		if (const UGameViewportClient* GVC = GEngine ? GEngine->GameViewport.Get() : nullptr)
		{
			if (GVC->Viewport)
			{
				const FIntPoint Size = GVC->Viewport->GetSizeXY();
				PC->SetMouseLocation(FMath::RoundToInt(K.Cursor.X * Size.X), FMath::RoundToInt(K.Cursor.Y * Size.Y));
			}
		}
		float MX = -1.f, MY = -1.f;
		const bool bMouse = PC->GetMousePosition(MX, MY);
		UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: cursor to (%.3f, %.3f) = absolute (%.0f, %.0f), Slate %s, player mouse %s (%.0f, %.0f)"),
			K.Cursor.X, K.Cursor.Y, Absolute.X, Absolute.Y, bHandled ? TEXT("handled") : TEXT("unhandled"), bMouse ? TEXT("at") : TEXT("unknown"), MX, MY);
		break;
	}
	case EScriptedKind::Teleport:
		PlacePawn(PC, K.Teleport, K.bHasYaw, K.Yaw);
		if (K.Hold > 0.0 && PC->GetPawn())
		{
			HoldAt = PC->GetPawn()->GetActorLocation();
			HoldUntil = Elapsed + K.Hold;
			UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: holding the pawn at (%.0f, %.0f, %.0f) for %.1f s"), HoldAt.X, HoldAt.Y, HoldAt.Z, K.Hold);
		}
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
		if (K.Hold > 0.0)
		{
			HoldAt = At;
			HoldUntil = Elapsed + K.Hold;
			UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: holding the pawn there for %.1f s"), K.Hold);
		}
		break;
	}
	case EScriptedKind::Shot:
	{
		// with the UI, as the evenly spaced screenshots: what the player sees at that moment (the inputs after it wait
		// until its frame is drawn: NamedShotWaiting)
		const FString File = FString::Printf(TEXT("shot_%s.png"), *K.Shot);
		if (K.When.IsValid())  // its event's: read every frame from now on (Watch)
		{
			Watches.Add(FWatch{static_cast<int32>(&K - Inputs.GetData()), Elapsed});
			UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: screenshot %s waits for its event from %.2f s"), *File, Elapsed);
			break;
		}
		UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: screenshot %s at %.2f s"), *File, Elapsed);
		AskShot(File, static_cast<int32>(&K - Inputs.GetData()));
		break;
	}
	case EScriptedKind::Travel:
		// the clock keeps counting through the load; inputs and samples wait for the new world's player controller
		GEngine->SetClientTravel(World, *K.Map, TRAVEL_Absolute);
		UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: travel to %s at %.2f s"), *K.Map, Elapsed);
		break;
	case EScriptedKind::View:
		PC->SetControlRotation(K.View);
		if (PC->PlayerCameraManager)
		{
			PC->PlayerCameraManager->UpdateCamera(0.f);
		}
		UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: view turned to pitch %.1f yaw %.1f"), K.View.Pitch, K.View.Yaw);
		break;
	case EScriptedKind::Wait:
		bWaiting = true;
		WaitFor = K.Wait;
		WaitGame = 0.0;
		WaitStart = FPlatformTime::Seconds();
		UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: the play's clock holds at %.2f s for %.1f s of real time"), Elapsed, K.Wait);
		break;
	case EScriptedKind::Wheel:
		SendWheel(K);
		break;
	case EScriptedKind::Pin:
	case EScriptedKind::Damage:
	case EScriptedKind::Set:
		Stage(K, World, PC);
		break;
	case EScriptedKind::Touch:
		StartTouch(K, World);
		break;
	case EScriptedKind::Move:
	{
		FMoving M;
		M.Input = static_cast<int32>(&K - Inputs.GetData());
		M.Start = Elapsed;
		Moving.Add(M);
		MoveMouse(Moving.Last());  // all of it now when it isn't spread over time
		break;
	}
	}
	++InputsSent;
}

/** Where a pin sets an actor ahead of the pawn: Front cm along the pawn's facing (plus Offset), at the height above the
 *  ground below it the actor had, facing the pawn. */
static FVector PinSpot(UWorld* World, const APawn* Pawn, const AActor* A, double Front, const FVector& Offset)
{
	const FVector Base = Pawn->GetActorLocation() + Pawn->GetActorForwardVector().GetSafeNormal2D() * Front + FVector(Offset.X, Offset.Y, 0.0);
	auto GroundZ = [World, Pawn, A](const FVector& At, double& OutZ)
	{
		FHitResult Hit;
		FCollisionQueryParams Params(TEXT("TaskProbePin"), false);
		Params.AddIgnoredActor(Pawn);
		Params.AddIgnoredActor(A);
		if (!World->LineTraceSingleByChannel(Hit, At + FVector(0, 0, 500), At - FVector(0, 0, 5000), ECC_Visibility, Params))
		{
			return false;
		}
		OutZ = Hit.ImpactPoint.Z;
		return true;
	};
	double Was = 0.0, Now = 0.0;
	const FVector Here = A->GetActorLocation();
	const double Above = GroundZ(Here, Was) ? Here.Z - Was : Here.Z - Pawn->GetActorLocation().Z;
	const double Z = GroundZ(FVector(Base.X, Base.Y, Pawn->GetActorLocation().Z), Now) ? Now + Above : Pawn->GetActorLocation().Z + Above;
	return FVector(Base.X, Base.Y, Z + Offset.Z);
}

void UTaskProbe::PinActor(const FScriptedKey& K, UWorld* World, APlayerController* PC)
{
	AActor* A = TaskProbe::NearestMatch(World, PC, K.Target);
	if (!A)
	{
		Missed(K, TEXT("pin"), TEXT("select"), TEXT("no actor but the player matches it"));
		return;
	}
	const APawn* Pawn = PC->GetPawn();
	FVector Point;
	if (K.At.IsValid() && !TaskProbe::PointOf(World, PC, K.At, Point))
	{
		Missed(K, TEXT("pin"), TEXT("at"), TEXT("its point doesn't resolve (no actor matches it, or no pawn)"));
		return;
	}
	if ((K.bFront || K.At.IsValid()) && Pawn)
	{
		const FVector At = K.At.IsValid() ? Point + K.Offset : PinSpot(World, Pawn, A, K.Front, K.Offset);
		const FVector Look = Pawn->GetActorLocation() - At;
		FRotator Rot = A->GetActorRotation();
		Rot.Yaw = FMath::RadiansToDegrees(FMath::Atan2(Look.Y, Look.X));
		A->SetActorLocationAndRotation(At, Rot, false, nullptr, ETeleportType::TeleportPhysics);
		if (APawn* Held = Cast<APawn>(A); Held && Held->GetController())
		{
			Held->GetController()->SetControlRotation(Rot);
		}
	}
	FPinned P;
	P.Actor = A;
	P.At = A->GetActorLocation();
	P.Until = Elapsed + K.Hold;
	Pinned.Add(P);
	UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: pinned %s at (%.0f, %.0f, %.0f) for %.1f s"), *A->GetName(), P.At.X, P.At.Y, P.At.Z, K.Hold);
}

void UTaskProbe::Stage(const FScriptedKey& K, UWorld* World, APlayerController* PC)
{
	if (K.Kind == EScriptedKind::Pin)
	{
		PinActor(K, World, PC);
		return;
	}
	if (K.Kind == EScriptedKind::Damage)
	{
		AActor* Target = TaskProbe::NearestMatch(World, PC, K.Target);
		if (!Target)
		{
			Missed(K, TEXT("damage"), TEXT("to"), TEXT("no actor matches it"));
			return;
		}
		// struck from `from`'s nearest match; by default the pawn, or the nearest other pawn when the pawn is struck
		AActor* From = nullptr;
		if (K.From.IsValid())
		{
			From = TaskProbe::NearestMatch(World, PC, K.From);
		}
		else if (Target == PC->GetPawn())
		{
			const TSharedRef<FJsonObject> Pawns = MakeShared<FJsonObject>();
			Pawns->SetStringField(TEXT("class"), TEXT("Pawn"));
			From = TaskProbe::NearestMatch(World, PC, Pawns);
		}
		else
		{
			From = PC->GetPawn();
		}
		const FVector There = Target->GetActorLocation();
		const FVector Dir = From ? (There - From->GetActorLocation()).GetSafeNormal() : -Target->GetActorForwardVector();
		FHitResult Hit(Target, Cast<UPrimitiveComponent>(Target->GetRootComponent()), There, -Dir);
		Hit.ImpactPoint = There;
		Hit.TraceStart = There - Dir * 100.0;
		Hit.TraceEnd = There;
		const APawn* Striker = Cast<APawn>(From);
		const float Taken = UGameplayStatics::ApplyPointDamage(Target, (float)K.Amount, Dir, Hit, Striker ? Striker->GetController() : nullptr, From,
			UDamageType::StaticClass());
		TaskProbe::NoteDamage(Target, Taken);
		UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: %.1f damage to %s from %s: it took %.1f"), K.Amount, *Target->GetName(),
			From ? *From->GetName() : TEXT("nothing"), Taken);
		return;
	}
	TArray<AActor*> All;
	AActor* Nearest = TaskProbe::NearestMatch(World, PC, K.Target, &All);
	const TCHAR* Kind = TEXT("set");
	if (!Nearest)
	{
		Missed(K, Kind, K.Path, TEXT("no actor matches its select"));
		return;
	}
	if (!K.bAll)
	{
		All = {Nearest};
	}
	int32 Done = 0;
	FString Why;
	for (AActor* A : All)
	{
		FString Failed;
		const bool bTook = TaskProbe::WriteProp(A, K.Path, K.Value, Failed);
		Done += bTook ? 1 : 0;
		Why = bTook ? Why : Failed;
		UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: %s %s on %s: %s"), Kind, *K.Path, *A->GetName(),
			bTook ? TEXT("done") : *Failed);
	}
	if (Done < All.Num())
	{
		Missed(K, Kind, K.Path, FString::Printf(TEXT("%d of %d actors didn't take it: %s"), All.Num() - Done, All.Num(), *Why));
	}
}

void UTaskProbe::Missed(const FScriptedKey& K, const TCHAR* Kind, const FString& Target, const FString& Why)
{
	const TSharedRef<FJsonObject> Row = MakeShared<FJsonObject>();
	Row->SetNumberField(TEXT("t"), K.Time);
	Row->SetStringField(TEXT("kind"), Kind);
	Row->SetStringField(TEXT("target"), Target.Left(200));
	Row->SetStringField(TEXT("why"), Why.Left(1000));
	InputsMissed.Add(MakeShared<FJsonValueObject>(Row));
	UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: %s %s at %.2f s did not land: %s"), Kind, *Target, K.Time, *Why);
}

void UTaskProbe::AskShot(const FString& File, int32 Input)
{
	// One capture serves every shot asked before the viewport next draws: the engine holds one screenshot request
	// (FScreenshotRequest keeps a single filename, so a second request before the draw replaces the first, whose file
	// is never written), and every shot is taken the same way (with the UI), so they would all be the same picture. The
	// first asked is the capture, a `shot` input's ahead of an evenly spaced one (inputs are sent before the evenly
	// spaced shot of their tick); the others are copies of its file (Finish), each listed under its own name.
	ShotTaken();
	if (ShotFrame.IsEmpty())
	{
		FScreenshotRequest::RequestScreenshot(FPaths::Combine(OutDir, File), true, false);
		ShotFrame = File;
	}
	FShotAsked Entry;
	Entry.File = File;
	Entry.Source = ShotFrame;
	Entry.Input = Input;
	Entry.At = Elapsed;
	ShotsAsked.Add(Entry);
	if (ShotFrame != File)
	{
		UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: screenshot %s is the same frame as %s"), *File, *ShotFrame);
	}
}

void UTaskProbe::ShotTaken()
{
	// the engine takes the request when the game viewport next draws, then clears it
	if (!ShotFrame.IsEmpty() && !FScreenshotRequest::IsScreenshotRequested())
	{
		ShotFrame.Reset();
	}
}

bool UTaskProbe::NamedShotWaiting() const
{
	// a `shot` input whose frame isn't drawn yet: the inputs after it wait, so a travel, a view turn or a teleport at the
	// same time never shows in the picture asked for before it; a second of play at most (a viewport that doesn't draw
	// never holds the rest of the play)
	return !ShotFrame.IsEmpty() && ShotsAsked.ContainsByPredicate([this](const FShotAsked& S)
		{ return S.Input != INDEX_NONE && S.Source == ShotFrame && Elapsed - S.At < 1.0; });
}

bool UTaskProbe::ShotWritten(const FString& File) const
{
	return IFileManager::Get().FileSize(*FPaths::Combine(OutDir, File)) > 0;
}

bool UTaskProbe::ShotsWritten() const
{
	return ShotFrame.IsEmpty() && !ShotsAsked.ContainsByPredicate([this](const FShotAsked& S) { return !ShotWritten(S.Source); });
}

bool UTaskProbe::ClickSlate(const FScriptedKey& K)
{
	// no UMG button matches: a Slate button (SNew(SButton) in a game's own UI) named by its text, tag or type, pressed
	// as a player's click at its centre would press it (the pointer moves there, so it is hovered, then the left button
	// goes down and up through Slate: its OnClicked fires as for a player)
	FVector2D At;
	FString Label;
	if (!FSlateApplication::IsInitialized())
	{
		return false;
	}
	const TSharedPtr<SWidget> Button = TaskProbe::FindSlateButton(K.Widget, At, Label);
	if (!Button.IsValid())
	{
		return false;
	}
	if (ScrolledOrCovered(K, Button, Label))
	{
		return true;
	}
	const TSharedPtr<SViewport> Viewport = GameViewportWidget();
	const bool bViewportCaptured = Viewport.IsValid() && Viewport->HasMouseCapture();
	FSlateApplication& Slate = FSlateApplication::Get();
	const TSet<FKey> NoButtons;
	TSet<FKey> Left;
	Left.Add(EKeys::LeftMouseButton);
	const FVector2D From = bCursorSet ? CursorAbsolute : At;
	Slate.ProcessMouseMoveEvent(FPointerEvent(FSlateApplication::CursorPointerIndex, At, From, NoButtons, EKeys::Invalid, 0.f, FModifierKeysState()));
	const bool bDown = Slate.ProcessMouseButtonDownEvent(TSharedPtr<FGenericWindow>(),
		FPointerEvent(FSlateApplication::CursorPointerIndex, At, At, Left, EKeys::LeftMouseButton, 0.f, FModifierKeysState()));
	// it took the press: a button pressed the default way (down and up) holds the mouse from the press to the release;
	// one that clicks on the press alone handled it while hovered (the pointer reached it, nothing covering it)
	const bool bPressed = Button->HasMouseCapture() || (bDown && Button->IsHovered());
	const bool bUp = Slate.ProcessMouseButtonUpEvent(FPointerEvent(FSlateApplication::CursorPointerIndex, At, At, NoButtons, EKeys::LeftMouseButton, 0.f, FModifierKeysState()));
	CursorAbsolute = At;
	bCursorSet = true;
	UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: clicked Slate button %s at (%.0f, %.0f): press %s, release %s"), *Label, At.X, At.Y,
		bDown ? TEXT("handled") : TEXT("unhandled"), bUp ? TEXT("handled") : TEXT("unhandled"));
	if (!bPressed)
	{
		Missed(K, TEXT("click"), K.Widget, FString::Printf(TEXT("Slate button (%s) found, but it didn't take the press at its centre%s"), *Label,
			bViewportCaptured ? TEXT(" (the game viewport holds the mouse captured)") : TEXT(" (covered, or Slate found no window there)")));
	}
	return true;
}

bool UTaskProbe::ScrolledOrCovered(const FScriptedKey& K, const TSharedPtr<SWidget>& Control, const FString& Label)
{
	// scrolled out of its own scroll areas' view: scrolled to, as a player does, and clicked in the next frame once the
	// layout has followed (game grader 1.16.0); once only
	FString Areas;
	if (!K.bScrolled && TaskProbe::ScrollIntoView(Control, Areas))
	{
		FScriptedKey Next = K;
		Next.bScrolled = true;
		Again.Add(Next);
		UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: scrolled %s to show %s for the click on '%s'"), *Areas, *Label, *K.Widget);
		return true;
	}
	// a press at its centre lands on something else drawn over it: nothing is pressed
	FString Over;
	if (TaskProbe::CoverAt(Control, Over) == 1)
	{
		UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: %s matches '%s', but %s is over it: not clicked"), *Label, *K.Widget, *Over);
		Missed(K, TEXT("click"), K.Widget, TEXT("covered by another control"));
		return true;
	}
	return false;
}

void UTaskProbe::Watch(UWorld* World, APlayerController* PC, bool bEnded)
{
	TArray<FWatch> Left;
	for (const FWatch& W : Watches)
	{
		const FScriptedKey& K = Inputs[W.Input];
		const TSharedPtr<FJsonObject>& E = K.When;
		double Within = 0.0;
		const bool bWithin = E->TryGetNumberField(TEXT("within"), Within);
		if (bEnded || (bWithin && Elapsed > W.Start + Within + 1e-6))
		{
			Missed(K, TEXT("shot_when"), K.Shot, TEXT("its event never happened"));
			continue;
		}
		const TSharedPtr<FJsonObject>* Query = nullptr;
		FString Field, Of, Match, Op;
		double Value = 0.0, Read = 0.0;
		E->TryGetObjectField(TEXT("query"), Query);
		E->TryGetStringField(TEXT("field"), Field);
		E->TryGetStringField(TEXT("of"), Of);
		E->TryGetStringField(TEXT("match"), Match);
		E->TryGetStringField(TEXT("op"), Op);
		E->TryGetNumberField(TEXT("value"), Value);
		bool bHolds = false;
		if (Watcher && Query && Watcher->ReadNow(*Query, Field, Of, Match, World, PC, Read))
		{
			const bool bEqual = FMath::IsNearlyEqual(Read, Value, 1e-9);
			bHolds = Op == TEXT(">") ? Read > Value : Op == TEXT(">=") ? Read >= Value : Op == TEXT("<") ? Read < Value
				: Op == TEXT("<=") ? Read <= Value : Op == TEXT("==") ? bEqual : Op == TEXT("!=") ? !bEqual : false;
		}
		if (bHolds)
		{
			const FString File = FString::Printf(TEXT("shot_%s.png"), *K.Shot);
			UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: screenshot %s at %.2f s: its event came (%s reads %g)"), *File, Elapsed, *Field, Read);
			AskShot(File, W.Input);
			continue;
		}
		Left.Add(W);
	}
	Watches = MoveTemp(Left);
}

void UTaskProbe::SendWheel(const FScriptedKey& K)
{
	// a player's wheel at the cursor (the viewport's centre before any cursor move), one event per notch: Slate gives it to
	// the UI under the cursor or the game viewport, which sends the engine's MouseWheelAxis and a MouseScrollUp or
	// MouseScrollDown press and release, so legacy mappings and Enhanced Input alike receive it
	const FString Target = FString::Printf(TEXT("%+d"), K.Wheel);
	const TSharedPtr<SViewport> Viewport = GameViewportWidget();
	FVector2D At = CursorAbsolute;
	if (!FSlateApplication::IsInitialized() || !Viewport.IsValid() || (!bCursorSet && !TaskProbe::ViewportPoint(0.5, 0.5, At)))
	{
		Missed(K, TEXT("wheel"), Target, TEXT("no game viewport"));
		return;
	}
	const TSet<FKey> NoButtons;
	int32 Handled = 0;
	for (int32 i = 0; i < FMath::Abs(K.Wheel); ++i)
	{
		const FPointerEvent Event(FSlateApplication::CursorPointerIndex, At, At, NoButtons, EKeys::Invalid, K.Wheel > 0 ? 1.f : -1.f, FModifierKeysState());
		Handled += FSlateApplication::Get().ProcessMouseWheelOrGestureEvent(Event, nullptr) ? 1 : 0;
	}
	UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: wheel %s at (%.0f, %.0f) through Slate, %d of %d notches handled"), *Target, At.X, At.Y,
		Handled, FMath::Abs(K.Wheel));
	if (Handled == 0)
	{
		// nothing took it: no window under the cursor for Slate, or nothing there (UI or viewport) handles a wheel
		Missed(K, TEXT("wheel"), Target, TEXT("Slate handled none of its notches at the cursor"));
	}
}

void UTaskProbe::MoveMouse(FMoving& M)
{
	// a player's mouse moving: each tick the part due by then, as one Slate mouse move. While the game viewport holds the
	// mouse captured (mouse look) the cursor stays put, as the OS holds a captured one, and the viewport turns the move's
	// delta into the engine's MouseX and MouseY (and Mouse2D, their pair); otherwise the cursor moves over the game, kept
	// inside the viewport, and no mouse axes are sent: a miss for a play that asks for mouse movement
	const FScriptedKey& K = Inputs[M.Input];
	const double Frac = K.Over > 0.0 ? FMath::Clamp((Elapsed - M.Start) / K.Over, 0.0, 1.0) : 1.0;
	M.bFinished = Frac >= 1.0;
	const FVector2D Step = K.Move * Frac - M.Sent;
	if (Step.IsNearlyZero(1e-4))
	{
		return;
	}
	M.Sent += Step;
	const FString Target = FString::Printf(TEXT("%.0f, %.0f"), K.Move.X, K.Move.Y);
	const TSharedPtr<SViewport> Viewport = GameViewportWidget();
	FVector2D From = CursorAbsolute, Min, Max;
	if (!FSlateApplication::IsInitialized() || !Viewport.IsValid() || (!bCursorSet && !TaskProbe::ViewportPoint(0.5, 0.5, From))
		|| !TaskProbe::ViewportPoint(0.0, 0.0, Min) || !TaskProbe::ViewportPoint(1.0, 1.0, Max))
	{
		if (!M.bMissed)
		{
			M.bMissed = true;
			Missed(K, TEXT("move"), Target, TEXT("no game viewport"));
		}
		return;
	}
	const bool bCaptured = Viewport->HasMouseCapture();
	FVector2D To = From + Step;
	if (!bCaptured)
	{
		To = FVector2D(FMath::Clamp(To.X, Min.X, Max.X - 1.0), FMath::Clamp(To.Y, Min.Y, Max.Y - 1.0));
	}
	const TSet<FKey> NoButtons;
	FSlateApplication::Get().ProcessMouseMoveEvent(FPointerEvent(FSlateApplication::CursorPointerIndex, To, From, NoButtons, EKeys::Invalid, 0.f, FModifierKeysState()));
	if (!bCaptured)
	{
		CursorAbsolute = To;
		bCursorSet = true;
		if (!M.bMissed)
		{
			M.bMissed = true;
			Missed(K, TEXT("move"), Target, TEXT("the game viewport doesn't hold the mouse captured: the cursor moved, no mouse axes were sent"));
		}
	}
}

void UTaskProbe::StartTouch(const FScriptedKey& K, UWorld* World)
{
	// a finger going down: its spots are resolved now (a widget's centre as it is laid out at this moment), then it is
	// sent a part each tick (MoveTouch) until it lifts
	const TCHAR* Kind = K.bDrag ? TEXT("drag") : TEXT("tap");
	auto Named = [](const FTouchSpot& S) { return S.bWidget ? S.Widget : FString::Printf(TEXT("%.3f, %.3f"), S.At.X, S.At.Y); };
	const FString Target = Named(K.Spots[0]);
	if (!FSlateApplication::IsInitialized())
	{
		Missed(K, Kind, Target, TEXT("no game viewport"));
		return;
	}
	if (Touching.ContainsByPredicate([&](const FTouching& T) { return !T.bFinished && Inputs[T.Input].Finger == K.Finger; }))
	{
		Missed(K, Kind, Target, FString::Printf(TEXT("finger %d is still down from an earlier touch"), K.Finger));
		return;
	}
	FTouching T;
	T.Input = static_cast<int32>(&K - Inputs.GetData());
	T.Start = Elapsed;
	for (const FTouchSpot& S : K.Spots)
	{
		FVector2D At;
		FString Label;
		if (S.bWidget ? !TaskProbe::WidgetCentre(World, S.Widget, At, Label) : !TaskProbe::ViewportPoint(S.At.X, S.At.Y, At))
		{
			Missed(K, Kind, Named(S), S.bWidget ? TEXT("no visible widget matches it, UMG or a Slate button") : TEXT("no game viewport"));
			return;
		}
		T.Points.Add(At);
	}
	Touching.Add(T);
	MoveTouch(Touching.Last());
}

void UTaskProbe::MoveTouch(FTouching& T)
{
	// one finger's part due by now, through Slate as a touch screen's events are (the application's own touch entry
	// points): down at its first spot, a move when its place changed, up once its path and its hold are over (never in
	// the tick it went down, so a tap is a press in one frame and a release in the next)
	const FScriptedKey& K = Inputs[T.Input];
	FSlateApplication& Slate = FSlateApplication::Get();
	const FInputDeviceId Device = IPlatformInputDeviceMapper::Get().GetDefaultInputDevice();
	const FPlatformUserId User = IPlatformInputDeviceMapper::Get().GetPrimaryPlatformUser();
	const TCHAR* Kind = K.bDrag ? TEXT("drag") : TEXT("tap");
	const double Since = Elapsed - T.Start;
	if (!T.bDown)
	{
		T.bDown = true;
		T.Last = T.Points[0];
		const bool bSent = Slate.OnTouchStarted(TSharedPtr<FGenericWindow>(), T.Last, 1.f, K.Finger, User, Device);
		UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: %s finger %d down at absolute (%.0f, %.0f)%s"), Kind, K.Finger, T.Last.X, T.Last.Y,
			bSent ? TEXT("") : TEXT(": Slate refused it"));
		if (!bSent)
		{
			T.bMissed = T.bFinished = true;
			Missed(K, Kind, FString::Printf(TEXT("finger %d"), K.Finger), TEXT("Slate refused the touch"));
		}
		return;
	}
	FVector2D To = T.Points.Last();
	if (T.Points.Num() > 1 && K.Over > 0.0 && Since < K.Over)
	{
		const double Along = FMath::Clamp(Since / K.Over, 0.0, 1.0) * (T.Points.Num() - 1);
		const int32 i = FMath::Min(FMath::FloorToInt32(Along), T.Points.Num() - 2);
		To = FMath::Lerp(T.Points[i], T.Points[i + 1], Along - i);
	}
	if (!To.Equals(T.Last, 0.01))
	{
		if (!Slate.OnTouchMoved(To, 1.f, K.Finger, User, Device) && !T.bMissed)
		{
			T.bMissed = true;
			Missed(K, Kind, FString::Printf(TEXT("finger %d"), K.Finger), TEXT("Slate has no such finger down: its move was not sent"));
		}
		T.Last = To;
	}
	if (Since >= (T.Points.Num() > 1 ? K.Over : 0.0) + K.Press)
	{
		Slate.OnTouchEnded(T.Last, K.Finger, User, Device);
		T.bFinished = true;
		UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: %s finger %d up at absolute (%.0f, %.0f) after %.2f s"), Kind, K.Finger, T.Last.X, T.Last.Y, Since);
	}
}

void UTaskProbe::LiftTouches()
{
	// the play is over: no finger stays down in Slate
	if (!FSlateApplication::IsInitialized())
	{
		return;
	}
	for (FTouching& T : Touching)
	{
		if (T.bDown && !T.bFinished)
		{
			FSlateApplication::Get().OnTouchEnded(T.Last, Inputs[T.Input].Finger, IPlatformInputDeviceMapper::Get().GetPrimaryPlatformUser(),
				IPlatformInputDeviceMapper::Get().GetDefaultInputDevice());
			T.bFinished = true;
		}
	}
}

bool UTaskProbe::Tick(float DeltaTime)
{
	if (bDone)
	{
		return false;
	}
#if PLATFORM_LINUX && WITH_EDITOR
	// A play on Linux runs in the editor's -game on a fresh shader cache: shader compiles still pending are finished each tick, which 5.7.4's synchronous mode
	// would otherwise assert on
	if (GShaderCompilingManager && GShaderCompilingManager->IsCompiling())
	{
		GShaderCompilingManager->FinishAllCompilation();
	}
#endif
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
	ShotTaken();
	if (bEnding)
	{
		// the play's time is up: the clock and the samples stand still while the screenshots asked for are taken and
		// written (the engine may write a file after the frame it took it on), a few seconds of real time at most
		if (!ShotsWritten() && FPlatformTime::Seconds() - ShotsWaitStart < 5.0)
		{
			return true;
		}
		Finish(TEXT("time"));
		FPlatformMisc::RequestExit(false);
		return false;
	}
	if (bWaiting)
	{
		// a wait: the game runs on, paced to real time (a frame ahead of the wall clock sleeps till it catches up), and
		// the play's clock holds until both its seconds of real time and of game time have passed
		WaitGame += DeltaTime;
		const double Real = FPlatformTime::Seconds() - WaitStart;
		if (WaitGame > Real)
		{
			FPlatformProcess::Sleep((float)FMath::Min(WaitGame - Real, 0.25));
		}
		if (Queries)
		{
			Queries->Frame(DeltaTime, World);
			Queries->Listen(World, Elapsed);
		}
		if (WaitGame >= WaitFor && FPlatformTime::Seconds() - WaitStart >= WaitFor)
		{
			bWaiting = false;
			UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: the wait is over (%.1f s of game time); the play's clock goes on from %.2f s"), WaitGame, Elapsed);
		}
		return true;
	}
	Elapsed += DeltaTime;
	if (Queries)
	{
		Queries->Frame(DeltaTime, World);
		Queries->Listen(World, Elapsed);
	}
	APlayerController* PC = World && World->HasBegunPlay() ? World->GetFirstPlayerController() : nullptr;

	// inputs wait for a player controller (e.g. during a map travel)
	// (a wait holds the inputs after it until it is over; a named shot holds them until its frame is drawn, but for
	// another named shot, which is the same frame)
	// a click whose control was scrolled into view last frame is made now, before any later input (game grader 1.16.0)
	if (PC && !bWaiting && Again.Num() > 0)
	{
		const TArray<FScriptedKey> Now = MoveTemp(Again);
		Again.Reset();
		for (const FScriptedKey& K : Now)
		{
			SendInput(K, World, PC);
		}
	}
	while (PC && !bWaiting && Again.Num() == 0 && NextInput < Inputs.Num() && Inputs[NextInput].Time <= Elapsed
		&& (Inputs[NextInput].Kind == EScriptedKind::Shot || !NamedShotWaiting()))
	{
		SendInput(Inputs[NextInput++], World, PC);
	}
	if (PC && Watches.Num() > 0)
	{
		Watch(World, PC, false);
	}
	// mouse movements spread over time: the part due by now
	for (FMoving& M : Moving)
	{
		if (!M.bFinished)
		{
			MoveMouse(M);
		}
	}
	Moving.RemoveAll([](const FMoving& M) { return M.bFinished; });
	// fingers on the screen: the part due by now (one that went down this tick was sent its press already)
	for (FTouching& T : Touching)
	{
		if (!T.bFinished && T.Start < Elapsed)
		{
			MoveTouch(T);
		}
	}
	Touching.RemoveAll([](const FTouching& T) { return T.bFinished; });

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
		AskShot(FString::Printf(TEXT("shot_%02d.png"), ShotsTaken), INDEX_NONE);
		++ShotsTaken;
	}

	if (Elapsed >= Seconds + 0.5)
	{
		// a screen sample reads the frame drawn after it: the last one waits for that frame (a few frames at most)
		if (Queries && Queries->WaitsForFrame() && FramesWaited++ < 5)
		{
			return true;
		}
		if (!ShotsWritten())
		{
			bEnding = true;
			ShotsWaitStart = FPlatformTime::Seconds();
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
	LiftTouches();
	Watch(nullptr, nullptr, true);
	for (const FScriptedKey& K : Again)
	{
		Missed(K, TEXT("click"), K.Widget, TEXT("its scroll area was scrolled to it, but the play ended before the press"));
	}
	Again.Reset();
	UGameInstance* GI = GetGameInstance();
	UWorld* World = GI ? GI->GetWorld() : nullptr;
	const TSharedRef<FJsonObject> Out = MakeShared<FJsonObject>();
	Out->SetStringField(TEXT("format"), TEXT("game-probe/1"));
	Out->SetStringField(TEXT("ended"), Reason);
	Out->SetNumberField(TEXT("seconds"), Elapsed);
	Out->SetStringField(TEXT("map"), World ? World->GetMapName() : FString());
	Out->SetNumberField(TEXT("inputs_sent"), InputsSent);
	// only the screenshots on disk, in the order asked for: a judge is never told of a picture that doesn't exist. A
	// copy of a frame's capture is written now; a `shot` input's picture that isn't on disk is listed as an input that
	// didn't land, an evenly spaced one's only logged
	TArray<TSharedPtr<FJsonValue>> Written;
	ShotTaken();
	for (const FShotAsked& S : ShotsAsked)
	{
		if (S.File != S.Source && ShotWritten(S.Source) && !ShotWritten(S.File))
		{
			IFileManager::Get().Copy(*FPaths::Combine(OutDir, S.File), *FPaths::Combine(OutDir, S.Source));
		}
		if (ShotWritten(S.File))
		{
			Written.Add(MakeShared<FJsonValueString>(S.File));
			continue;
		}
		const TCHAR* Why = S.Source == ShotFrame ? TEXT("the play ended before the engine took it")
			: ShotWritten(S.Source) ? TEXT("its copy of the frame's capture could not be written")
			: TEXT("the engine took it, but wrote no file");
		if (S.Input != INDEX_NONE)
		{
			Missed(Inputs[S.Input], TEXT("shot"), S.File, Why);
		}
		else
		{
			UE_LOG(LogTaskProbe, Log, TEXT("TaskProbe: screenshot %s left out: %s"), *S.File, Why);
		}
	}
	// every input that didn't land (a click no button took, a wheel step or mouse movement no game viewport received):
	// always written, so a grader tells "none missed" from a plugin that didn't say
	Out->SetArrayField(TEXT("inputs_missed"), InputsMissed);
	Out->SetArrayField(TEXT("screenshots"), Written);
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
