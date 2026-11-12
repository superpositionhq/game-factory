#include "TaskProbeQueries.h"

#include "ActiveSound.h"
#include "AIController.h"
#include "Animation/AnimInstance.h"
#include "Audio.h"
#include "AudioDevice.h"
#include "AudioThread.h"
#include "BehaviorTree/BlackboardComponent.h"
#include "BehaviorTree/BlackboardData.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Bool.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Class.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Enum.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Float.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Int.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Name.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_NativeEnum.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Object.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Rotator.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_String.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Vector.h"
#include "BatchedElements.h"
#include "Blueprint/UserWidget.h"
#include "Blueprint/WidgetTree.h"
#include "Camera/PlayerCameraManager.h"
#include "CanvasBatchedElementRenderItem.h"
#include "CanvasTypes.h"
#include "CollisionQueryParams.h"
#include "Components/ActorComponent.h"
#include "Components/Button.h"
#include "Components/DecalComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/Image.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/LightComponent.h"
#include "Components/LocalLightComponent.h"
#include "Components/MeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/ProgressBar.h"
#include "Components/RectLightComponent.h"
#include "Components/RichTextBlock.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/SkinnedMeshComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/SpotLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextBlock.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/Font.h"
#include "Engine/GameViewportClient.h"
#include "Engine/HitResult.h"
#include "Engine/Scene.h"
#include "Engine/SkinnedAsset.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture.h"
#include "Engine/TextureRenderTarget2D.h"
#include "EngineFontServices.h"
#include "Debugging/SlateDebugging.h"
#include "EngineUtils.h"
#include "Framework/Application/SlateApplication.h"
#include "Fonts/FontCache.h"
#include "Fonts/FontMeasure.h"
#include "GameFramework/DamageType.h"
#include "GameFramework/HUD.h"
#include "GameFramework/WorldSettings.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "GlobalRenderResources.h"
#include "Interfaces/Interface_PostProcessVolume.h"
#include "Kismet/GameplayStatics.h"
#include "Internationalization/Regex.h"
#include "Materials/Material.h"
#include "Materials/MaterialExpressionAbs.h"
#include "Materials/MaterialExpressionAdd.h"
#include "Materials/MaterialExpressionAppendVector.h"
#include "Materials/MaterialExpressionBlendMaterialAttributes.h"
#include "Materials/MaterialExpressionClamp.h"
#include "Materials/MaterialExpressionCollectionParameter.h"
#include "Materials/MaterialExpressionComponentMask.h"
#include "Materials/MaterialExpressionConstant.h"
#include "Materials/MaterialExpressionConstant2Vector.h"
#include "Materials/MaterialExpressionConstant3Vector.h"
#include "Materials/MaterialExpressionConstant4Vector.h"
#include "Materials/MaterialExpressionCosine.h"
#include "Materials/MaterialExpressionDivide.h"
#include "Materials/MaterialExpressionFunctionInput.h"
#include "Materials/MaterialExpressionFunctionOutput.h"
#include "Materials/MaterialExpressionLinearInterpolate.h"
#include "Materials/MaterialExpressionMakeMaterialAttributes.h"
#include "Materials/MaterialExpressionMaterialFunctionCall.h"
#include "Materials/MaterialExpressionMax.h"
#include "Materials/MaterialExpressionMin.h"
#include "Materials/MaterialExpressionMultiply.h"
#include "Materials/MaterialExpressionNamedReroute.h"
#include "Materials/MaterialExpressionOneMinus.h"
#include "Materials/MaterialExpressionPower.h"
#include "Materials/MaterialExpressionReroute.h"
#include "Materials/MaterialExpressionSaturate.h"
#include "Materials/MaterialExpressionScalarParameter.h"
#include "Materials/MaterialExpressionSine.h"
#include "Materials/MaterialExpressionStaticBoolParameter.h"
#include "Materials/MaterialExpressionStaticSwitch.h"
#include "Materials/MaterialExpressionStaticSwitchParameter.h"
#include "Materials/MaterialExpressionSubstrate.h"
#include "Materials/MaterialExpressionSubtract.h"
#include "Materials/MaterialExpressionVectorParameter.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialParameterCollectionInstance.h"
#include "MaterialShared.h"
#include "Misc/App.h"
#include "Misc/FileHelper.h"
#include "Particles/ParticleSystemComponent.h"
#include "PhysicsEngine/BodyInstance.h"
#include "Rendering/SkeletalMeshLODRenderData.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Rendering/DrawElements.h"
#include "Rendering/SlateRenderer.h"
#include "SceneInterface.h"
#include "SceneView.h"
#include "SceneViewExtension.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundClass.h"
#include "TextureResource.h"
#include "Textures/SlateShaderResource.h"
#include "Types/ReflectionMetadata.h"
#include "UObject/ObjectKey.h"
#include "UObject/StrongObjectPtr.h"
#include "UObject/UObjectIterator.h"
#include "UObject/UnrealType.h"
#include "UnrealClient.h"
#include "Widgets/Colors/SColorBlock.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Input/SEditableText.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Notifications/SProgressBar.h"
#include "Widgets/SViewport.h"
#include "Widgets/SWindow.h"
#include "Widgets/Text/SMultiLineEditableText.h"
#include "Widgets/Text/SRichTextBlock.h"
#include "Widgets/Text/STextBlock.h"

namespace TaskProbe
{
static constexpr int32 MaxRows = 200;     // rows per sample of one query
static constexpr int32 MaxQueries = 256;  // queries per play
static constexpr double TraceLength = 200000.0;  // cm, toward a directional light or the sky
static constexpr double AudibleVolume = 0.001;  // audio: a sound at least this loud at the listener (-60 dB) is audible
static constexpr int32 MaxSoundStarts = 8192;  // audio: sounds followed from their start, per play
static constexpr int32 MaxStartRows = 64;  // audio: starts listed per sample (its starts_total counts them all)
static constexpr float FreshPlayback = 0.5f;  // audio: a sound first seen this far into its playback (s) was playing already

static TSharedPtr<FJsonValue> Null() { return MakeShared<FJsonValueNull>(); }
static TSharedPtr<FJsonValue> Num(double V)
{
	if (!FMath::IsFinite(V))
	{
		return Null();
	}
	return MakeShared<FJsonValueNumber>(V);
}
static TSharedPtr<FJsonValue> Str(const FString& S) { return MakeShared<FJsonValueString>(S); }
static TSharedPtr<FJsonValue> Arr(std::initializer_list<double> Values)
{
	TArray<TSharedPtr<FJsonValue>> Out;
	for (const double V : Values)
	{
		Out.Add(Num(V));
	}
	return MakeShared<FJsonValueArray>(Out);
}
static TSharedPtr<FJsonValue> V4(const FVector4& V) { return Arr({V.X, V.Y, V.Z, V.W}); }

/** Every match's numeric value of one field, summed up when more matched than the rows hold ("full"), so a count, a sum,
 *  a min or a max over a selection is never cut at the rows cap. */
struct FFull
{
	int64 N = 0;
	int64 NonZero = 0;
	double Sum = 0.0;
	double Min = 0.0;
	double Max = 0.0;

	void Add(const TSharedPtr<FJsonValue>& V)
	{
		if (!V.IsValid() || V->Type != EJson::Number)
		{
			return;  // null, a string (read through match) or anything else: rows only
		}
		const double X = V->AsNumber();
		Min = N ? FMath::Min(Min, X) : X;
		Max = N ? FMath::Max(Max, X) : X;
		Sum += X;
		NonZero += X != 0.0 ? 1 : 0;
		++N;
	}
};

/** "total" when more matched than the rows hold, and "full" with each field's FFull. */
static void SetTotal(FJsonObject& Out, int32 Total, int32 Rows, const TArray<FString>& Fields, const TMap<FString, FFull>& Full)
{
	if (Total <= Rows)
	{
		return;
	}
	Out.SetNumberField(TEXT("total"), Total);
	const TSharedRef<FJsonObject> All = MakeShared<FJsonObject>();
	for (const FString& F : Fields)
	{
		const FFull* Found = Full.Find(F);
		if (!Found)
		{
			continue;
		}
		const TSharedRef<FJsonObject> O = MakeShared<FJsonObject>();
		O->SetNumberField(TEXT("n"), (double)Found->N);
		O->SetNumberField(TEXT("nonzero"), (double)Found->NonZero);
		O->SetField(TEXT("sum"), Num(Found->Sum));
		O->SetField(TEXT("min"), Found->N ? Num(Found->Min) : Null());
		O->SetField(TEXT("max"), Found->N ? Num(Found->Max) : Null());
		All->SetObjectField(F, O);
	}
	Out.SetObjectField(TEXT("full"), All);
}
static TSharedPtr<FJsonValue> Rgb(const FLinearColor& C) { return Arr({C.R, C.G, C.B}); }

/** A class or any parent class by name without prefix letters (SCCastlePiece), with them (ASCCastlePiece), or a
 *  Blueprint class by its asset name (BP_Wall_C, or BP_Wall). Empty matches everything. */
static bool ClassMatches(const UClass* C, const FString& Want)
{
	if (Want.IsEmpty())
	{
		return true;
	}
	for (; C; C = C->GetSuperClass())
	{
		const FString N = C->GetName();
		if (N.Equals(Want, ESearchCase::IgnoreCase) || (FString(C->GetPrefixCPP()) + N).Equals(Want, ESearchCase::IgnoreCase) ||
			N.Equals(Want + TEXT("_C"), ESearchCase::IgnoreCase))
		{
			return true;
		}
	}
	return false;
}

static bool ActorNameMatches(const AActor* A, const FString& Pattern)
{
	if (A->GetName().MatchesWildcard(Pattern))
	{
		return true;
	}
#if WITH_EDITOR
	if (A->GetActorLabel(false).MatchesWildcard(Pattern))
	{
		return true;
	}
#endif
	return false;
}

static bool ReadVec(const TSharedPtr<FJsonObject>& O, const TCHAR* Key, FVector& Out)
{
	const TArray<TSharedPtr<FJsonValue>>* A = nullptr;
	if (!O.IsValid() || !O->TryGetArrayField(Key, A) || A->Num() < 3)
	{
		return false;
	}
	double V[3];
	for (int32 i = 0; i < 3; ++i)
	{
		if (!(*A)[i].IsValid() || !(*A)[i]->TryGetNumber(V[i]))
		{
			return false;
		}
	}
	Out = FVector(V[0], V[1], V[2]);
	return true;
}

/** A select's `near`: within `radius` cm of a point, and optionally inside a height band: z_min and z_max (cm), world
 *  heights, or offsets from the point's own z with z_relative. */
struct FNearSel
{
	TSharedPtr<FJsonObject> Point;  // none: no near; an empty one matches nothing
	double Radius = 0.0;
	bool bZMin = false, bZMax = false, bZRelative = false;
	double ZMin = 0.0, ZMax = 0.0;

	bool IsSet() const { return Point.IsValid(); }
	/** Loc is near Centre (the point resolved): within the radius, and inside the height band when one is given. */
	bool Holds(const FVector& Centre, const FVector& Loc) const
	{
		if (FVector::Dist(Loc, Centre) > Radius)
		{
			return false;
		}
		return InBand(Centre, Loc.Z);
	}
	bool InBand(const FVector& Centre, double Z) const
	{
		const double Base = bZRelative ? Centre.Z : 0.0;
		return !(bZMin && Z < Base + ZMin) && !(bZMax && Z > Base + ZMax);
	}
};

/** An actor select's `has`: a component the actor carries that matches every key given (CarriesComponent). */
struct FHasSel
{
	FString Class;
	bool bLit = false;
	bool bVisible = false;
	bool bSimulating = false;
	bool bMovable = false;
	FNearSel Near;
};

/** An actor select's `where`: a reflected property (a prop: path) compared with a number, boolean or string. */
struct FWhereSel
{
	FString Prop;
	FString Op;
	TSharedPtr<FJsonValue> Value;
};

struct FSel
{
	FString Class, Tag, Name;
	bool bPlayer = false;
	FNearSel Near;
	TSharedPtr<FHasSel> Has;  // only with `has`
	TArray<FWhereSel> Where;  // only with `where`
	bool bNotPlayer = false;  // player: false, anything but the player pawn
};

/** has: the renderer its `lit` reads a mesh with when the material graph can't say (FGlowRender): the query set's while
 *  it samples, teleport_to's own while it picks; none elsewhere (the graph's bound, as without a renderer). */
static FGlowRender* SelectRender = nullptr;

/** A near object, {"point": <Point>, "radius": cm, "z_min", "z_max", "z_relative"}: its point (an empty one, which
 *  matches nothing, when it has none), radius and height band. */
static FNearSel ParseNearObject(const TSharedPtr<FJsonObject>& Near)
{
	FNearSel Out;
	if (!Near.IsValid())
	{
		return Out;
	}
	const TSharedPtr<FJsonObject>* Point = nullptr;
	if (Near->TryGetObjectField(TEXT("point"), Point))
	{
		Out.Point = *Point;
	}
	else
	{
		Out.Point = MakeShared<FJsonObject>();  // a near without a point matches nothing
	}
	Near->TryGetNumberField(TEXT("radius"), Out.Radius);
	Out.bZMin = Near->TryGetNumberField(TEXT("z_min"), Out.ZMin);
	Out.bZMax = Near->TryGetNumberField(TEXT("z_max"), Out.ZMax);
	Near->TryGetBoolField(TEXT("z_relative"), Out.bZRelative);
	return Out;
}

/** O's `near` (ParseNearObject); none when O has no near. */
static FNearSel ParseNear(const TSharedPtr<FJsonObject>& O)
{
	const TSharedPtr<FJsonObject>* Near = nullptr;
	if (O.IsValid() && O->TryGetObjectField(TEXT("near"), Near) && Near->IsValid())
	{
		return ParseNearObject(*Near);
	}
	return FNearSel();
}

static FSel ParseSel(const TSharedPtr<FJsonObject>& O)
{
	FSel S;
	if (!O.IsValid())
	{
		return S;
	}
	O->TryGetStringField(TEXT("class"), S.Class);
	O->TryGetStringField(TEXT("tag"), S.Tag);
	O->TryGetStringField(TEXT("name"), S.Name);
	bool bPlayerField = false;
	if (O->TryGetBoolField(TEXT("player"), bPlayerField))
	{
		S.bPlayer = bPlayerField;
		S.bNotPlayer = !bPlayerField;
	}
	S.Near = ParseNear(O);
	const TSharedPtr<FJsonObject>* Has = nullptr;
	if (O->TryGetObjectField(TEXT("has"), Has) && Has->IsValid())
	{
		S.Has = MakeShared<FHasSel>();
		(*Has)->TryGetStringField(TEXT("class"), S.Has->Class);
		(*Has)->TryGetBoolField(TEXT("lit"), S.Has->bLit);
		(*Has)->TryGetBoolField(TEXT("visible"), S.Has->bVisible);
		(*Has)->TryGetBoolField(TEXT("simulating"), S.Has->bSimulating);
		(*Has)->TryGetBoolField(TEXT("movable"), S.Has->bMovable);
		S.Has->Near = ParseNear(*Has);
	}
	const TArray<TSharedPtr<FJsonValue>>* Where = nullptr;
	if (O->TryGetArrayField(TEXT("where"), Where))
	{
		for (const TSharedPtr<FJsonValue>& W : *Where)
		{
			const TSharedPtr<FJsonObject>* WO = nullptr;
			if (!W.IsValid() || !W->TryGetObject(WO) || !WO->IsValid())
			{
				continue;
			}
			FWhereSel C;
			(*WO)->TryGetStringField(TEXT("prop"), C.Prop);
			(*WO)->TryGetStringField(TEXT("op"), C.Op);
			C.Value = (*WO)->TryGetField(TEXT("value"));
			S.Where.Add(C);
		}
	}
	return S;
}

static APawn* PlayerPawn(APlayerController* PC) { return PC ? PC->GetPawn() : nullptr; }

static bool ResolvePoint(const TSharedPtr<FJsonObject>& P, UWorld* World, APlayerController* PC, int32 Depth, FVector& Out);
static bool CarriesComponent(const AActor* A, const FHasSel& Has, UWorld* World, const FVector& NearP);
static TSharedPtr<FJsonValue> ReadProp(UObject* Root, const FString& Path);

/** A where holds for the actor: its property read as a prop: field reads it (numbers, booleans as 1 or 0, an enum as its
 *  index, strings) compared with the value (a boolean as 1 or 0); a property that doesn't resolve, or a string compared
 *  by order, never holds. */
static bool WhereHolds(AActor* A, const FWhereSel& W)
{
	const TSharedPtr<FJsonValue> Have = ReadProp(A, W.Prop);
	if (!Have.IsValid() || !W.Value.IsValid() || Have->IsNull())
	{
		return false;
	}
	if (W.Value->Type == EJson::String || Have->Type == EJson::String)
	{
		FString L, R;
		if (!Have->TryGetString(L) || !W.Value->TryGetString(R))
		{
			return false;
		}
		return W.Op == TEXT("==") ? L == R : W.Op == TEXT("!=") ? L != R : false;
	}
	double L = 0.0, R = 0.0;
	bool bR = false;
	if (!Have->TryGetNumber(L))
	{
		return false;
	}
	if (W.Value->TryGetBool(bR))
	{
		R = bR ? 1.0 : 0.0;
	}
	else if (!W.Value->TryGetNumber(R))
	{
		return false;
	}
	if (W.Op == TEXT(">")) return L > R;
	if (W.Op == TEXT(">=")) return L >= R;
	if (W.Op == TEXT("<")) return L < R;
	if (W.Op == TEXT("<=")) return L <= R;
	if (W.Op == TEXT("==")) return FMath::IsNearlyEqual(L, R, 1e-6);
	if (W.Op == TEXT("!=")) return !FMath::IsNearlyEqual(L, R, 1e-6);
	return false;
}

/** The actors a selection matches (Out holds at most Limit; Total counts them all). */
static void FindActors(UWorld* World, APlayerController* PC, const FSel& S, int32 Depth, int32 Limit, TArray<AActor*>& Out, int32& Total)
{
	Total = 0;
	if (!World)
	{
		return;
	}
	FVector NearP = FVector::ZeroVector;
	const bool bNear = S.Near.IsSet();
	if (bNear && !ResolvePoint(S.Near.Point, World, PC, Depth + 1, NearP))
	{
		return;
	}
	FVector HasNearP = FVector::ZeroVector;  // has: the point its component must be near
	if (S.Has.IsValid() && S.Has->Near.IsSet() && !ResolvePoint(S.Has->Near.Point, World, PC, Depth + 1, HasNearP))
	{
		return;
	}
	const FName TagName = S.Tag.IsEmpty() ? NAME_None : FName(*S.Tag);
	auto Test = [&](AActor* A)
	{
		if (!IsValid(A) || A->IsActorBeingDestroyed())
		{
			return false;
		}
		if (!S.Class.IsEmpty() && !ClassMatches(A->GetClass(), S.Class))
		{
			return false;
		}
		if (!S.Tag.IsEmpty() && !A->ActorHasTag(TagName))
		{
			return false;
		}
		if (!S.Name.IsEmpty() && !ActorNameMatches(A, S.Name))
		{
			return false;
		}
		if (bNear && !S.Near.Holds(NearP, A->GetActorLocation()))
		{
			return false;
		}
		if (S.Has.IsValid() && !CarriesComponent(A, *S.Has, World, HasNearP))
		{
			return false;
		}
		for (const FWhereSel& W : S.Where)
		{
			if (!WhereHolds(A, W))
			{
				return false;
			}
		}
		if (S.bNotPlayer && A == PlayerPawn(PC))
		{
			return false;
		}
		return true;
	};
	if (S.bPlayer)
	{
		APawn* Pawn = PlayerPawn(PC);
		if (Pawn && Test(Pawn))
		{
			Total = 1;
			if (Limit > 0)
			{
				Out.Add(Pawn);
			}
		}
		return;
	}
	for (TActorIterator<AActor> It(World); It; ++It)
	{
		if (Test(*It))
		{
			++Total;
			if (Out.Num() < Limit)
			{
				Out.Add(*It);
			}
		}
	}
}

/** Point: {"xyz": [x, y, z]}, {"pawn": true, "offset": [...]}, {"camera": true, "forward": cm}, {"actor": <select>, "offset": [...]}. */
static bool ResolvePoint(const TSharedPtr<FJsonObject>& P, UWorld* World, APlayerController* PC, int32 Depth, FVector& Out)
{
	if (!P.IsValid() || Depth > 3)
	{
		return false;
	}
	FVector Offset = FVector::ZeroVector;
	ReadVec(P, TEXT("offset"), Offset);
	if (ReadVec(P, TEXT("xyz"), Out))
	{
		return true;
	}
	bool bFlag = false;
	if (P->TryGetBoolField(TEXT("pawn"), bFlag) && bFlag)
	{
		const APawn* Pawn = PlayerPawn(PC);
		if (!Pawn)
		{
			return false;
		}
		Out = Pawn->GetActorLocation() + Offset;
		return true;
	}
	if (P->TryGetBoolField(TEXT("camera"), bFlag) && bFlag)
	{
		const APlayerCameraManager* View = PC ? PC->PlayerCameraManager.Get() : nullptr;
		if (!View)
		{
			return false;
		}
		double Forward = 0.0;
		P->TryGetNumberField(TEXT("forward"), Forward);
		Out = View->GetCameraLocation() + View->GetCameraRotation().Vector() * Forward;
		return true;
	}
	const TSharedPtr<FJsonObject>* Select = nullptr;
	if (P->TryGetObjectField(TEXT("actor"), Select))
	{
		TArray<AActor*> Found;
		int32 Total = 0;
		FindActors(World, PC, ParseSel(*Select), Depth + 1, 1, Found, Total);
		if (Found.Num() == 0)
		{
			return false;
		}
		Out = Found[0]->GetActorLocation() + Offset;
		return true;
	}
	return false;
}

// ---------------------------------------------------------------- reflection: prop:<Component>.<Property>[.<Sub>]

static bool SplitToken(const FString& Tok, FString& Name, int32& Index)
{
	Index = INDEX_NONE;
	Name = Tok;
	int32 Open = INDEX_NONE;
	if (Tok.FindChar(TEXT('['), Open))
	{
		if (!Tok.EndsWith(TEXT("]")))
		{
			return false;
		}
		Name = Tok.Left(Open);
		const FString Inner = Tok.Mid(Open + 1, Tok.Len() - Open - 2);
		if (Inner.IsEmpty() || !Inner.IsNumeric() || Inner.Contains(TEXT("-")) || Inner.Contains(TEXT(".")))
		{
			return false;
		}
		Index = FCString::Atoi(*Inner);
	}
	return !Name.IsEmpty();
}

/** A component by its name (StaticMeshComponent0), else by its class or a parent class, with or without the
 *  Component suffix (SpringArm, CharacterMovement). */
static UActorComponent* FindComponent(AActor* A, const FString& Name)
{
	TInlineComponentArray<UActorComponent*> Comps(A);
	for (UActorComponent* C : Comps)
	{
		if (C && C->GetName().Equals(Name, ESearchCase::IgnoreCase))
		{
			return C;
		}
	}
	const FString WithSuffix = Name + TEXT("Component");
	for (UActorComponent* C : Comps)
	{
		for (const UClass* K = C ? C->GetClass() : nullptr; K; K = K->GetSuperClass())
		{
			const FString N = K->GetName();
			if (N.Equals(Name, ESearchCase::IgnoreCase) || N.Equals(WithSuffix, ESearchCase::IgnoreCase))
			{
				return C;
			}
		}
	}
	return nullptr;
}

/** Numbers and booleans as numbers, enums as their index, object references as 1 when set, strings, names and texts
 *  as strings, arrays as their length, other structs as their exported text. */
static TSharedPtr<FJsonValue> PropValue(const FProperty* P, const void* V)
{
	if (const FBoolProperty* B = CastField<FBoolProperty>(P))
	{
		return Num(B->GetPropertyValue(V) ? 1.0 : 0.0);
	}
	if (const FEnumProperty* E = CastField<FEnumProperty>(P))
	{
		const FNumericProperty* U = E->GetUnderlyingProperty();
		if (!U)
		{
			return Null();
		}
		const int64 Raw = U->GetSignedIntPropertyValue(V);
		const UEnum* En = E->GetEnum();
		const int32 Ix = En ? En->GetIndexByValue(Raw) : INDEX_NONE;
		return Num(Ix != INDEX_NONE ? (double)Ix : (double)Raw);
	}
	if (const FNumericProperty* N = CastField<FNumericProperty>(P))
	{
		if (const UEnum* En = N->GetIntPropertyEnum())
		{
			const int64 Raw = N->GetSignedIntPropertyValue(V);
			const int32 Ix = En->GetIndexByValue(Raw);
			return Num(Ix != INDEX_NONE ? (double)Ix : (double)Raw);
		}
		if (N->IsFloatingPoint())
		{
			return Num(N->GetFloatingPointPropertyValue(V));
		}
		if (N->IsInteger())
		{
			return Num((double)N->GetSignedIntPropertyValue(V));
		}
		return Null();
	}
	if (const FSoftObjectProperty* SO = CastField<FSoftObjectProperty>(P))
	{
		return Num(SO->GetPropertyValue(V).IsNull() ? 0.0 : 1.0);
	}
	if (const FObjectPropertyBase* O = CastField<FObjectPropertyBase>(P))
	{
		return Num(O->GetObjectPropertyValue(V) ? 1.0 : 0.0);
	}
	if (const FStrProperty* S = CastField<FStrProperty>(P))
	{
		return Str(S->GetPropertyValue(V));
	}
	if (const FNameProperty* Nm = CastField<FNameProperty>(P))
	{
		return Str(Nm->GetPropertyValue(V).ToString());
	}
	if (const FTextProperty* T = CastField<FTextProperty>(P))
	{
		return Str(T->GetPropertyValue(V).ToString());
	}
	if (const FArrayProperty* A = CastField<FArrayProperty>(P))
	{
		FScriptArrayHelper Helper(A, V);
		return Num(Helper.Num());
	}
	if (CastField<FStructProperty>(P))
	{
		FString Text;
		P->ExportTextItem_Direct(Text, V, nullptr, nullptr, PPF_None);
		return Str(Text);
	}
	return Null();
}

static TSharedPtr<FJsonValue> WalkProp(UObject* Obj, void* Container, const UStruct* Type, const TArray<FString>& Toks, int32 i);

/** prop:<Component>.<Property>[.<Sub>] or prop:<Property> on an actor (or any object), by reflection. Unknown: null. */
static TSharedPtr<FJsonValue> ReadProp(UObject* Root, const FString& Path)
{
	TArray<FString> Toks;
	Path.ParseIntoArray(Toks, TEXT("."), true);
	if (!Root || Toks.Num() == 0 || Toks.Num() > 16)
	{
		return Null();
	}
	UObject* Obj = Root;  // the object the walk is in (nullptr inside a struct)
	void* Container = Root;
	const UStruct* Type = Root->GetClass();
	int32 i = 0;
	FString Name;
	int32 Index = INDEX_NONE;
	if (!SplitToken(Toks[0], Name, Index))
	{
		return Null();
	}
	if (AActor* A = Cast<AActor>(Root))
	{
		const bool bActorProp = FindFProperty<FProperty>(A->GetClass(), *Name) != nullptr;
		const bool bMaterials = Name.Equals(TEXT("Materials"), ESearchCase::IgnoreCase);
		if (!bActorProp && !bMaterials)
		{
			UActorComponent* C = FindComponent(A, Name);
			if (!C)
			{
				return Null();
			}
			if (Toks.Num() == 1)
			{
				return Num(1.0);  // the component exists
			}
			Obj = C;
			Container = C;
			Type = C->GetClass();
			i = 1;
		}
	}
	return WalkProp(Obj, Container, Type, Toks, i);
}

/** Walks Toks[i..] from a container (an object, or a struct when Obj is nullptr) of the given type. */
static TSharedPtr<FJsonValue> WalkProp(UObject* Obj, void* Container, const UStruct* Type, const TArray<FString>& Toks, int32 i)
{
	FString Name;
	int32 Index = INDEX_NONE;
	if (!Container || !Type || i >= Toks.Num())
	{
		return Null();
	}
	for (; i < Toks.Num(); ++i)
	{
		if (!SplitToken(Toks[i], Name, Index))
		{
			return Null();
		}
		const bool bLast = i == Toks.Num() - 1;
		const FProperty* P = FindFProperty<FProperty>(Type, *Name);
		if (!P)
		{
			// Materials / Materials[i] on a primitive component (or an actor's root): its effective materials (the
			// overrides, else the mesh's), as a count or 1 when set; a further .<Sub> reads the material.
			if (Obj && Name.Equals(TEXT("Materials"), ESearchCase::IgnoreCase))
			{
				UPrimitiveComponent* Prim = Cast<UPrimitiveComponent>(Obj);
				if (!Prim)
				{
					if (const AActor* A = Cast<AActor>(Obj))
					{
						Prim = Cast<UPrimitiveComponent>(A->GetRootComponent());
					}
				}
				if (!Prim)
				{
					return Null();
				}
				if (Index == INDEX_NONE)
				{
					return bLast ? Num(Prim->GetNumMaterials()) : Null();
				}
				UMaterialInterface* M = Index < Prim->GetNumMaterials() ? Prim->GetMaterial(Index) : nullptr;
				if (bLast)
				{
					return Num(M ? 1.0 : 0.0);
				}
				if (!M)
				{
					return Null();
				}
				Obj = M;
				Container = M;
				Type = M->GetClass();
				continue;
			}
			return Null();
		}
		void* ValuePtr = nullptr;
		const FProperty* ValueProp = P;
		if (Index != INDEX_NONE)
		{
			if (const FArrayProperty* AP = CastField<FArrayProperty>(P))
			{
				FScriptArrayHelper Helper(AP, AP->ContainerPtrToValuePtr<void>(Container));
				if (!Helper.IsValidIndex(Index))
				{
					return Null();
				}
				ValuePtr = Helper.GetRawPtr(Index);
				ValueProp = AP->Inner;
			}
			else if (Index < P->ArrayDim)
			{
				ValuePtr = P->ContainerPtrToValuePtr<void>(Container, Index);
			}
			else
			{
				return Null();
			}
		}
		else
		{
			ValuePtr = P->ContainerPtrToValuePtr<void>(Container);
		}
		if (!ValuePtr || !ValueProp)
		{
			return Null();
		}
		if (bLast)
		{
			return PropValue(ValueProp, ValuePtr);
		}
		if (const FStructProperty* SP = CastField<FStructProperty>(ValueProp))
		{
			Obj = nullptr;
			Container = ValuePtr;
			Type = SP->Struct;
			continue;
		}
		if (const FObjectPropertyBase* OP = CastField<FObjectPropertyBase>(ValueProp))
		{
			UObject* Next = OP->GetObjectPropertyValue(ValuePtr);
			if (!IsValid(Next))
			{
				return Null();
			}
			Obj = Next;
			Container = Next;
			Type = Next->GetClass();
			continue;
		}
		return Null();
	}
	return Null();
}

// ---------------------------------------------------------------- actors

/** An angle in (-180, 180]. */
static double Angle(double Deg) { return FRotator::NormalizeAxis(Deg); }

/** bone:<Component>.<BoneOrSocket>.x|y|z: the world location of a bone or socket of a mesh component. */
static TSharedPtr<FJsonValue> BoneField(AActor* A, const FString& Path)
{
	TArray<FString> Toks;
	Path.ParseIntoArray(Toks, TEXT("."), true);
	if (Toks.Num() < 3)
	{
		return Null();
	}
	const FString Axis = Toks.Last();
	const FString Bone = FString::Join(TArrayView<const FString>(Toks).Slice(1, Toks.Num() - 2), TEXT("."));
	const USceneComponent* C = Cast<USceneComponent>(FindComponent(A, Toks[0]));
	if (!C || !C->DoesSocketExist(FName(*Bone)))
	{
		return Null();
	}
	const FVector L = C->GetSocketLocation(FName(*Bone));
	if (Axis.Equals(TEXT("x"), ESearchCase::IgnoreCase)) return Num(L.X);
	if (Axis.Equals(TEXT("y"), ESearchCase::IgnoreCase)) return Num(L.Y);
	if (Axis.Equals(TEXT("z"), ESearchCase::IgnoreCase)) return Num(L.Z);
	return Null();
}

/** bb:<Key>: a blackboard value of an AI controller (or of a pawn's AI controller). */
static TSharedPtr<FJsonValue> BlackboardField(AActor* A, const FString& KeyName)
{
	const AAIController* AI = Cast<AAIController>(A);
	if (!AI)
	{
		if (const APawn* Pawn = Cast<APawn>(A))
		{
			AI = Cast<AAIController>(Pawn->GetController());
		}
	}
	const UBlackboardComponent* BB = AI ? AI->GetBlackboardComponent() : nullptr;
	const UBlackboardData* Data = BB ? BB->GetBlackboardAsset() : nullptr;
	if (!Data)
	{
		return Null();
	}
	const FName Key(*KeyName);
	const FBlackboard::FKey Id = BB->GetKeyID(Key);
	const FBlackboardEntry* Entry = Id != FBlackboard::InvalidKey ? Data->GetKey(Id) : nullptr;
	const UBlackboardKeyType* Type = Entry ? Entry->KeyType.Get() : nullptr;
	if (!Type)
	{
		return Null();
	}
	if (Type->IsA<UBlackboardKeyType_Bool>()) return Num(BB->GetValueAsBool(Key) ? 1.0 : 0.0);
	if (Type->IsA<UBlackboardKeyType_Int>()) return Num(BB->GetValueAsInt(Key));
	if (Type->IsA<UBlackboardKeyType_Float>()) return Num(BB->GetValueAsFloat(Key));
	if (Type->IsA<UBlackboardKeyType_Enum>() || Type->IsA<UBlackboardKeyType_NativeEnum>())
	{
		const UEnum* En = nullptr;
		if (const UBlackboardKeyType_Enum* E = Cast<UBlackboardKeyType_Enum>(Type)) En = E->EnumType;
		if (const UBlackboardKeyType_NativeEnum* E = Cast<UBlackboardKeyType_NativeEnum>(Type)) En = E->EnumType;
		const uint8 Raw = BB->GetValueAsEnum(Key);
		const int32 Ix = En ? En->GetIndexByValue(Raw) : INDEX_NONE;
		return Num(Ix != INDEX_NONE ? (double)Ix : (double)Raw);
	}
	if (Type->IsA<UBlackboardKeyType_Object>()) return Num(BB->GetValueAsObject(Key) ? 1.0 : 0.0);
	if (Type->IsA<UBlackboardKeyType_Class>()) return Num(BB->GetValueAsClass(Key) ? 1.0 : 0.0);
	if (Type->IsA<UBlackboardKeyType_Name>()) return Str(BB->GetValueAsName(Key).ToString());
	if (Type->IsA<UBlackboardKeyType_String>()) return Str(BB->GetValueAsString(Key));
	if (Type->IsA<UBlackboardKeyType_Vector>()) return Str(BB->GetValueAsVector(Key).ToString());
	if (Type->IsA<UBlackboardKeyType_Rotator>()) return Str(BB->GetValueAsRotator(Key).ToString());
	return Null();
}

/**
 * The world-aligned box around the actor's geometry, for extent_*: its own registered mesh components (static,
 * instanced, skeletal, spline, procedural and dynamic meshes, world-space widgets) that are drawn in game and have a
 * mesh, each by its bounds. Collision shapes (boxes, spheres, capsules), lights, audio, effects, editor-only and
 * visualization components (a camera's frustum, which alone spans 1010 cm around the camera in editor builds, its
 * proxy mesh, arrows, billboards), hidden components and empty meshes don't count; child actors' components don't
 * either. Invalid when the actor draws nothing.
 */
static FBox GeometryBox(const AActor* A)
{
	FBox Box(ForceInit);
	TInlineComponentArray<UMeshComponent*> Meshes(A);
	for (const UMeshComponent* M : Meshes)
	{
		if (!M || !M->IsRegistered() || M->IsEditorOnly() || !M->IsVisible() || M->bHiddenInGame)
		{
			continue;
		}
		if (const UStaticMeshComponent* SM = Cast<UStaticMeshComponent>(M); SM && !SM->GetStaticMesh())
		{
			continue;
		}
		if (const USkinnedMeshComponent* SK = Cast<USkinnedMeshComponent>(M); SK && !SK->GetSkinnedAsset())
		{
			continue;
		}
		const FBoxSphereBounds& B = M->Bounds;
		if (B.BoxExtent.IsNearlyZero())
		{
			continue;  // no geometry (e.g. an instanced mesh with no instances, a screen-space widget)
		}
		Box += B.GetBox();
	}
	return Box;
}

/** Whether a primitive component simulates physics: its own body, or any body of a skeletal mesh (a ragdoll, pieces
 *  that broke off). */
static bool Simulating(const UPrimitiveComponent* P)
{
	if (!P)
	{
		return false;
	}
	if (P->IsSimulatingPhysics())
	{
		return true;
	}
	if (const USkeletalMeshComponent* SK = Cast<USkeletalMeshComponent>(P))
	{
		for (const FBodyInstance* B : SK->Bodies)
		{
			if (B && B->IsInstanceSimulatingPhysics())
			{
				return true;
			}
		}
	}
	return false;
}

/** A live effect (a components select's `effect`): a particle system component (Niagara, Cascade: any FX system
 *  component) that is active, or a decal component that is drawn (visible, not hidden in game, its owner not hidden).
 *  An effect actor (a Niagara actor, an emitter, a decal actor) counts by its component. */
static bool LiveEffect(const UActorComponent* C)
{
	if (const UFXSystemComponent* FX = Cast<UFXSystemComponent>(C))
	{
		return FX->IsActive();
	}
	if (const UDecalComponent* D = Cast<UDecalComponent>(C))
	{
		const AActor* Owner = D->GetOwner();
		return D->IsVisible() && !D->bHiddenInGame && !(Owner && Owner->IsHidden());
	}
	return false;
}

/**
 * spread: how far apart the parts of the actor's geometry are, the diagonal (cm) of the world-aligned box around their
 * centres: each mesh component GeometryBox counts by its bounds centre, a skeletal mesh with several physics bodies by
 * each body's place. 0 with one part, null with none. A whole object reads its parts' own layout; one broken into
 * pieces that fell or flew apart reads more, whatever still draws them.
 */
static TSharedPtr<FJsonValue> Spread(const AActor* A)
{
	FBox Box(ForceInit);
	TInlineComponentArray<UMeshComponent*> Meshes(A);
	for (const UMeshComponent* M : Meshes)
	{
		if (!M || !M->IsRegistered() || M->IsEditorOnly() || !M->IsVisible() || M->bHiddenInGame)
		{
			continue;
		}
		if (const UStaticMeshComponent* SM = Cast<UStaticMeshComponent>(M); SM && !SM->GetStaticMesh())
		{
			continue;
		}
		if (const USkinnedMeshComponent* SK = Cast<USkinnedMeshComponent>(M); SK && !SK->GetSkinnedAsset())
		{
			continue;
		}
		if (M->Bounds.BoxExtent.IsNearlyZero())
		{
			continue;
		}
		const USkeletalMeshComponent* Skeletal = Cast<USkeletalMeshComponent>(M);
		int32 Bodies = 0;
		if (Skeletal && Skeletal->Bodies.Num() > 1)
		{
			for (const FBodyInstance* B : Skeletal->Bodies)
			{
				if (B && B->IsValidBodyInstance())
				{
					Box += B->GetUnrealWorldTransform().GetLocation();
					++Bodies;
				}
			}
		}
		if (Bodies == 0)
		{
			Box += M->Bounds.Origin;
		}
	}
	return Box.IsValid ? Num(Box.GetSize().Size()) : Null();
}

static constexpr double ChangeBounds = 1.0;  // cm: changed when a part's world, or a skinned mesh's local, bounds moved more
static constexpr double ChangePose = 5.0;  // cm: changed when a skinned mesh's bones moved more than this in all

static bool IsChangeField(const FString& F)
{
	return F == TEXT("changed") || F == TEXT("bounds_change") || F == TEXT("pose_change");
}

/** A part as it is now, for changed: drawn (visible, not hidden in game, its owner not hidden), its world bounds and, of
 *  a skinned mesh, its local bounds and every bone's place in the component's own space (a follower's from its leader
 *  pose), so a pose that moves reads whether or not its bounds do and whatever the component itself does. */
static FPartState PartState(const UPrimitiveComponent* P)
{
	FPartState S;
	const AActor* Owner = P->GetOwner();
	S.bDrawn = P->IsRegistered() && P->IsVisible() && !P->bHiddenInGame && !(Owner && Owner->IsHidden());
	S.World = P->Bounds.GetBox();
	if (const USkinnedMeshComponent* SK = Cast<USkinnedMeshComponent>(P))
	{
		S.bSkinned = true;
		if (SK->GetSkinnedAsset())
		{
			S.Local = SK->CalcBounds(FTransform::Identity).GetBox();
			const int32 N = SK->GetNumBones();
			S.Bones.Reserve(N);
			for (int32 i = 0; i < N; ++i)
			{
				S.Bones.Add(SK->GetBoneTransform(i, FTransform::Identity).GetLocation());
			}
		}
	}
	return S;
}

/** How far (cm) the furthest face of a box moved; -1 when only one of them is a box. */
static double BoxMove(const FBox& A, const FBox& B)
{
	if (!A.IsValid || !B.IsValid)
	{
		return A.IsValid == B.IsValid ? 0.0 : -1.0;
	}
	return (A.Min - B.Min).GetAbs().ComponentMax((A.Max - B.Max).GetAbs()).GetMax();
}

/** A part against its first sample: changed, bounds_change (its world bounds' furthest face, cm) and pose_change (its
 *  bones' moves summed, cm; only for a skinned mesh). */
struct FChangeReading
{
	bool bChanged = false;
	bool bAny = false;  // a part was compared (else bounds_change is null)
	bool bPose = false;  // a skinned mesh was compared (else pose_change is null)
	double Bounds = 0.0;
	double Pose = 0.0;
};

static FChangeReading PartChange(const FPartState& First, const FPartState& Now)
{
	FChangeReading C;
	C.bAny = true;
	const double World = BoxMove(First.World, Now.World);
	C.Bounds = FMath::Max(World, 0.0);
	C.bChanged = First.bDrawn != Now.bDrawn || World < 0.0 || World > ChangeBounds;
	if (First.bSkinned && Now.bSkinned)
	{
		C.bPose = true;
		const int32 N = FMath::Min(First.Bones.Num(), Now.Bones.Num());
		for (int32 i = 0; i < N; ++i)
		{
			C.Pose += FVector::Dist(First.Bones[i], Now.Bones[i]);
		}
		const double Local = BoxMove(First.Local, Now.Local);
		C.bChanged |= First.Bones.Num() != Now.Bones.Num() || C.Pose > ChangePose || Local < 0.0 || Local > ChangeBounds;
	}
	return C;
}

static TSharedPtr<FJsonValue> ChangeField(const FChangeReading& C, const FString& F)
{
	if (F == TEXT("changed")) return Num(C.bChanged ? 1.0 : 0.0);
	if (F == TEXT("bounds_change")) return C.bAny ? Num(C.Bounds) : Null();
	if (F == TEXT("pose_change")) return C.bPose ? Num(C.Pose) : Null();
	return Null();
}

/** The parts changed compares of an actor: its own registered mesh components with a mesh (static, instanced,
 *  skeletal, spline, procedural and dynamic meshes, world-space widgets), drawn or hidden; editor-only ones and empty
 *  meshes left out, as GeometryBox leaves them. */
static void ChangeParts(const AActor* A, TArray<UMeshComponent*>& Out)
{
	TInlineComponentArray<UMeshComponent*> Meshes(A);
	for (UMeshComponent* M : Meshes)
	{
		if (!M || !M->IsRegistered() || M->IsEditorOnly())
		{
			continue;
		}
		if (const UStaticMeshComponent* SM = Cast<UStaticMeshComponent>(M); SM && !SM->GetStaticMesh())
		{
			continue;
		}
		if (const USkinnedMeshComponent* SK = Cast<USkinnedMeshComponent>(M); SK && !SK->GetSkinnedAsset())
		{
			continue;
		}
		Out.Add(M);
	}
}

/**
 * An actor against the first sample it was seen in: changed when any part changed (PartChange), a part drawn then is
 * gone, or a part not there then is drawn now; bounds_change the largest of its parts'; pose_change its skinned
 * meshes' summed. The first sample records every part and reads unchanged.
 */
static FChangeReading ActorChange(AActor* A, TMap<FObjectKey, FPartState>& Firsts, TMap<FObjectKey, TArray<FObjectKey>>& FirstParts)
{
	FChangeReading Out;
	TArray<UMeshComponent*> Parts;
	ChangeParts(A, Parts);
	const FObjectKey ActorKey(A);
	const TArray<FObjectKey>* Before = FirstParts.Find(ActorKey);
	TArray<FObjectKey> Keys;
	for (const UMeshComponent* M : Parts)
	{
		const FObjectKey Key(M);
		Keys.Add(Key);
		const FPartState Now = PartState(M);
		if (!Before)
		{
			Firsts.Add(Key, Now);
			Out.bAny = true;
			Out.bPose |= Now.bSkinned;
			continue;
		}
		const FPartState* First = Before->Contains(Key) ? Firsts.Find(Key) : nullptr;
		if (!First)
		{
			Out.bChanged |= Now.bDrawn;  // a part added since, drawn
			continue;
		}
		const FChangeReading C = PartChange(*First, Now);
		Out.bChanged |= C.bChanged;
		Out.bAny = true;
		Out.Bounds = FMath::Max(Out.Bounds, C.Bounds);
		Out.bPose |= C.bPose;
		Out.Pose += C.Pose;
	}
	if (!Before)
	{
		FirstParts.Add(ActorKey, MoveTemp(Keys));
		return Out;
	}
	for (const FObjectKey& Key : *Before)
	{
		const FPartState* First = Firsts.Find(Key);
		if (!Keys.Contains(Key) && First && First->bDrawn)
		{
			Out.bChanged = true;  // a part drawn then is gone
		}
	}
	return Out;
}

/** damage_taken: what each actor's TakeDamage returned for the play's staged hits, summed (the probe notes them). */
static TMap<FObjectKey, double> DamageTaken;

void NoteDamage(const AActor* A, double Taken)
{
	if (A)
	{
		DamageTaken.FindOrAdd(FObjectKey(A)) += Taken;
	}
}

static TSharedPtr<FJsonValue> ActorField(AActor* A, const FString& F)
{
	if (F.StartsWith(TEXT("prop:")))
	{
		return ReadProp(A, F.Mid(5));
	}
	if (F.StartsWith(TEXT("bone:")))
	{
		return BoneField(A, F.Mid(5));
	}
	if (F.StartsWith(TEXT("bb:")))
	{
		return BlackboardField(A, F.Mid(3));
	}
	if (F.StartsWith(TEXT("rel_yaw:")))
	{
		const USceneComponent* C = Cast<USceneComponent>(FindComponent(A, F.Mid(8)));
		return C ? Num(Angle(C->GetComponentRotation().Yaw - A->GetActorRotation().Yaw)) : Null();
	}
	if (F.StartsWith(TEXT("world_yaw:")) || F.StartsWith(TEXT("world_pitch:")) || F.StartsWith(TEXT("world_roll:")))
	{
		// the component's own rotation in the world, whether its actor or the component itself turned
		FString Which, Name;
		F.Split(TEXT(":"), &Which, &Name);
		const USceneComponent* C = Cast<USceneComponent>(FindComponent(A, Name));
		if (!C)
		{
			return Null();
		}
		const FRotator R = C->GetComponentRotation();
		return Num(Angle(Which == TEXT("world_yaw") ? R.Yaw : Which == TEXT("world_pitch") ? R.Pitch : R.Roll));
	}
	if (F.StartsWith(TEXT("forward:")))
	{
		// forward:<Component>.x|y|z: the component's forward unit vector in the world (a light's: where its light goes)
		FString Name, Axis;
		if (!F.Mid(8).Split(TEXT("."), &Name, &Axis, ESearchCase::CaseSensitive, ESearchDir::FromEnd))
		{
			return Null();
		}
		const USceneComponent* C = Cast<USceneComponent>(FindComponent(A, Name));
		if (!C)
		{
			return Null();
		}
		const FVector V = C->GetForwardVector();
		if (Axis == TEXT("x")) return Num(V.X);
		if (Axis == TEXT("y")) return Num(V.Y);
		if (Axis == TEXT("z")) return Num(V.Z);
		return Null();
	}
	if (F == TEXT("count"))
	{
		return Num(1.0);
	}
	const FVector L = A->GetActorLocation();
	const FRotator R = A->GetActorRotation();
	if (F == TEXT("x")) return Num(L.X);
	if (F == TEXT("y")) return Num(L.Y);
	if (F == TEXT("z")) return Num(L.Z);
	if (F == TEXT("yaw")) return Num(Angle(R.Yaw));
	if (F == TEXT("pitch")) return Num(Angle(R.Pitch));
	if (F == TEXT("roll")) return Num(Angle(R.Roll));
	if (F == TEXT("facing_vs_velocity"))
	{
		const FVector V = A->GetVelocity();
		if (V.Size() < 10.0)
		{
			return Null();
		}
		const double Cos = FMath::Clamp(FVector::DotProduct(A->GetActorForwardVector(), V.GetSafeNormal()), -1.0, 1.0);
		return Num(FMath::RadiansToDegrees(FMath::Acos(Cos)));
	}
	if (F == TEXT("scale"))
	{
		const FVector S = A->GetActorScale3D();
		return Num((FMath::Abs(S.X) + FMath::Abs(S.Y) + FMath::Abs(S.Z)) / 3.0);
	}
	if (F.StartsWith(TEXT("extent_")))
	{
		const FBox Box = GeometryBox(A);
		if (!Box.IsValid)
		{
			return Null();  // nothing drawn: no mesh component with a mesh
		}
		const FVector Extent = Box.GetExtent();
		if (F == TEXT("extent_x")) return Num(Extent.X);
		if (F == TEXT("extent_y")) return Num(Extent.Y);
		if (F == TEXT("extent_z")) return Num(Extent.Z);
		return Null();
	}
	if (F == TEXT("hidden"))
	{
		return Num(A->IsHidden() ? 1.0 : 0.0);
	}
	if (F == TEXT("collision"))
	{
		bool bAny = false;
		if (A->GetActorEnableCollision())
		{
			TInlineComponentArray<UPrimitiveComponent*> Prims(A);
			for (const UPrimitiveComponent* Prim : Prims)
			{
				if (Prim && Prim->IsRegistered() && Prim->IsCollisionEnabled())
				{
					bAny = true;
					break;
				}
			}
		}
		return Num(bAny ? 1.0 : 0.0);
	}
	if (F == TEXT("speed"))
	{
		return Num(A->GetVelocity().Size());
	}
	if (F == TEXT("simulating"))
	{
		// any of its primitive components simulates physics (its pieces broke loose, a ragdoll)
		TInlineComponentArray<UPrimitiveComponent*> Prims(A);
		for (const UPrimitiveComponent* Prim : Prims)
		{
			if (Prim && Prim->IsRegistered() && Simulating(Prim))
			{
				return Num(1.0);
			}
		}
		return Num(0.0);
	}
	if (F == TEXT("spread"))
	{
		return Spread(A);
	}
	if (F == TEXT("montage"))
	{
		// an animation montage plays on one of its skeletal meshes (a stagger, a flinch, a parry, an attack)
		TInlineComponentArray<USkeletalMeshComponent*> Meshes(A);
		for (const USkeletalMeshComponent* M : Meshes)
		{
			const UAnimInstance* Anim = M && M->IsRegistered() ? M->GetAnimInstance() : nullptr;
			if (Anim && Anim->IsAnyMontagePlaying())
			{
				return Num(1.0);
			}
		}
		return Num(0.0);
	}
	if (F == TEXT("damage_taken"))
	{
		const double* Taken = DamageTaken.Find(FObjectKey(A));
		return Taken ? Num(*Taken) : Null();
	}
	return Null();
}

/** focus_player: 1 when the actor's AI controller (its own, or the actor itself as one) has the player pawn as its focus. */
static TSharedPtr<FJsonValue> FocusField(AActor* A, APlayerController* PC)
{
	const AAIController* AI = Cast<AAIController>(A);
	if (!AI)
	{
		if (const APawn* Pawn = Cast<APawn>(A))
		{
			AI = Cast<AAIController>(Pawn->GetController());
		}
	}
	if (!AI)
	{
		return Null();
	}
	const APawn* Player = PlayerPawn(PC);
	return Num(Player && AI->GetFocusActor() == Player ? 1.0 : 0.0);
}

// ---------------------------------------------------------------- widgets

static bool WidgetClassMatches(UWidget* W, const FString& Want, bool bWithOwners)
{
	if (ClassMatches(W->GetClass(), Want))
	{
		return true;
	}
	if (!bWithOwners)
	{
		return false;
	}
	// an enclosing user widget of that class (the widget's tree belongs to it)
	for (UUserWidget* Owner = W->GetTypedOuter<UUserWidget>(); Owner; Owner = Owner->GetTypedOuter<UUserWidget>())
	{
		if (ClassMatches(Owner->GetClass(), Want))
		{
			return true;
		}
	}
	return false;
}

/** Visible and every parent visible (through the enclosing user widgets up to the one in the viewport). */
static bool WidgetVisible(UWidget* W)
{
	for (int32 Depth = 0; W && Depth < 512; ++Depth)
	{
		if (!W->IsVisible() || W->GetRenderOpacity() <= 0.001f)
		{
			return false;
		}
		if (UWidget* Parent = W->GetParent())
		{
			W = Parent;
			continue;
		}
		W = W->GetTypedOuter<UUserWidget>();
	}
	return true;
}

/** The game viewport's rectangle in Slate's absolute (desktop) space. */
static bool ViewportRect(FVector2D& Pos, FVector2D& Size)
{
	const UGameViewportClient* GVC = GEngine ? GEngine->GameViewport.Get() : nullptr;
	const TSharedPtr<SViewport> VP = GVC ? GVC->GetGameViewportWidget() : nullptr;
	if (!VP.IsValid())
	{
		return false;
	}
	const FGeometry& G = VP->GetTickSpaceGeometry();
	Pos = FVector2D(G.GetAbsolutePosition());
	Size = FVector2D(G.GetAbsoluteSize());
	return Size.X > 0.0 && Size.Y > 0.0;
}

/** x, y, w, h: a widget's rectangle (its cached geometry) in viewport fractions; null before it has been laid out. */
static TSharedPtr<FJsonValue> RectField(const FGeometry& G, const FString& F)
{
	FVector2D VPos, VSize;
	const FVector2D Pos(G.GetAbsolutePosition());
	const FVector2D Size(G.GetAbsoluteSize());
	if (!ViewportRect(VPos, VSize) || (Size.X <= 0.0 && Size.Y <= 0.0))
	{
		return Null();
	}
	if (F == TEXT("x")) return Num((Pos.X - VPos.X) / VSize.X);
	if (F == TEXT("y")) return Num((Pos.Y - VPos.Y) / VSize.Y);
	if (F == TEXT("w")) return Num(Size.X / VSize.X);
	if (F == TEXT("h")) return Num(Size.Y / VSize.Y);
	return Null();
}

static bool IsRectField(const FString& F) { return F == TEXT("x") || F == TEXT("y") || F == TEXT("w") || F == TEXT("h"); }

static TSharedPtr<FJsonValue> BrushFields(const FSlateBrush* Brush, const FString& F)
{
	const UObject* Resource = Brush ? Brush->GetResourceObject() : nullptr;
	if (F == TEXT("has_brush"))
	{
		return Num(Resource ? 1.0 : 0.0);
	}
	return Resource ? Str(Resource->GetPathName()) : Null();  // brush
}

static TSharedPtr<FJsonValue> WidgetField(UWidget* W, const FString& F)
{
	if (F == TEXT("count"))
	{
		return Num(1.0);
	}
	if (F == TEXT("visible"))
	{
		return Num(WidgetVisible(W) ? 1.0 : 0.0);
	}
	if (IsRectField(F))
	{
		return RectField(W->GetCachedGeometry(), F);
	}
	if (F == TEXT("text"))
	{
		if (const UTextBlock* T = Cast<UTextBlock>(W))
		{
			return Str(T->GetText().ToString());
		}
		if (const URichTextBlock* RT = Cast<URichTextBlock>(W))
		{
			return Str(RT->GetText().ToString());
		}
		return Null();
	}
	if (F == TEXT("percent"))
	{
		if (const UProgressBar* PB = Cast<UProgressBar>(W))
		{
			return Num(PB->GetPercent());
		}
		return Null();
	}
	if (F == TEXT("has_brush") || F == TEXT("brush"))
	{
		if (const UImage* I = Cast<UImage>(W))
		{
			return BrushFields(&I->GetBrush(), F);
		}
		return Null();
	}
	if (F.StartsWith(TEXT("prop:")))
	{
		return ReadProp(W, F.Mid(5));
	}
	return Null();
}

/** The UMG trees in the viewport (AddToViewport / AddToPlayerScreen) of a world, in a stable order. */
static void ViewportWidgets(UWorld* World, TArray<UUserWidget*>& Tops)
{
	if (!World)
	{
		return;
	}
	for (TObjectIterator<UUserWidget> It; It; ++It)
	{
		UUserWidget* W = *It;
		if (IsValid(W) && !W->HasAnyFlags(RF_ClassDefaultObject | RF_ArchetypeObject) && W->GetWorld() == World && W->IsInViewport())
		{
			Tops.Add(W);
		}
	}
	Tops.Sort([](const UUserWidget& A, const UUserWidget& B) { return A.GetName() < B.GetName(); });
}

/** A top user widget and every widget under it, once each, the user widgets nested in its tree included (a HUD built of
 *  child user widgets, e.g. a per-player HUD inside a shared overlay, or a gauge inside that HUD). The engine's
 *  UWidgetTree::ForEachWidgetAndDescendants walks into a nested user widget's tree but never passes the nested user
 *  widget itself, so widgets of those classes were never found. */
static void ForEachWidgetDeep(UUserWidget* Top, TFunctionRef<void(UWidget*)> Visit)
{
	TSet<UWidget*> Seen;
	TFunction<void(UUserWidget*, int32)> Walk = [&](UUserWidget* User, int32 Depth)
	{
		if (!User || !User->WidgetTree || Depth > 64)
		{
			return;
		}
		User->WidgetTree->ForEachWidget([&](UWidget* W)
		{
			bool bAlready = false;
			Seen.Add(W, &bAlready);
			if (!W || bAlready)
			{
				return;
			}
			Visit(W);
			if (UUserWidget* Nested = Cast<UUserWidget>(W))
			{
				Walk(Nested, Depth + 1);
			}
		});
	};
	if (Top)
	{
		Seen.Add(Top);
		Visit(Top);
		Walk(Top, 0);
	}
}

bool ViewportPoint(double Fx, double Fy, FVector2D& OutAbsolute)
{
	FVector2D Pos, Size;
	if (!ViewportRect(Pos, Size))
	{
		return false;
	}
	OutAbsolute = Pos + FVector2D(FMath::Clamp(Fx, 0.0, 1.0) * Size.X, FMath::Clamp(Fy, 0.0, 1.0) * Size.Y);
	return true;
}

UButton* FindButton(UWorld* World, const FString& Want)
{
	TArray<UUserWidget*> Tops;
	ViewportWidgets(World, Tops);
	UButton* Found = nullptr;
	auto Visit = [&](UWidget* W)
	{
		UButton* B = Cast<UButton>(W);
		if (!Found && B && (B->GetName().MatchesWildcard(Want) || ClassMatches(B->GetClass(), Want)) && B->GetIsEnabled() && WidgetVisible(B))
		{
			Found = B;
		}
	};
	for (UUserWidget* Top : Tops)
	{
		ForEachWidgetDeep(Top, Visit);
	}
	return Found;
}

/** Do, with a renderer of its own for a `has` `lit` while none is set (defined after FGlowRender). */
static void WithSelectRender(TFunctionRef<void()> Do);

static bool TeleportSpotNow(UWorld* World, APlayerController* PC, const TSharedPtr<FJsonObject>& Select, double Distance,
	const FVector& Offset, const TSharedPtr<FJsonObject>& Face, FVector& OutLocation, double& OutYaw, FString& OutName)
{
	const APawn* Pawn = PlayerPawn(PC);
	if (!World || !Pawn || !Select.IsValid())
	{
		return false;
	}
	TArray<AActor*> Found;
	int32 Total = 0;
	FindActors(World, PC, ParseSel(Select), 0, MAX_int32, Found, Total);
	const FVector From = Pawn->GetActorLocation();
	const AActor* Target = nullptr;
	double Best = 0.0;
	for (const AActor* A : Found)
	{
		const double D = FVector::DistSquared(A->GetActorLocation(), From);
		if (A != Pawn && (!Target || D < Best))
		{
			Target = A;
			Best = D;
		}
	}
	if (!Target)
	{
		return false;
	}
	const FVector There = Target->GetActorLocation();
	FVector Side = FVector(From.X - There.X, From.Y - There.Y, 0.0).GetSafeNormal();
	if (Side.IsNearlyZero())
	{
		Side = -Target->GetActorForwardVector().GetSafeNormal2D();  // the pawn is right above it: in front of it
	}
	if (Side.IsNearlyZero())
	{
		Side = FVector(-1.0, 0.0, 0.0);
	}
	OutLocation = There + Side * Distance + Offset;
	FVector Look = There;
	if (Face.IsValid() && !ResolvePoint(Face, World, PC, 0, Look))
	{
		Look = There;  // the point doesn't resolve: face the target
	}
	const FVector Dir = Look - OutLocation;
	OutYaw = Dir.SizeSquared2D() > 1.0 ? FMath::RadiansToDegrees(FMath::Atan2(Dir.Y, Dir.X)) : Pawn->GetActorRotation().Yaw;
	OutName = Target->GetName();
	return true;
}

bool TeleportSpot(UWorld* World, APlayerController* PC, const TSharedPtr<FJsonObject>& Select, double Distance, const FVector& Offset,
	const TSharedPtr<FJsonObject>& Face, FVector& OutLocation, double& OutYaw, FString& OutName)
{
	bool bFound = false;
	WithSelectRender([&] { bFound = TeleportSpotNow(World, PC, Select, Distance, Offset, Face, OutLocation, OutYaw, OutName); });
	return bFound;
}

// ---------------------------------------------------------------- the stages of a contact (game-contact-checks spec)

AActor* NearestMatch(UWorld* World, APlayerController* PC, const TSharedPtr<FJsonObject>& Select, TArray<AActor*>* OutAll)
{
	if (!World || !Select.IsValid())
	{
		return nullptr;
	}
	const FSel S = ParseSel(Select);
	TArray<AActor*> Found;
	int32 Total = 0;
	WithSelectRender([&] { FindActors(World, PC, S, 0, MAX_int32, Found, Total); });
	const APawn* Pawn = PlayerPawn(PC);
	if (!S.bPlayer)
	{
		Found.Remove(const_cast<APawn*>(Pawn));  // a stage acts on something other than the player unless it names the player
	}
	const FVector From = Pawn ? Pawn->GetActorLocation() : FVector::ZeroVector;
	Found.Sort([&From](const AActor& A, const AActor& B) { return FVector::DistSquared(A.GetActorLocation(), From) < FVector::DistSquared(B.GetActorLocation(), From); });
	if (OutAll)
	{
		*OutAll = Found;
	}
	return Found.IsEmpty() ? nullptr : Found[0];
}

bool PointOf(UWorld* World, APlayerController* PC, const TSharedPtr<FJsonObject>& Point, FVector& OutPoint)
{
	bool bFound = false;
	WithSelectRender([&] { bFound = Point.IsValid() && ResolvePoint(Point, World, PC, 0, OutPoint); });
	return bFound;
}

/** set: the property Path names on Root (an actor's own, else one of its components' as prop: reads it), and where its
 *  value is; false with why when a part of the path doesn't resolve. */
static bool ResolveWritable(UObject* Root, const FString& Path, FProperty*& OutProp, void*& OutPtr, FString& OutWhy)
{
	TArray<FString> Toks;
	Path.ParseIntoArray(Toks, TEXT("."), true);
	if (!Root || Toks.Num() == 0 || Toks.Num() > 6)
	{
		OutWhy = TEXT("no property path");
		return false;
	}
	void* Container = Root;
	const UStruct* Type = Root->GetClass();
	int32 i = 0;
	if (AActor* A = Cast<AActor>(Root); A && !FindFProperty<FProperty>(A->GetClass(), *Toks[0]))
	{
		UActorComponent* C = Toks.Num() > 1 ? FindComponent(A, Toks[0]) : nullptr;
		if (!C)
		{
			OutWhy = FString::Printf(TEXT("%s has no property or component %s"), *A->GetClass()->GetName(), *Toks[0]);
			return false;
		}
		Container = C;
		Type = C->GetClass();
		i = 1;
	}
	for (; i < Toks.Num(); ++i)
	{
		FProperty* P = FindFProperty<FProperty>(Type, *Toks[i]);
		if (!P)
		{
			OutWhy = FString::Printf(TEXT("%s has no property %s"), *Type->GetName(), *Toks[i]);
			return false;
		}
		void* Ptr = P->ContainerPtrToValuePtr<void>(Container);
		if (i == Toks.Num() - 1)
		{
			OutProp = P;
			OutPtr = Ptr;
			return true;
		}
		if (const FStructProperty* SP = CastField<FStructProperty>(P))
		{
			Container = Ptr;
			Type = SP->Struct;
		}
		else if (const FObjectPropertyBase* OP = CastField<FObjectPropertyBase>(P))
		{
			UObject* Next = OP->GetObjectPropertyValue(Ptr);
			if (!IsValid(Next))
			{
				OutWhy = FString::Printf(TEXT("%s is not set"), *Toks[i]);
				return false;
			}
			Container = Next;
			Type = Next->GetClass();
		}
		else
		{
			OutWhy = FString::Printf(TEXT("%s holds no properties"), *Toks[i]);
			return false;
		}
	}
	OutWhy = TEXT("no property path");
	return false;
}

/** A JSON number, boolean or string written into a property's value: numbers, booleans, enums (by their name, or a
 *  number as their index), names, strings and texts; false with why for any other kind. */
static bool AssignJson(const FProperty* P, void* Ptr, const TSharedPtr<FJsonValue>& Value, FString& OutWhy)
{
	double Number = 0.0;
	bool bBool = false;
	FString Text;
	const bool bIsNumber = Value.IsValid() && Value->Type == EJson::Number && Value->TryGetNumber(Number);
	const bool bIsBool = Value.IsValid() && Value->Type == EJson::Boolean && Value->TryGetBool(bBool);
	const bool bIsString = Value.IsValid() && Value->Type == EJson::String && Value->TryGetString(Text);
	auto EnumValue = [&](const UEnum* En, int64& Out)
	{
		if (bIsString && En)
		{
			int64 V = En->GetValueByNameString(Text);
			if (V == INDEX_NONE)
			{
				V = En->GetValueByNameString(En->GenerateFullEnumName(*Text));
			}
			Out = V;
			return V != INDEX_NONE;
		}
		if (bIsNumber && En)
		{
			const int32 Index = (int32)Number;
			if (Number != (double)Index || Index < 0 || Index >= En->NumEnums())
			{
				return false;
			}
			Out = En->GetValueByIndex(Index);
			return En->IsValidEnumValue(Out);
		}
		return false;
	};
	if (const FBoolProperty* B = CastField<FBoolProperty>(P))
	{
		if (!bIsBool && !bIsNumber)
		{
			OutWhy = TEXT("a boolean property takes true, false or a number");
			return false;
		}
		B->SetPropertyValue(Ptr, bIsBool ? bBool : Number != 0.0);
		return true;
	}
	if (const FEnumProperty* E = CastField<FEnumProperty>(P))
	{
		int64 V = 0;
		if (!E->GetUnderlyingProperty() || !EnumValue(E->GetEnum(), V))
		{
			OutWhy = TEXT("not one of the enum's values");
			return false;
		}
		E->GetUnderlyingProperty()->SetIntPropertyValue(Ptr, V);
		return true;
	}
	if (const FNumericProperty* N = CastField<FNumericProperty>(P))
	{
		if (const UEnum* En = N->GetIntPropertyEnum())
		{
			int64 V = 0;
			if (!EnumValue(En, V))
			{
				OutWhy = TEXT("not one of the enum's values");
				return false;
			}
			N->SetIntPropertyValue(Ptr, V);
			return true;
		}
		if (!bIsNumber && !bIsBool)
		{
			OutWhy = TEXT("a number property takes a number");
			return false;
		}
		const double V = bIsBool ? (bBool ? 1.0 : 0.0) : Number;
		if (N->IsFloatingPoint())
		{
			N->SetFloatingPointPropertyValue(Ptr, V);
		}
		else
		{
			N->SetIntPropertyValue(Ptr, (int64)FMath::RoundToDouble(V));
		}
		return true;
	}
	if (!bIsString)
	{
		OutWhy = TEXT("a name, string or text property takes a string");
	}
	else if (const FStrProperty* S = CastField<FStrProperty>(P))
	{
		S->SetPropertyValue(Ptr, Text);
		return true;
	}
	else if (const FNameProperty* Nm = CastField<FNameProperty>(P))
	{
		Nm->SetPropertyValue(Ptr, FName(*Text));
		return true;
	}
	else if (const FTextProperty* T = CastField<FTextProperty>(P))
	{
		T->SetPropertyValue(Ptr, FText::FromString(Text));
		return true;
	}
	else
	{
		OutWhy = FString::Printf(TEXT("a %s property can't be set"), *P->GetClass()->GetName());
	}
	return false;
}

bool WriteProp(UObject* Root, const FString& Path, const TSharedPtr<FJsonValue>& Value, FString& OutWhy)
{
	FProperty* P = nullptr;
	void* Ptr = nullptr;
	return ResolveWritable(Root, Path, P, Ptr, OutWhy) && AssignJson(P, Ptr, Value, OutWhy);
}

// ---------------------------------------------------------------- Slate widgets under the game viewport

/** SImage's brush is behind a protected accessor: call it through a member pointer taken in a derived scope. */
struct FTaskProbeImagePeek : public SImage
{
	static const FSlateBrush* Brush(const SImage& Image) { return (Image.*(&FTaskProbeImagePeek::GetImageAttribute))().Get(); }
};

static void WalkSlate(const TSharedRef<SWidget>& W, TFunctionRef<void(const TSharedRef<SWidget>&)> Visit, int32 Depth = 0)
{
	if (Depth > 256)
	{
		return;
	}
	Visit(W);
	FChildren* Children = W->GetChildren();
	if (!Children)
	{
		return;
	}
	for (int32 i = 0; i < Children->Num(); ++i)
	{
		WalkSlate(Children->GetChildAt(i), Visit, Depth + 1);
	}
}

static bool SlateVisible(const TSharedRef<SWidget>& W)
{
	TSharedPtr<SWidget> Cur = W;
	for (int32 Depth = 0; Cur.IsValid() && Depth < 512; ++Depth)
	{
		if (!Cur->GetVisibility().IsVisible() || Cur->GetRenderOpacity() <= 0.001f)
		{
			return false;
		}
		Cur = Cur->GetParentWidget();
	}
	return true;
}

static TSharedPtr<FJsonValue> SlateField(const TSharedRef<SWidget>& W, const FString& F)
{
	const FName Type = W->GetType();
	if (F == TEXT("count"))
	{
		return Num(1.0);
	}
	if (F == TEXT("visible"))
	{
		return Num(SlateVisible(W) ? 1.0 : 0.0);
	}
	if (IsRectField(F))
	{
		return RectField(W->GetTickSpaceGeometry(), F);
	}
	if (F == TEXT("text"))
	{
		return Type == TEXT("STextBlock") ? Str(StaticCastSharedRef<STextBlock>(W)->GetText().ToString()) : Null();
	}
	if (F == TEXT("has_brush") || F == TEXT("brush"))
	{
		return Type == TEXT("SImage") ? BrushFields(FTaskProbeImagePeek::Brush(StaticCastSharedRef<SImage>(W).Get()), F) : Null();
	}
	return Null();
}

FString LabelKey(const FString& Text)
{
	FString Out;
	bool bGap = false;
	for (int32 i = 0; i < Text.Len(); ++i)
	{
		const TCHAR C = Text[i];
		if (!FChar::IsAlnum(C))
		{
			bGap = true;
			continue;
		}
		if (bGap && !Out.IsEmpty())
		{
			Out.AppendChar(TEXT('_'));
		}
		Out.AppendChar(FChar::ToLower(C));
		bGap = false;
	}
	return Out;
}

TSharedPtr<SWidget> FindSlateButton(const FString& Want, FVector2D& OutCentre, FString& OutLabel)
{
	const UGameViewportClient* GVC = GEngine ? GEngine->GameViewport.Get() : nullptr;
	const TSharedPtr<SViewport> Root = GVC ? GVC->GetGameViewportWidget() : nullptr;
	const FString Key = LabelKey(Want);
	TSharedPtr<SWidget> Found;
	if (!Root.IsValid() || Key.IsEmpty())
	{
		return Found;
	}
	WalkSlate(Root.ToSharedRef(), [&](const TSharedRef<SWidget>& W)
	{
		const FString Type = W->GetTypeAsString();
		if (Found.IsValid() || !Type.EndsWith(TEXT("Button")) || !W->IsEnabled() || !SlateVisible(W))
		{
			return;
		}
		const FGeometry& G = W->GetTickSpaceGeometry();
		const FVector2D Size(G.GetAbsoluteSize());
		if (Size.X <= 0.0 || Size.Y <= 0.0)
		{
			return;  // never laid out: nothing a player could click
		}
		// its captions: every text block inside it, each alone and all of them in order
		TArray<FString> Texts;
		WalkSlate(W, [&](const TSharedRef<SWidget>& In)
		{
			if (In->GetType() == TEXT("STextBlock"))
			{
				Texts.Add(StaticCastSharedRef<STextBlock>(In)->GetText().ToString());
			}
		});
		FString Label;
		for (const FString& T : Texts)
		{
			if (Label.IsEmpty() && LabelKey(T) == Key)
			{
				Label = FString::Printf(TEXT("text \"%s\""), *T);
			}
		}
		if (Label.IsEmpty() && Texts.Num() > 1 && LabelKey(FString::Join(Texts, TEXT(" "))) == Key)
		{
			Label = FString::Printf(TEXT("text \"%s\""), *FString::Join(Texts, TEXT(" ")));
		}
		const FName Tag = W->GetTag();
		if (Label.IsEmpty() && !Tag.IsNone() && LabelKey(Tag.ToString()) == Key)
		{
			Label = FString::Printf(TEXT("tag %s"), *Tag.ToString());
		}
		if (Label.IsEmpty() && (LabelKey(Type) == Key || (Type.StartsWith(TEXT("S"), ESearchCase::CaseSensitive) && LabelKey(Type.Mid(1)) == Key)))
		{
			Label = FString::Printf(TEXT("type %s"), *Type);
		}
		if (!Label.IsEmpty())
		{
			Found = W;
			OutCentre = FVector2D(G.GetAbsolutePosition()) + Size * 0.5;
			OutLabel = FString::Printf(TEXT("%s, %s"), *Type, *Label);
		}
	});
	return Found;
}

// ---------------------------------------------------------------- grading

/** The colour-pipeline settings the plugin reports, from a view's final post-process settings or blended here. */
struct FGrade
{
	float WhiteTemp = 6500.f;
	float WhiteTint = 0.f;
	FVector4 Saturation = FVector4(1, 1, 1, 1);
	FVector4 Contrast = FVector4(1, 1, 1, 1);
	FVector4 Gamma = FVector4(1, 1, 1, 1);
	FVector4 Gain = FVector4(1, 1, 1, 1);
	FVector4 Offset = FVector4(0, 0, 0, 0);
	float ExposureBias = 0.f;
	float ExposureMin = 0.f;
	float ExposureMax = 0.f;
	int32 ExposureMethod = 0;
	float LutIntensity = 1.f;
	TWeakObjectPtr<UTexture> Lut;

	void From(const FPostProcessSettings& P)
	{
		WhiteTemp = P.WhiteTemp;
		WhiteTint = P.WhiteTint;
		Saturation = P.ColorSaturation;
		Contrast = P.ColorContrast;
		Gamma = P.ColorGamma;
		Gain = P.ColorGain;
		Offset = P.ColorOffset;
		ExposureBias = P.AutoExposureBias;
		ExposureMin = P.AutoExposureMinBrightness;
		ExposureMax = P.AutoExposureMaxBrightness;
		ExposureMethod = (int32)P.AutoExposureMethod.GetValue();
		LutIntensity = P.ColorGradingIntensity;
		Lut = P.ColorGradingLUT.Get();
	}

	static FVector4 Lerp4(const FVector4& A, const FVector4& B, float W) { return A + (B - A) * (double)W; }

	/** As FSceneView::OverridePostProcessSettings: overridden values lerp toward the source by its weight. */
	void Blend(const FPostProcessSettings& S, float W)
	{
		if (W <= 0.f)
		{
			return;
		}
		if (S.bOverride_WhiteTemp) WhiteTemp = FMath::Lerp(WhiteTemp, S.WhiteTemp, W);
		if (S.bOverride_WhiteTint) WhiteTint = FMath::Lerp(WhiteTint, S.WhiteTint, W);
		if (S.bOverride_ColorSaturation) Saturation = Lerp4(Saturation, S.ColorSaturation, W);
		if (S.bOverride_ColorContrast) Contrast = Lerp4(Contrast, S.ColorContrast, W);
		if (S.bOverride_ColorGamma) Gamma = Lerp4(Gamma, S.ColorGamma, W);
		if (S.bOverride_ColorGain) Gain = Lerp4(Gain, S.ColorGain, W);
		if (S.bOverride_ColorOffset) Offset = Lerp4(Offset, S.ColorOffset, W);
		if (S.bOverride_AutoExposureBias) ExposureBias = FMath::Lerp(ExposureBias, S.AutoExposureBias, W);
		if (S.bOverride_AutoExposureMinBrightness) ExposureMin = FMath::Lerp(ExposureMin, S.AutoExposureMinBrightness, W);
		if (S.bOverride_AutoExposureMaxBrightness) ExposureMax = FMath::Lerp(ExposureMax, S.AutoExposureMaxBrightness, W);
		if (S.bOverride_AutoExposureMethod && W >= 0.5f) ExposureMethod = (int32)S.AutoExposureMethod.GetValue();
		if (S.bOverride_ColorGradingIntensity) LutIntensity = FMath::Lerp(LutIntensity, S.ColorGradingIntensity, W);
		if (S.bOverride_ColorGradingLUT && W >= 0.5f) Lut = S.ColorGradingLUT.Get();
	}
};

/** A light that lights the scene, as the renderer adds it: registered, affecting the world, drawn in game (visible, not
 *  hidden in game, its owner not hidden: a hidden light is never added to the scene) and of an intensity above 0. */
static bool LightOn(const ULightComponentBase* L, const UWorld* World)
{
	const AActor* Owner = L ? L->GetOwner() : nullptr;
	return L && L->GetWorld() == World && !L->HasAnyFlags(RF_ClassDefaultObject | RF_ArchetypeObject) && L->IsRegistered() &&
		L->bAffectsWorld && L->ShouldComponentAddToScene() && L->Intensity > 0.f && L->IsVisible() && !L->bHiddenInGame &&
		!(Owner && Owner->IsHidden());
}

static FString OwnerName(const UActorComponent* C)
{
	const AActor* Owner = C ? C->GetOwner() : nullptr;
	return Owner ? Owner->GetName() : (C ? C->GetName() : FString());
}

// ---------------------------------------------------------------- pieces, screen

/** A procedural mesh component's sections (UProceduralMeshComponent, read by reflection so the game needn't enable its
 *  plugin): each section with triangles, by its local bounds, whether it is visible and its triangles (index count / 3;
 *  0 when the index buffer can't be read). False when C has no sections array (not a procedural mesh). */
static bool ProcSections(UMeshComponent* C, TFunctionRef<void(const FBox&, bool, int64)> Visit)
{
	const FArrayProperty* AP = FindFProperty<FArrayProperty>(C->GetClass(), TEXT("ProcMeshSections"));
	const FStructProperty* SP = AP ? CastField<FStructProperty>(AP->Inner) : nullptr;
	if (!SP || !SP->Struct)
	{
		return false;
	}
	const FArrayProperty* Indices = FindFProperty<FArrayProperty>(SP->Struct, TEXT("ProcIndexBuffer"));
	const FStructProperty* BoxProp = FindFProperty<FStructProperty>(SP->Struct, TEXT("SectionLocalBox"));
	const FBoolProperty* VisibleProp = FindFProperty<FBoolProperty>(SP->Struct, TEXT("bSectionVisible"));
	FScriptArrayHelper Sections(AP, AP->ContainerPtrToValuePtr<void>(C));
	for (int32 i = 0; i < Sections.Num(); ++i)
	{
		uint8* Section = Sections.GetRawPtr(i);
		int64 Triangles = 0;
		if (Indices)
		{
			FScriptArrayHelper Tris(Indices, Indices->ContainerPtrToValuePtr<void>(Section));
			if (Tris.Num() == 0)
			{
				continue;  // an empty section draws nothing
			}
			Triangles = Tris.Num() / 3;
		}
		FBox Box(ForceInit);
		if (BoxProp && BoxProp->Struct && BoxProp->Struct->GetName().StartsWith(TEXT("Box")) && BoxProp->GetElementSize() == sizeof(FBox))
		{
			Box = *BoxProp->ContainerPtrToValuePtr<FBox>(Section);
		}
		Visit(Box, !VisibleProp || VisibleProp->GetPropertyValue_InContainer(Section), Triangles);
	}
	return true;
}

/** The name of a mesh component's mesh asset (a static or skinned mesh), empty when it has none or isn't one. */
static FString MeshAssetName(const UMeshComponent* C)
{
	if (const UStaticMeshComponent* SM = Cast<UStaticMeshComponent>(C))
	{
		return SM->GetStaticMesh() ? SM->GetStaticMesh()->GetName() : FString();
	}
	if (const USkinnedMeshComponent* SK = Cast<USkinnedMeshComponent>(C))
	{
		return SK->GetSkinnedAsset() ? SK->GetSkinnedAsset()->GetName() : FString();
	}
	return FString();
}

/** The triangles one piece of a static or skeletal mesh component draws at full detail (one instance of an instanced
 *  one): a Nanite mesh's own triangles (its LOD0 is a reduced fallback), else LOD0's; 0 for any other mesh component
 *  or a mesh without render data. */
static int64 PieceTriangles(const UMeshComponent* C)
{
	if (const UStaticMeshComponent* SM = Cast<UStaticMeshComponent>(C))
	{
		const UStaticMesh* Mesh = SM->GetStaticMesh();
		if (!Mesh)
		{
			return 0;
		}
		const int32 Nanite = Mesh->HasValidNaniteData() ? Mesh->GetNumNaniteTriangles() : 0;
		return Nanite > 0 ? Nanite : Mesh->GetNumTriangles(0);
	}
	if (const USkinnedMeshComponent* SK = Cast<USkinnedMeshComponent>(C))
	{
		const USkinnedAsset* Asset = SK->GetSkinnedAsset();
		const FSkeletalMeshRenderData* Data = Asset ? Asset->GetResourceForRendering() : nullptr;
		return Data && Data->LODRenderData.Num() > 0 ? Data->LODRenderData[0].GetTotalFaces() : 0;
	}
	return 0;
}

// lit, glow: whether something gives off light and how much, one reading over every way a build makes light (a light
// component, a mesh drawn with an emissive or unlit material)

static constexpr double EmissiveFloor = 0.01;  // lit: an emissive surface brighter than this (luminance; emissive 1 = 1 cd/m2)
static constexpr int32 GraphBudget = 4096;  // expressions one material reading visits at most
static constexpr uint8 GlowLight = 1, GlowEmissive = 2, GlowUnlit = 4, GlowEffect = 8;  // glow_sources

static bool IsGlowField(const FString& F) { return F == TEXT("lit") || F == TEXT("glow"); }

static double Luminance(double R, double G, double B) { return 0.2126 * R + 0.7152 * G + 0.0722 * B; }

/** What a material value can be, per channel: the lowest and highest (N channels, 1-4; one channel stands for all). */
struct FRange
{
	double Lo[4] = {0.0, 0.0, 0.0, 0.0};
	double Hi[4] = {0.0, 0.0, 0.0, 0.0};
	int32 N = 1;
	double L(int32 i) const { return Lo[FMath::Min(i, N - 1)]; }
	double H(int32 i) const { return Hi[FMath::Min(i, N - 1)]; }
	bool Exact() const
	{
		for (int32 i = 0; i < N; ++i)
		{
			if (Lo[i] != Hi[i]) return false;
		}
		return true;
	}
	static FRange Of(double Low, double High, int32 Channels = 1)
	{
		FRange R;
		R.N = Channels;
		for (int32 i = 0; i < 4; ++i)
		{
			R.Lo[i] = Low;
			R.Hi[i] = High;
		}
		return R;
	}
	static FRange Color(const FLinearColor& C, int32 Channels)
	{
		FRange R;
		R.N = Channels;
		const double V[4] = {C.R, C.G, C.B, C.A};
		for (int32 i = 0; i < 4; ++i)
		{
			R.Lo[i] = R.Hi[i] = V[i];
		}
		return R;
	}
};

/** Each channel of A and B combined by Fn(aLo, aHi, bLo, bHi, Lo, Hi). */
template <typename FnType>
static FRange Combine(const FRange& A, const FRange& B, FnType Fn)
{
	FRange R;
	R.N = FMath::Max(A.N, B.N);
	for (int32 i = 0; i < R.N; ++i)
	{
		Fn(A.L(i), A.H(i), B.L(i), B.H(i), R.Lo[i], R.Hi[i]);
	}
	return R;
}

static void Span(std::initializer_list<double> Values, double& Lo, double& Hi)
{
	Lo = TNumericLimits<double>::Max();
	Hi = TNumericLimits<double>::Lowest();
	for (const double V : Values)
	{
		if (!FMath::IsFinite(V))
		{
			Lo = 0.0;  // unbounded (a division by 0, a power of 0 below 0): read as an unknown input
			Hi = 1.0;
			return;
		}
		Lo = FMath::Min(Lo, V);
		Hi = FMath::Max(Hi, V);
	}
}

static FRange Mul(const FRange& A, const FRange& B)
{
	return Combine(A, B, [](double a, double b, double c, double d, double& Lo, double& Hi) { Span({a * c, a * d, b * c, b * d}, Lo, Hi); });
}

static FRange Add(const FRange& A, const FRange& B)
{
	return Combine(A, B, [](double a, double b, double c, double d, double& Lo, double& Hi) { Lo = a + c; Hi = b + d; });
}

static FRange Sub(const FRange& A, const FRange& B)
{
	return Combine(A, B, [](double a, double b, double c, double d, double& Lo, double& Hi) { Lo = a - d; Hi = b - c; });
}

static FRange Div(const FRange& A, const FRange& B)
{
	return Combine(A, B, [](double a, double b, double c, double d, double& Lo, double& Hi)
	{
		if (c > 0.0 || d < 0.0)
		{
			Span({a / c, a / d, b / c, b / d}, Lo, Hi);
		}
		else
		{
			Lo = 0.0;  // a divisor that can be 0
			Hi = 1.0;
		}
	});
}

static FRange MaxOf(const FRange& A, const FRange& B)
{
	return Combine(A, B, [](double a, double b, double c, double d, double& Lo, double& Hi) { Lo = FMath::Max(a, c); Hi = FMath::Max(b, d); });
}

static FRange MinOf(const FRange& A, const FRange& B)
{
	return Combine(A, B, [](double a, double b, double c, double d, double& Lo, double& Hi) { Lo = FMath::Min(a, c); Hi = FMath::Min(b, d); });
}

/** Either value: a switch the reading can't settle. */
static FRange Hull(const FRange& A, const FRange& B)
{
	return Combine(A, B, [](double a, double b, double c, double d, double& Lo, double& Hi) { Lo = FMath::Min(a, c); Hi = FMath::Max(b, d); });
}

/** The channels a mask keeps, in order (none set: all of them). */
static FRange Pick(const FRange& V, bool R, bool G, bool B, bool A)
{
	const bool Keep[4] = {R, G, B, A};
	FRange Out;
	Out.N = 0;
	for (int32 i = 0; i < 4; ++i)
	{
		if (Keep[i])
		{
			Out.Lo[Out.N] = V.L(i);
			Out.Hi[Out.N] = V.H(i);
			++Out.N;
		}
	}
	return Out.N > 0 ? Out : V;
}

static FRange Append(const FRange& A, const FRange& B)
{
	FRange Out = A;
	for (int32 i = 0; i < B.N && Out.N < 4; ++i)
	{
		Out.Lo[Out.N] = B.Lo[i];
		Out.Hi[Out.N] = B.Hi[i];
		++Out.N;
	}
	return Out;
}

/** The emissive of a value, as a luminance: its highest red, green and blue (one channel: grey), never below 0. */
static double RangeLuminance(const FRange& V)
{
	return FMath::Max(0.0, Luminance(FMath::Max(V.H(0), 0.0), FMath::Max(V.H(1), 0.0), FMath::Max(V.H(2), 0.0)));
}

#if WITH_EDITORONLY_DATA
/** The material function call a graph is being read inside, for its inputs. */
struct FGraphCall
{
	const UMaterialExpressionMaterialFunctionCall* Call = nullptr;
	const FGraphCall* Parent = nullptr;
};

/** A material graph being read: whose parameter values (a material instance's, a dynamic one's overrides included),
 *  the primitive's custom data and the world's parameter collections. */
struct FGraph
{
	const UMaterialInterface* Material = nullptr;
	const UPrimitiveComponent* Prim = nullptr;
	const UWorld* World = nullptr;
	int32 Budget = GraphBudget;
	bool bUnknown = false;  // an input it couldn't evaluate was on the way: the value is a bound, not the value
};

/** An input the reading can't evaluate (a texture, vertex colour, time, a custom node): at most white, and the graph's
 *  value a bound from then on. Which inputs those are depends on the graph alone, never on parameter values, so a
 *  material is read the same way at every sample. */
static FRange Unknown(FGraph& G)
{
	G.bUnknown = true;
	return FRange::Of(0.0, 1.0, 4);
}

static FRange Eval(FGraph& G, const FExpressionInput& In, const FGraphCall* Call);
static FRange EmissiveOf(FGraph& G, const FExpressionInput& In, const FGraphCall* Call);

/** An input's value, or Default when nothing is connected to it. */
static FRange EvalOr(FGraph& G, const FExpressionInput& In, const FGraphCall* Call, double Default)
{
	return In.Expression ? Eval(G, In, Call) : FRange::Of(Default, Default);
}

/** What a call passes to a function input: its connected input, in the caller's graph; null when nothing is. */
static const FExpressionInput* CallInput(const UMaterialExpressionFunctionInput* X, const FGraphCall* Call)
{
	if (!Call || !Call->Call)
	{
		return nullptr;
	}
	for (const FFunctionExpressionInput& FI : Call->Call->FunctionInputs)
	{
		if ((FI.ExpressionInput == X || (X->Id.IsValid() && FI.ExpressionInputId == X->Id)) && FI.Input.Expression)
		{
			return &FI.Input;
		}
	}
	return nullptr;
}

static FRange FunctionInputValue(FGraph& G, const UMaterialExpressionFunctionInput* X, const FGraphCall* Call)
{
	if (const FExpressionInput* In = CallInput(X, Call))
	{
		return Eval(G, *In, Call->Parent);
	}
	if (X->Preview.Expression)
	{
		return Eval(G, X->Preview, Call);  // its default, in the function's own graph
	}
	return FRange::Color(FLinearColor(X->PreviewValue.X, X->PreviewValue.Y, X->PreviewValue.Z, X->PreviewValue.W), 4);
}

static bool SwitchValue(const FGraph& G, const UMaterialExpressionStaticBoolParameter* X)
{
	bool bValue = X->DefaultValue != 0;
	FGuid Id;
	if (G.Material)
	{
		G.Material->GetStaticSwitchParameterValue(FHashedMaterialParameterInfo(X->ParameterName), bValue, Id);
	}
	return bValue;
}

/** One expression's value at OutputIndex (its full value; the input reading it applies its own mask). */
static FRange Node(FGraph& G, UMaterialExpression* E, int32 OutputIndex, const FGraphCall* Call)
{
	if (const UMaterialExpressionConstant* X = Cast<UMaterialExpressionConstant>(E))
	{
		return FRange::Of(X->R, X->R);
	}
	if (const UMaterialExpressionConstant2Vector* X = Cast<UMaterialExpressionConstant2Vector>(E))
	{
		return FRange::Color(FLinearColor(X->R, X->G, 0.f, 0.f), 2);
	}
	if (const UMaterialExpressionConstant3Vector* X = Cast<UMaterialExpressionConstant3Vector>(E))
	{
		return FRange::Color(X->Constant, 3);
	}
	if (const UMaterialExpressionConstant4Vector* X = Cast<UMaterialExpressionConstant4Vector>(E))
	{
		return FRange::Color(X->Constant, 4);
	}
	if (const UMaterialExpressionScalarParameter* X = Cast<UMaterialExpressionScalarParameter>(E))
	{
		// its value now: the primitive's custom data, else the material instance's (a dynamic one's override included)
		float V = X->DefaultValue;
		if (X->bUseCustomPrimitiveData)
		{
			const TArray<float>& Data = G.Prim ? G.Prim->GetCustomPrimitiveData().Data : TArray<float>();
			V = Data.IsValidIndex(X->PrimitiveDataIndex) ? Data[X->PrimitiveDataIndex] : V;
		}
		else if (G.Material)
		{
			G.Material->GetScalarParameterValue(FHashedMaterialParameterInfo(X->ParameterName), V);
		}
		return FRange::Of(V, V);
	}
	if (const UMaterialExpressionVectorParameter* X = Cast<UMaterialExpressionVectorParameter>(E))
	{
		FLinearColor C = X->DefaultValue;
		if (X->bUseCustomPrimitiveData)
		{
			const TArray<float>& Data = G.Prim ? G.Prim->GetCustomPrimitiveData().Data : TArray<float>();
			float* Out[4] = {&C.R, &C.G, &C.B, &C.A};
			for (int32 i = 0; i < 4; ++i)
			{
				if (Data.IsValidIndex(X->PrimitiveDataIndex + i))
				{
					*Out[i] = Data[X->PrimitiveDataIndex + i];
				}
			}
		}
		else if (G.Material)
		{
			G.Material->GetVectorParameterValue(FHashedMaterialParameterInfo(X->ParameterName), C);
		}
		return FRange::Color(C, 4);
	}
	if (const UMaterialExpressionStaticSwitchParameter* X = Cast<UMaterialExpressionStaticSwitchParameter>(E))
	{
		return SwitchValue(G, X) ? EvalOr(G, X->A, Call, 0.0) : EvalOr(G, X->B, Call, 0.0);
	}
	if (const UMaterialExpressionStaticBoolParameter* X = Cast<UMaterialExpressionStaticBoolParameter>(E))
	{
		const double V = SwitchValue(G, X) ? 1.0 : 0.0;
		return FRange::Of(V, V);
	}
	if (const UMaterialExpressionStaticSwitch* X = Cast<UMaterialExpressionStaticSwitch>(E))
	{
		const FRange V = EvalOr(G, X->Value, Call, X->DefaultValue ? 1.0 : 0.0);
		if (V.Exact())
		{
			return V.Lo[0] != 0.0 ? EvalOr(G, X->A, Call, 0.0) : EvalOr(G, X->B, Call, 0.0);
		}
		return Hull(EvalOr(G, X->A, Call, 0.0), EvalOr(G, X->B, Call, 0.0));
	}
	if (const UMaterialExpressionCollectionParameter* X = Cast<UMaterialExpressionCollectionParameter>(E))
	{
		// a material parameter collection's value now, in this world
		const UMaterialParameterCollectionInstance* Inst = X->Collection && G.World ? G.World->GetParameterCollectionInstance(X->Collection) : nullptr;
		float S = 0.f;
		FLinearColor C;
		if (Inst && Inst->GetScalarParameterValue(X->ParameterName, S))
		{
			return FRange::Of(S, S);
		}
		if (Inst && Inst->GetVectorParameterValue(X->ParameterName, C))
		{
			return FRange::Color(C, 4);
		}
		return Unknown(G);
	}
	if (const UMaterialExpressionMultiply* X = Cast<UMaterialExpressionMultiply>(E))
	{
		return Mul(EvalOr(G, X->A, Call, X->ConstA), EvalOr(G, X->B, Call, X->ConstB));
	}
	if (const UMaterialExpressionAdd* X = Cast<UMaterialExpressionAdd>(E))
	{
		return Add(EvalOr(G, X->A, Call, X->ConstA), EvalOr(G, X->B, Call, X->ConstB));
	}
	if (const UMaterialExpressionSubtract* X = Cast<UMaterialExpressionSubtract>(E))
	{
		return Sub(EvalOr(G, X->A, Call, X->ConstA), EvalOr(G, X->B, Call, X->ConstB));
	}
	if (const UMaterialExpressionDivide* X = Cast<UMaterialExpressionDivide>(E))
	{
		return Div(EvalOr(G, X->A, Call, X->ConstA), EvalOr(G, X->B, Call, X->ConstB));
	}
	if (const UMaterialExpressionMax* X = Cast<UMaterialExpressionMax>(E))
	{
		return MaxOf(EvalOr(G, X->A, Call, X->ConstA), EvalOr(G, X->B, Call, X->ConstB));
	}
	if (const UMaterialExpressionMin* X = Cast<UMaterialExpressionMin>(E))
	{
		return MinOf(EvalOr(G, X->A, Call, X->ConstA), EvalOr(G, X->B, Call, X->ConstB));
	}
	if (const UMaterialExpressionLinearInterpolate* X = Cast<UMaterialExpressionLinearInterpolate>(E))
	{
		// a + t (b - a) is linear in each of a, b and t, so its bounds are at their bounds' corners
		const FRange A = EvalOr(G, X->A, Call, X->ConstA), B = EvalOr(G, X->B, Call, X->ConstB), T = EvalOr(G, X->Alpha, Call, X->ConstAlpha);
		FRange R;
		R.N = FMath::Max3(A.N, B.N, T.N);
		for (int32 i = 0; i < R.N; ++i)
		{
			const double a0 = A.L(i), a1 = A.H(i), b0 = B.L(i), b1 = B.H(i), t0 = T.L(i), t1 = T.H(i);
			Span({a0 + t0 * (b0 - a0), a0 + t0 * (b1 - a0), a1 + t0 * (b0 - a1), a1 + t0 * (b1 - a1),
				a0 + t1 * (b0 - a0), a0 + t1 * (b1 - a0), a1 + t1 * (b0 - a1), a1 + t1 * (b1 - a1)}, R.Lo[i], R.Hi[i]);
		}
		return R;
	}
	if (const UMaterialExpressionClamp* X = Cast<UMaterialExpressionClamp>(E))
	{
		// clamp is increasing in its input, its min and its max
		const FRange V = EvalOr(G, X->Input, Call, 0.0), Lo = EvalOr(G, X->Min, Call, X->MinDefault), Hi = EvalOr(G, X->Max, Call, X->MaxDefault);
		FRange R;
		R.N = FMath::Max3(V.N, Lo.N, Hi.N);
		for (int32 i = 0; i < R.N; ++i)
		{
			const bool bMin = X->ClampMode != CMODE_ClampMax, bMax = X->ClampMode != CMODE_ClampMin;
			double L = V.L(i), H = V.H(i);
			if (bMin) { L = FMath::Max(L, Lo.L(i)); H = FMath::Max(H, Lo.H(i)); }
			if (bMax) { L = FMath::Min(L, Hi.L(i)); H = FMath::Min(H, Hi.H(i)); }
			R.Lo[i] = L;
			R.Hi[i] = H;
		}
		return R;
	}
	if (const UMaterialExpressionSaturate* X = Cast<UMaterialExpressionSaturate>(E))
	{
		return MinOf(MaxOf(EvalOr(G, X->Input, Call, 0.0), FRange::Of(0.0, 0.0)), FRange::Of(1.0, 1.0));
	}
	if (const UMaterialExpressionPower* X = Cast<UMaterialExpressionPower>(E))
	{
		return Combine(EvalOr(G, X->Base, Call, 0.0), EvalOr(G, X->Exponent, Call, X->ConstExponent),
			[](double a, double b, double c, double d, double& Lo, double& Hi)
			{
				a = FMath::Max(a, 0.0);  // the shader's pow of a negative base is undefined
				b = FMath::Max(b, 0.0);
				Span({FMath::Pow(a, c), FMath::Pow(a, d), FMath::Pow(b, c), FMath::Pow(b, d)}, Lo, Hi);
			});
	}
	if (const UMaterialExpressionOneMinus* X = Cast<UMaterialExpressionOneMinus>(E))
	{
		return Sub(FRange::Of(1.0, 1.0), EvalOr(G, X->Input, Call, 0.0));
	}
	if (const UMaterialExpressionAbs* X = Cast<UMaterialExpressionAbs>(E))
	{
		FRange V = EvalOr(G, X->Input, Call, 0.0);
		for (int32 i = 0; i < V.N; ++i)
		{
			const double L = V.Lo[i], H = V.Hi[i];
			V.Lo[i] = L >= 0.0 ? L : H <= 0.0 ? -H : 0.0;
			V.Hi[i] = FMath::Max(FMath::Abs(L), FMath::Abs(H));
		}
		return V;
	}
	if (E->IsA<UMaterialExpressionSine>() || E->IsA<UMaterialExpressionCosine>())
	{
		const bool bSine = E->IsA<UMaterialExpressionSine>();
		const UMaterialExpressionSine* S = Cast<UMaterialExpressionSine>(E);
		const UMaterialExpressionCosine* C = Cast<UMaterialExpressionCosine>(E);
		FRange V = EvalOr(G, bSine ? S->Input : C->Input, Call, 0.0);
		if (!V.Exact())
		{
			return FRange::Of(-1.0, 1.0);
		}
		const double Period = bSine ? S->Period : C->Period;
		for (int32 i = 0; i < V.N; ++i)
		{
			const double X = Period > 0.0 ? V.Lo[i] * 2.0 * UE_DOUBLE_PI / Period : V.Lo[i];
			V.Lo[i] = V.Hi[i] = bSine ? FMath::Sin(X) : FMath::Cos(X);
		}
		return V;
	}
	if (const UMaterialExpressionComponentMask* X = Cast<UMaterialExpressionComponentMask>(E))
	{
		return Pick(EvalOr(G, X->Input, Call, 0.0), X->R, X->G, X->B, X->A);
	}
	if (const UMaterialExpressionAppendVector* X = Cast<UMaterialExpressionAppendVector>(E))
	{
		return Append(EvalOr(G, X->A, Call, 0.0), EvalOr(G, X->B, Call, 0.0));
	}
	if (const UMaterialExpressionReroute* X = Cast<UMaterialExpressionReroute>(E))
	{
		return EvalOr(G, X->Input, Call, 0.0);
	}
	if (const UMaterialExpressionNamedRerouteDeclaration* X = Cast<UMaterialExpressionNamedRerouteDeclaration>(E))
	{
		return EvalOr(G, X->Input, Call, 0.0);
	}
	if (const UMaterialExpressionNamedRerouteUsage* X = Cast<UMaterialExpressionNamedRerouteUsage>(E))
	{
		return X->Declaration ? EvalOr(G, X->Declaration->Input, Call, 0.0) : Unknown(G);
	}
	if (const UMaterialExpressionMaterialFunctionCall* X = Cast<UMaterialExpressionMaterialFunctionCall>(E))
	{
		const UMaterialExpressionFunctionOutput* Out = X->FunctionOutputs.IsValidIndex(OutputIndex) ? X->FunctionOutputs[OutputIndex].ExpressionOutput.Get() : nullptr;
		const FGraphCall Inner{X, Call};
		return Out ? EvalOr(G, Out->A, &Inner, 0.0) : Unknown(G);
	}
	if (const UMaterialExpressionFunctionInput* X = Cast<UMaterialExpressionFunctionInput>(E))
	{
		return FunctionInputValue(G, X, Call);
	}
	if (const UMaterialExpressionFunctionOutput* X = Cast<UMaterialExpressionFunctionOutput>(E))
	{
		return EvalOr(G, X->A, Call, 0.0);
	}
	return Unknown(G);
}

static FRange Eval(FGraph& G, const FExpressionInput& In, const FGraphCall* Call)
{
	UMaterialExpression* E = In.Expression;
	if (!E)
	{
		return FRange::Of(0.0, 0.0);
	}
	if (--G.Budget < 0)
	{
		return Unknown(G);
	}
	const FRange V = Node(G, E, In.OutputIndex, Call);
	return In.Mask ? Pick(V, In.MaskR != 0, In.MaskG != 0, In.MaskB != 0, In.MaskA != 0) : V;
}

/** The emissive a material-attributes or Substrate value carries: a MakeMaterialAttributes' or a BSDF's own emissive
 *  input, either attribute set of a blend, the sum over a Substrate operator's inputs (mixing, layering, adding). */
static FRange EmissiveOf(FGraph& G, const FExpressionInput& In, const FGraphCall* Call)
{
	UMaterialExpression* E = In.Expression;
	if (!E)
	{
		return FRange::Of(0.0, 0.0);
	}
	if (--G.Budget < 0)
	{
		return Unknown(G);
	}
	if (const UMaterialExpressionMakeMaterialAttributes* X = Cast<UMaterialExpressionMakeMaterialAttributes>(E))
	{
		return EvalOr(G, X->EmissiveColor, Call, 0.0);
	}
	if (const UMaterialExpressionBlendMaterialAttributes* X = Cast<UMaterialExpressionBlendMaterialAttributes>(E))
	{
		G.bUnknown = true;  // either attribute set: a bound
		return Hull(EmissiveOf(G, X->A, Call), EmissiveOf(G, X->B, Call));
	}
	if (const UMaterialExpressionReroute* X = Cast<UMaterialExpressionReroute>(E))
	{
		return EmissiveOf(G, X->Input, Call);
	}
	if (const UMaterialExpressionNamedRerouteDeclaration* X = Cast<UMaterialExpressionNamedRerouteDeclaration>(E))
	{
		return EmissiveOf(G, X->Input, Call);
	}
	if (const UMaterialExpressionNamedRerouteUsage* X = Cast<UMaterialExpressionNamedRerouteUsage>(E))
	{
		return X->Declaration ? EmissiveOf(G, X->Declaration->Input, Call) : Unknown(G);
	}
	if (const UMaterialExpressionMaterialFunctionCall* X = Cast<UMaterialExpressionMaterialFunctionCall>(E))
	{
		const UMaterialExpressionFunctionOutput* Out = X->FunctionOutputs.IsValidIndex(In.OutputIndex) ? X->FunctionOutputs[In.OutputIndex].ExpressionOutput.Get() : nullptr;
		const FGraphCall Inner{X, Call};
		return Out ? EmissiveOf(G, Out->A, &Inner) : Unknown(G);
	}
	if (const UMaterialExpressionFunctionInput* X = Cast<UMaterialExpressionFunctionInput>(E))
	{
		if (const FExpressionInput* Passed = CallInput(X, Call))
		{
			return EmissiveOf(G, *Passed, Call->Parent);
		}
		return X->Preview.Expression ? EmissiveOf(G, X->Preview, Call) : FRange::Of(0.0, 0.0);
	}
	if (const UMaterialExpressionFunctionOutput* X = Cast<UMaterialExpressionFunctionOutput>(E))
	{
		return EmissiveOf(G, X->A, Call);
	}
	if (E->IsA<UMaterialExpressionSubstrateBSDF>())
	{
		// a BSDF's emissive input (Slab, Unlit, Simple Clear Coat, ...), found by name
		const FStructProperty* P = FindFProperty<FStructProperty>(E->GetClass(), TEXT("EmissiveColor"));
		if (P && P->Struct && P->Struct->GetFName() == TEXT("ExpressionInput"))
		{
			return EvalOr(G, *P->ContainerPtrToValuePtr<FExpressionInput>(E), Call, 0.0);
		}
		FRange Sum = FRange::Of(0.0, 0.0);
		for (FExpressionInputIterator It{E}; It; ++It)
		{
			if (It->Expression && (It->Expression->IsA<UMaterialExpressionSubstrateBSDF>() || It->Expression->IsA<UMaterialExpressionMaterialFunctionCall>() ||
				It->Expression->IsA<UMaterialExpressionRerouteBase>()))
			{
				Sum = Add(Sum, EmissiveOf(G, *It.Input, Call));
			}
		}
		return Sum;
	}
	return Unknown(G);  // SetMaterialAttributes and other attribute nodes
}
#endif  // WITH_EDITORONLY_DATA

/** A material's emissive from its graph (editor-only data, there in an uncooked -game play): the base material's
 *  emissive input evaluated with the instance's parameter values now; bExact when every input on the way could be
 *  evaluated (else Out is the bound). False without the graph (a cooked build). */
static bool GraphEmissive(const UMaterialInterface* MI, const UPrimitiveComponent* Prim, const UWorld* World, double& Out, bool& bExact)
{
#if WITH_EDITORONLY_DATA
	const UMaterial* Base = MI ? MI->GetMaterial() : nullptr;
	const UMaterialEditorOnlyData* Ed = Base ? Base->GetEditorOnlyData() : nullptr;
	if (!Ed)
	{
		return false;
	}
	FGraph G;
	G.Material = MI;
	G.Prim = Prim;
	G.World = World;
	FRange V;
	if (Base->bUseMaterialAttributes)
	{
		V = EmissiveOf(G, Ed->MaterialAttributes, nullptr);
	}
	else if (Ed->EmissiveColor.Expression)
	{
		V = Eval(G, Ed->EmissiveColor, nullptr);
	}
	else if (Ed->FrontMaterial.Expression)
	{
		V = EmissiveOf(G, Ed->FrontMaterial, nullptr);
	}
	else
	{
		V = Ed->EmissiveColor.UseConstant ? FRange::Color(Ed->EmissiveColor.Constant, 3) : FRange::Of(0.0, 0.0);
	}
	Out = RangeLuminance(V);
	bExact = !G.bUnknown;
	return true;
#else
	return false;
#endif
}

/** Without the graph (a cooked build): an emissive input left unconnected reads 0; a connected one by the material's
 *  parameters named for it (Emissive, Emission, Emit, Glow): the brightest such colour times every such scalar. False
 *  when it is connected and no parameter says how bright. */
static bool NamedEmissive(const UMaterialInterface* MI, double& Out)
{
	const UMaterial* Base = MI ? MI->GetMaterial() : nullptr;
	if (!Base)
	{
		return false;
	}
	if (!Base->bUseMaterialAttributes && !Base->IsPropertyConnected(MP_EmissiveColor) && !Base->HasSubstrateFrontMaterialConnected())
	{
		Out = 0.0;
		return true;
	}
	auto Named = [](const FName& N)
	{
		const FString S = N.ToString();
		return S.Contains(TEXT("Emissive")) || S.Contains(TEXT("Emission")) || S.Contains(TEXT("Emit")) || S.Contains(TEXT("Glow"));
	};
	bool bAny = false;
	double Strength = 1.0, Color = 1.0;
	bool bColor = false;
	TArray<FMaterialParameterInfo> Infos;
	TArray<FGuid> Ids;
	MI->GetAllScalarParameterInfo(Infos, Ids);
	for (const FMaterialParameterInfo& Info : Infos)
	{
		float V = 0.f;
		if (Named(Info.Name) && MI->GetScalarParameterValue(FHashedMaterialParameterInfo(Info), V))
		{
			Strength *= V;
			bAny = true;
		}
	}
	Infos.Reset();
	Ids.Reset();
	MI->GetAllVectorParameterInfo(Infos, Ids);
	for (const FMaterialParameterInfo& Info : Infos)
	{
		FLinearColor C;
		if (Named(Info.Name) && MI->GetVectorParameterValue(FHashedMaterialParameterInfo(Info), C))
		{
			const double L = Luminance(C.R, C.G, C.B);
			Color = bColor ? FMath::Max(Color, L) : L;
			bColor = bAny = true;
		}
	}
	Out = FMath::Max(0.0, Color * Strength);
	return bAny;
}

/** A material's emissive luminance now: from its graph, else by its parameters' names; false when neither can say.
 *  bExact: the graph was evaluated whole (no texture, custom node or other input it can only bound), so Out is the
 *  value, not a bound or a guess by names. */
static bool MaterialEmissive(const UMaterialInterface* MI, const UPrimitiveComponent* Prim, const UWorld* World, double& Out, bool& bExact)
{
	bExact = false;
	return GraphEmissive(MI, Prim, World, Out, bExact) || NamedEmissive(MI, Out);
}

static bool MaterialEmissive(const UMaterialInterface* MI, const UPrimitiveComponent* Prim, const UWorld* World, double& Out)
{
	bool bExact = false;
	return MaterialEmissive(MI, Prim, World, Out, bExact);
}

// ---------------------------------------------------------------- lit, glow: a mesh's emissive as rendered

static constexpr int32 GlowRenderSize = 128;  // pixels square, each view of a mesh
static constexpr int32 GlowRenderBudget = 64;  // meshes rendered per sample at most (each mesh once per sample)

/** The four views a mesh is rendered from: the directions to a regular tetrahedron's corners in its own frame, so each
 *  face of its local bounds box is seen from two of them at the same slant. */
static const FVector GlowViews[4] = {FVector(1.0, 1.0, 1.0), FVector(1.0, -1.0, -1.0), FVector(-1.0, 1.0, -1.0), FVector(-1.0, -1.0, 1.0)};

/** Show flags off in the render: every light and what light does (direct lights, the sky, global illumination,
 *  reflections, ambient occlusion, shadows), the sky, fog and clouds behind the mesh, and what blurs or rescales a
 *  frame. What is left in scene colour is what the mesh gives off itself: emissive and unlit shading. */
static const TCHAR* const GlowDarkFlags[] = {
	TEXT("DirectLighting"), TEXT("DeferredLighting"), TEXT("DirectionalLights"), TEXT("PointLights"), TEXT("SpotLights"),
	TEXT("RectLights"), TEXT("MegaLights"), TEXT("SkyLighting"), TEXT("GlobalIllumination"), TEXT("LumenGlobalIllumination"),
	TEXT("LumenReflections"), TEXT("ReflectionEnvironment"), TEXT("ScreenSpaceReflections"), TEXT("AmbientCubemap"),
	TEXT("AmbientOcclusion"), TEXT("ScreenSpaceAO"), TEXT("DistanceFieldAO"), TEXT("VolumetricLightmap"),
	TEXT("IndirectLightingCache"), TEXT("Specular"), TEXT("DynamicShadows"), TEXT("ContactShadows"), TEXT("CapsuleShadows"),
	TEXT("LightShafts"), TEXT("LightFunctions"), TEXT("Atmosphere"), TEXT("Fog"), TEXT("VolumetricFog"), TEXT("Cloud"),
	TEXT("TemporalAA"), TEXT("AntiAliasing"), TEXT("MotionBlur"), TEXT("Bloom"), TEXT("EyeAdaptation"), TEXT("LocalExposure"),
	TEXT("DepthOfField"), TEXT("Decals")};

/** A mesh's emissive as the renderer draws it: what its materials give off at that sample (custom nodes, textures,
 *  custom primitive data, dynamic parameters and time included), the same pixels a player's view gets before light
 *  is added. */
struct FGlowRendered
{
	bool bRead = false;
	double Mean = 0.0;  // luminance over its local bounds box, mean of the four views: summed luminance x pixel area / box area seen
	double Peak = 0.0;  // the brightest pixel's luminance
};

/** Renders one mesh at a time in isolation (a scene capture showing only it, from four fixed views around it,
 *  orthographic, its light-free scene colour in HDR) and reads the pixels back. One per query set; its capture and
 *  render targets are transient objects it keeps, registered with the world only while it renders, so no query ever
 *  sees them. */
class FGlowRender
{
public:
	void NewSample()
	{
		Cache.Reset();
		Budget = GlowRenderBudget;
	}

	/** False when nothing can be rendered (no renderer: -nullrhi; no scene; the budget spent; a material still compiling).
	 *  M is a mesh or a particle system component. */
	FGlowRendered Read(const UPrimitiveComponent* M, UWorld* World)
	{
		if (const FGlowRendered* Seen = Cache.Find(FObjectKey(M)))
		{
			return *Seen;
		}
		FGlowRendered R;
		if (Budget > 0 && World && World->Scene && FApp::CanEverRender() && Ready(M, World))
		{
			--Budget;
			R = Render(M, World);
		}
		Cache.Add(FObjectKey(M), R);
		return R;
	}

private:
	/** Its materials' shaders are there to draw with: one still compiling is finished first (an uncooked play compiles
	 *  them as they are first drawn; till then the renderer draws a default material in their place). */
	static bool Ready(const UPrimitiveComponent* M, const UWorld* World)
	{
		TArray<UMaterialInterface*> Used;
		M->GetUsedMaterials(Used);
		for (UMaterialInterface* MI : Used)
		{
			if (!MI || !MI->IsCompiling())
			{
				continue;
			}
			if (FMaterialResource* Res = World->Scene ? MI->GetMaterialResource(World->Scene->GetShaderPlatform()) : nullptr)
			{
				Res->FinishCompilation();
			}
			if (MI->IsCompiling())
			{
				return false;
			}
		}
		return true;
	}

	void Setup()
	{
		if (!Capture.IsValid())
		{
			USceneCaptureComponent2D* C = NewObject<USceneCaptureComponent2D>(GetTransientPackage(), NAME_None, RF_Transient);
			C->bCaptureEveryFrame = false;
			C->bCaptureOnMovement = false;
			C->bAlwaysPersistRenderingState = false;
			C->PrimitiveRenderMode = ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
			C->CaptureSource = SCS_SceneColorHDR;
			C->ProjectionType = ECameraProjectionMode::Orthographic;
			// exposure 1: the scene colour holds the emissive as the material gives it (1 = 1 cd/m2)
			C->PostProcessBlendWeight = 1.f;
			C->PostProcessSettings.bOverride_AutoExposureMethod = true;
			C->PostProcessSettings.AutoExposureMethod = AEM_Manual;
			C->PostProcessSettings.bOverride_AutoExposureBias = true;
			C->PostProcessSettings.AutoExposureBias = 0.f;
			C->PostProcessSettings.bOverride_AutoExposureApplyPhysicalCameraExposure = true;
			C->PostProcessSettings.AutoExposureApplyPhysicalCameraExposure = false;
			TArray<FEngineShowFlagsSetting> Settings;
			for (const TCHAR* Name : GlowDarkFlags)
			{
				FEngineShowFlagsSetting Setting;
				Setting.ShowFlagName = Name;
				Setting.Enabled = false;
				Settings.Add(Setting);
			}
			C->SetShowFlagSettings(Settings);
			Capture.Reset(C);
		}
		for (TStrongObjectPtr<UTextureRenderTarget2D>& T : Targets)
		{
			if (!T.IsValid())
			{
				UTextureRenderTarget2D* RT = NewObject<UTextureRenderTarget2D>(GetTransientPackage(), NAME_None, RF_Transient);
				RT->RenderTargetFormat = RTF_RGBA16f;
				RT->ClearColor = FLinearColor::Black;
				RT->bAutoGenerateMips = false;
				RT->InitAutoFormat(GlowRenderSize, GlowRenderSize);
				RT->UpdateResourceImmediate(true);
				T.Reset(RT);
			}
		}
	}

	static void DarkFlags(FEngineShowFlags& Flags)
	{
		for (const TCHAR* Name : GlowDarkFlags)
		{
			const int32 Index = FEngineShowFlags::FindIndexByName(Name);
			if (Index != INDEX_NONE)
			{
				Flags.SetSingleFlag(Index, false);
			}
		}
	}

	FGlowRendered Render(const UPrimitiveComponent* M, UWorld* World)
	{
		FGlowRendered R;
		Setup();
		USceneCaptureComponent2D* C = Capture.Get();
		// the mesh's local bounds box, in the world: its centre, size (cm) and the sphere around it
		const FTransform& X = M->GetComponentTransform();
		const FBoxSphereBounds Local = M->CalcBounds(FTransform::Identity);
		const FVector Size = Local.BoxExtent * 2.0 * X.GetScale3D().GetAbs();
		const FVector Centre = X.TransformPosition(Local.Origin);
		const double Radius = FMath::Max(Size.Size() / 2.0, 1.0);
		const double Width = Radius * 2.0 * 1.02;  // the box from any side, with a margin
		C->RegisterComponentWithWorld(World);
		DarkFlags(C->ShowFlags);
		C->ShowOnlyComponents.Reset();
		C->ShowOnlyComponents.Add(const_cast<UPrimitiveComponent*>(M));
		C->OrthoWidth = (float)Width;
		double Seen = 0.0;  // the box's area the views see (m2)
		for (int32 v = 0; v < 4; ++v)
		{
			const FVector Dir = X.GetRotation().RotateVector(GlowViews[v].GetSafeNormal());  // from the mesh toward the camera
			const FVector N = GlowViews[v].GetSafeNormal();
			Seen += (FMath::Abs(N.X) * Size.Y * Size.Z + FMath::Abs(N.Y) * Size.X * Size.Z + FMath::Abs(N.Z) * Size.X * Size.Y) / 10000.0;
			C->SetWorldLocationAndRotation(Centre + Dir * (Radius + 50.0), FRotationMatrix::MakeFromX(-Dir).Rotator());
			C->TextureTarget = Targets[v].Get();
			C->CaptureScene();
		}
		const double PixelArea = FMath::Square(Width / GlowRenderSize) / 10000.0;  // m2
		double Sum = 0.0;
		bool bRead = true;
		for (int32 v = 0; v < 4 && bRead; ++v)
		{
			FTextureRenderTargetResource* Res = Targets[v]->GameThread_GetRenderTargetResource();
			TArray<FFloat16Color> Pixels;
			bRead = Res && Res->ReadFloat16Pixels(Pixels) && Pixels.Num() >= GlowRenderSize * GlowRenderSize;
			for (const FFloat16Color& P : Pixels)
			{
				const double L = Luminance(P.R.GetFloat(), P.G.GetFloat(), P.B.GetFloat());
				if (FMath::IsFinite(L) && L > 0.0)
				{
					Sum += L * PixelArea;
					R.Peak = FMath::Max(R.Peak, L);
				}
			}
		}
		C->ShowOnlyComponents.Reset();
		C->TextureTarget = nullptr;
		C->UnregisterComponent();
		R.bRead = bRead;
		R.Mean = bRead && Seen > 1e-8 ? Sum / Seen : 0.0;
		return R;
	}

	TStrongObjectPtr<USceneCaptureComponent2D> Capture;
	TStrongObjectPtr<UTextureRenderTarget2D> Targets[4];
	TMap<FObjectKey, FGlowRendered> Cache;  // each mesh once per sample, whichever queries read it
	int32 Budget = GlowRenderBudget;
};

/** How a source's amount was read (glow_read, for logs): its material graph evaluated whole; rendered; or a bound
 *  (the graph's with an input it can't evaluate, or by parameter names) when it couldn't be rendered. */
static constexpr uint8 ReadGraph = 1, ReadRender = 2, ReadBound = 4;

/** lit and glow of one actor or component, summed over its sources (lights and meshes). */
struct FGlowReading
{
	bool bRead = false;  // it was read (else lit and glow are null)
	bool bLit = false;
	double Glow = 0.0;
	uint8 Kinds = 0;  // GlowLight | GlowEmissive | GlowUnlit: the sources that are lit
	uint8 Reads = 0;  // ReadGraph | ReadRender | ReadBound: how its meshes were read
};

/** A light component as a source: lit when it lights the scene (LightOn) and its light function, if any, isn't black;
 *  glow its intensity in candelas (point, spot and rect lights; a directional light's lux and a sky light's scale as
 *  they are) times its colour's luminance and its light function's. */
static void AddLight(FGlowReading& R, const ULightComponentBase* L, const UWorld* World)
{
	R.bRead = true;
	if (!LightOn(L, World))
	{
		return;
	}
	double I = L->Intensity;
	if (const ULocalLightComponent* Local = Cast<ULocalLightComponent>(L))
	{
		const USpotLightComponent* Spot = Cast<USpotLightComponent>(L);
		const float Cos = Spot ? FMath::Cos(FMath::DegreesToRadians(Spot->OuterConeAngle)) : -1.f;
		I *= ULocalLightComponent::GetUnitsConversionFactor(Local->IntensityUnits, ELightUnits::Candelas, Cos);
	}
	const FLinearColor C(L->LightColor);
	I *= Luminance(C.R, C.G, C.B);
	const ULightComponent* LC = Cast<ULightComponent>(L);
	double Function = 1.0;
	if (LC && LC->LightFunctionMaterial && MaterialEmissive(LC->LightFunctionMaterial, nullptr, World, Function))
	{
		I *= Function;
	}
	if (I > 0.0)
	{
		R.bLit = true;
		R.Glow += I;
		R.Kinds |= GlowLight;
	}
}

/** A mesh component as a source, lit when it is drawn (visible, not hidden in game, its owner not hidden) and its
 *  emissive luminance is above EmissiveFloor; glow that luminance times a quarter of the surface of its local bounds
 *  (m2, scaled), the candelas a lamp that size would give every way. Its emissive is read one of two ways:
 *  - every material it draws with (its own, overrides and dynamic instances with their parameters now, its overlay)
 *    has a graph the reading evaluates whole: the brightest material's luminance, as if it covered the whole mesh;
 *  - else (a custom node, a texture, a per-primitive or time input, a cooked build's material) it is rendered alone,
 *    without light (FGlowRender): lit by its brightest pixel, glow by its luminance over the box summed and averaged
 *    over four views, which is the same amount for a box lit all over and less where only part of it glows.
 *  When it can't be rendered (no renderer), the graph's bound or the parameter names, as when there was no render.
 *  False when no material could be read. */
static bool AddMesh(FGlowReading& R, const UMeshComponent* M, UWorld* World, FGlowRender* Render)
{
	TArray<UMaterialInterface*> Used;
	M->GetUsedMaterials(Used);
	bool bRead = Used.IsEmpty();
	bool bAllRead = true;  // every material it draws with said how bright it can be
	bool bExact = true;
	bool bAllUnlit = !Used.IsEmpty();
	double Best = 0.0;
	bool bUnlit = false;
	for (const UMaterialInterface* MI : Used)
	{
		double L = 0.0;
		bool bThisExact = false;
		if (!MI)
		{
			bRead = true;
			continue;
		}
		bAllUnlit &= MI->GetShadingModels().HasOnlyShadingModel(MSM_Unlit);
		if (MaterialEmissive(MI, M, World, L, bThisExact))
		{
			bRead = true;
			bExact &= bThisExact;
			if (L > Best)
			{
				Best = L;
				bUnlit = MI->GetShadingModels().HasOnlyShadingModel(MSM_Unlit);
			}
		}
		else
		{
			bExact = bAllRead = false;
		}
	}
	const AActor* Owner = M->GetOwner();
	const bool bDrawn = M->IsRegistered() && M->IsVisible() && !M->bHiddenInGame && !(Owner && Owner->IsHidden());
	const FVector Size = M->CalcBounds(FTransform::Identity).BoxExtent * 2.0 * M->GetComponentTransform().GetScale3D().GetAbs();
	const double Area = 2.0 * (Size.X * Size.Y + Size.Y * Size.Z + Size.Z * Size.X) / 10000.0;
	// a bound at or under the floor is dark whatever the inputs are: nothing to render
	if (!bExact && bDrawn && Render && !(bAllRead && Best <= EmissiveFloor))
	{
		const FGlowRendered Seen = Render->Read(M, World);
		if (Seen.bRead)
		{
			R.bRead = true;
			R.Reads |= ReadRender;
			if (Seen.Peak > EmissiveFloor)
			{
				R.bLit = true;
				R.Glow += Seen.Mean * Area / 4.0;
				R.Kinds |= bAllUnlit ? GlowUnlit : GlowEmissive;
			}
			return true;
		}
	}
	if (!bRead)
	{
		return false;
	}
	R.bRead = true;
	R.Reads |= bExact ? ReadGraph : ReadBound;
	if (!bDrawn || Best <= EmissiveFloor)
	{
		return true;
	}
	R.bLit = true;
	R.Glow += Best * Area / 4.0;
	R.Kinds |= bUnlit ? GlowUnlit : GlowEmissive;
	return true;
}

/** A particle system component (Niagara, Cascade: any FX system component) as a source: dark unless it is active and
 *  drawn (visible, not hidden in game, its owner not hidden); then rendered alone as a mesh is (FGlowRender: its
 *  sprites, ribbons, beams and meshes as they are drawn at that sample), lit by its brightest pixel and glow by the
 *  same formula over its local bounds. Without a renderer, the bound its materials' emissive graphs give, as a mesh's
 *  bound reads. False when nothing could be read. */
static bool AddEffect(FGlowReading& R, const UFXSystemComponent* FX, UWorld* World, FGlowRender* Render)
{
	const AActor* Owner = FX->GetOwner();
	const bool bDrawn = FX->IsRegistered() && FX->IsVisible() && !FX->bHiddenInGame && !(Owner && Owner->IsHidden());
	if (!bDrawn || !FX->IsActive())
	{
		R.bRead = true;
		return true;
	}
	const FVector Size = FX->CalcBounds(FTransform::Identity).BoxExtent * 2.0 * FX->GetComponentTransform().GetScale3D().GetAbs();
	const double Area = 2.0 * (Size.X * Size.Y + Size.Y * Size.Z + Size.Z * Size.X) / 10000.0;
	if (Render)
	{
		const FGlowRendered Seen = Render->Read(FX, World);
		if (Seen.bRead)
		{
			R.bRead = true;
			R.Reads |= ReadRender;
			if (Seen.Peak > EmissiveFloor)
			{
				R.bLit = true;
				R.Glow += Seen.Mean * Area / 4.0;
				R.Kinds |= GlowEffect;
			}
			return true;
		}
	}
	TArray<UMaterialInterface*> Used;
	FX->GetUsedMaterials(Used);
	double Best = 0.0;
	bool bRead = false;
	for (const UMaterialInterface* MI : Used)
	{
		double L = 0.0;
		if (MI && MaterialEmissive(MI, FX, World, L))
		{
			bRead = true;
			Best = FMath::Max(Best, L);
		}
	}
	if (!bRead)
	{
		return false;
	}
	R.bRead = true;
	R.Reads |= ReadBound;
	if (Best > EmissiveFloor)
	{
		R.bLit = true;
		R.Glow += Best * Area / 4.0;
		R.Kinds |= GlowEffect;
	}
	return true;
}

/** An actor's sources: its own registered light components, the mesh components changed compares (ChangeParts) and
 *  its particle system components. */
static FGlowReading ActorGlow(const AActor* A, UWorld* World, FGlowRender* Render)
{
	FGlowReading R;
	R.bRead = true;  // an actor with nothing that gives light reads 0
	bool bUnread = false;
	TInlineComponentArray<ULightComponentBase*> Lights(A);
	for (const ULightComponentBase* L : Lights)
	{
		if (L && L->IsRegistered() && !L->IsEditorOnly())
		{
			AddLight(R, L, World);
		}
	}
	TArray<UMeshComponent*> Meshes;
	ChangeParts(A, Meshes);
	for (const UMeshComponent* M : Meshes)
	{
		bUnread |= !AddMesh(R, M, World, Render);
	}
	TInlineComponentArray<UFXSystemComponent*> Effects(A);
	for (const UFXSystemComponent* FX : Effects)
	{
		if (FX && FX->IsRegistered() && !FX->IsEditorOnly())
		{
			bUnread |= !AddEffect(R, FX, World, Render);
		}
	}
	R.bRead = R.bLit || !bUnread;
	return R;
}

/** has: A carries a component that matches every key the select's `has` gives: `class` (the component's class or a
 *  parent, as a components select names it), `visible` (drawn, as the components `visible` field reads it), `lit` (it
 *  gives off light, as the components `lit` field reads it: a light that lights the scene, or a drawn mesh whose
 *  material is emissive or unlit and bright, from its graph or else as rendered; a particle system that is active and
 *  draws light), `near` (the component's own place within `radius` cm of the point, and its height band), `simulating`
 *  (a primitive simulating physics) and `movable` (Movable mobility). Its own registered components, editor-only ones
 *  left out. */
static bool CarriesComponent(const AActor* A, const FHasSel& Has, UWorld* World, const FVector& NearP)
{
	TInlineComponentArray<UActorComponent*> Components(A);
	for (UActorComponent* C : Components)
	{
		if (!C || !C->IsRegistered() || C->IsEditorOnly() || !ClassMatches(C->GetClass(), Has.Class))
		{
			continue;
		}
		const USceneComponent* SC = Cast<USceneComponent>(C);
		if (Has.Near.IsSet() && (!SC || !Has.Near.Holds(NearP, SC->GetComponentLocation())))
		{
			continue;
		}
		if (Has.bVisible && (!SC || !SC->IsVisible() || SC->bHiddenInGame || A->IsHidden()))
		{
			continue;
		}
		// simulating: a primitive whose physics body simulates (as the simulating field reads it), so it can be pushed
		if (Has.bSimulating && !Simulating(Cast<UPrimitiveComponent>(C)))
		{
			continue;
		}
		// movable: a scene component of Movable mobility
		if (Has.bMovable && (!SC || SC->Mobility != EComponentMobility::Movable))
		{
			continue;
		}
		if (Has.bLit)
		{
			FGlowReading Glow;
			if (const ULightComponentBase* Light = Cast<ULightComponentBase>(C))
			{
				AddLight(Glow, Light, World);
			}
			else if (const UMeshComponent* Mesh = Cast<UMeshComponent>(C))
			{
				AddMesh(Glow, Mesh, World, SelectRender);
			}
			else if (const UFXSystemComponent* FX = Cast<UFXSystemComponent>(C))
			{
				AddEffect(Glow, FX, World, SelectRender);
			}
			if (!Glow.bLit)
			{
				continue;
			}
		}
		return true;
	}
	return false;
}

static void WithSelectRender(TFunctionRef<void()> Do)
{
	FGlowRender Own;
	Own.NewSample();
	TGuardValue<FGlowRender*> Render(SelectRender, SelectRender ? SelectRender : &Own);
	Do();
}

static TSharedPtr<FJsonValue> GlowField(const FGlowReading& R, const FString& F)
{
	if (!R.bRead) return Null();
	if (F == TEXT("lit")) return Num(R.bLit ? 1.0 : 0.0);
	if (F == TEXT("glow")) return Num(R.Glow);
	return Null();
}

/** The kinds of source that are lit, for logs: "light", "emissive", "unlit", comma-separated. */
static FString GlowSources(const FGlowReading& R)
{
	TArray<FString> Kinds;
	if (R.Kinds & GlowLight) Kinds.Add(TEXT("light"));
	if (R.Kinds & GlowEmissive) Kinds.Add(TEXT("emissive"));
	if (R.Kinds & GlowUnlit) Kinds.Add(TEXT("unlit"));
	if (R.Kinds & GlowEffect) Kinds.Add(TEXT("effect"));
	return FString::Join(Kinds, TEXT(","));
}

/** How its meshes were read, for logs: "graph", "render", "bound", comma-separated; empty without a mesh. */
static FString GlowReads(const FGlowReading& R)
{
	TArray<FString> Reads;
	if (R.Reads & ReadGraph) Reads.Add(TEXT("graph"));
	if (R.Reads & ReadRender) Reads.Add(TEXT("render"));
	if (R.Reads & ReadBound) Reads.Add(TEXT("bound"));
	return FString::Join(Reads, TEXT(","));
}

/** An 8-bit sRGB value as linear light, 0-1. */
static double SrgbToLinear(uint8 V)
{
	static double Table[256];
	static bool bMade = false;
	if (!bMade)
	{
		for (int32 i = 0; i < 256; ++i)
		{
			const double C = i / 255.0;
			Table[i] = C <= 0.04045 ? C / 12.92 : FMath::Pow((C + 0.055) / 1.055, 2.4);
		}
		bMade = true;
	}
	return Table[V];
}

// ---------------------------------------------------------------- ui: what the UI shows on screen, whatever draws it

static constexpr float UiAlphaFloor = 0.004f;  // an element drawn at this alpha or less is not on screen

/** An element's rectangle in viewport fractions from Slate geometry; false when it has no size or lies off screen. */
static bool UiRect(const FGeometry& G, FUiElement& E)
{
	FVector2D VPos, VSize;
	const FVector2D Pos(G.GetAbsolutePosition());
	const FVector2D Size(G.GetAbsoluteSize());
	if (!ViewportRect(VPos, VSize) || Size.X <= 0.0 || Size.Y <= 0.0)
	{
		return false;
	}
	E.X = (Pos.X - VPos.X) / VSize.X;
	E.Y = (Pos.Y - VPos.Y) / VSize.Y;
	E.W = Size.X / VSize.X;
	E.H = Size.Y / VSize.Y;
	E.bHasRect = true;
	return E.X + E.W > 0.0 && E.X < 1.0 && E.Y + E.H > 0.0 && E.Y < 1.0;
}

/** A brush that paints something: drawn as an image, box or border, not fully transparent. */
static bool BrushDraws(const FSlateBrush* Brush)
{
	return Brush && Brush->DrawAs != ESlateBrushDrawType::NoDrawType &&
		(!Brush->TintColor.IsColorSpecified() || Brush->TintColor.GetSpecifiedColor().A > UiAlphaFloor);
}

/** Rich text as shown: its markup (<Style>...</>, <img .../>) left out, &lt; &gt; &amp; &quot; as the characters. */
static FString PlainRichText(const FString& Marked)
{
	static const FRegexPattern Tag(TEXT("</>|<[A-Za-z_][^<>]*>"));
	FString Out;
	FRegexMatcher Matcher(Tag, Marked);
	int32 From = 0;
	while (Matcher.FindNext())
	{
		Out += Marked.Mid(From, Matcher.GetMatchBeginning() - From);
		From = Matcher.GetMatchEnding();
	}
	Out += Marked.Mid(From);
	return Out.Replace(TEXT("&lt;"), TEXT("<")).Replace(TEXT("&gt;"), TEXT(">")).Replace(TEXT("&quot;"), TEXT("\"")).Replace(TEXT("&amp;"), TEXT("&"));
}

/** The element a visible Slate widget draws, if it draws one the ui reading counts (text, a box, an image). */
static void UiSlateElement(const TSharedRef<SWidget>& W, TArray<FUiElement>& Out)
{
	const FName Type = W->GetType();
	FUiElement E;
	if (Type == TEXT("STextBlock"))
	{
		E.Kind = TEXT("text");
		E.Text = StaticCastSharedRef<STextBlock>(W)->GetText().ToString();
	}
	else if (Type == TEXT("SRichTextBlock"))
	{
		E.Kind = TEXT("text");
		E.Text = PlainRichText(StaticCastSharedRef<SRichTextBlock>(W)->GetText().ToString());
	}
	else if (Type == TEXT("SEditableText") || Type == TEXT("SMultiLineEditableText"))
	{
		// an empty field shows its hint
		E.Kind = TEXT("text");
		const bool bSingle = Type == TEXT("SEditableText");
		E.Text = bSingle ? StaticCastSharedRef<SEditableText>(W)->GetText().ToString() : StaticCastSharedRef<SMultiLineEditableText>(W)->GetText().ToString();
		if (E.Text.IsEmpty())
		{
			E.Text = bSingle ? StaticCastSharedRef<SEditableText>(W)->GetHintText().ToString() : StaticCastSharedRef<SMultiLineEditableText>(W)->GetHintText().ToString();
		}
	}
	else if (Type == TEXT("SImage"))
	{
		const FSlateBrush* Brush = FTaskProbeImagePeek::Brush(StaticCastSharedRef<SImage>(W).Get());
		if (!BrushDraws(Brush))
		{
			return;
		}
		E.Kind = Brush->GetResourceObject() ? TEXT("image") : TEXT("box");
	}
	else if (Type == TEXT("SBorder") || Type == TEXT("SButton"))
	{
		const TSharedRef<SBorder> B = StaticCastSharedRef<SBorder>(W);
		const FSlateBrush* Brush = B->GetBorderImage();
		const FSlateColor Back = B->GetBorderBackgroundColor();
		if (!BrushDraws(Brush) || (Back.IsColorSpecified() && Back.GetSpecifiedColor().A <= UiAlphaFloor))
		{
			return;
		}
		E.Kind = Brush->GetResourceObject() ? TEXT("image") : TEXT("box");
	}
	else if (Type == TEXT("SProgressBar") || Type == TEXT("SColorBlock"))
	{
		E.Kind = TEXT("box");
	}
	else
	{
		return;
	}
	if (E.Kind == TEXT("text") && E.Text.TrimStartAndEnd().IsEmpty())
	{
		return;
	}
	if (!UiRect(W->GetTickSpaceGeometry(), E))
	{
		return;
	}
	const TSharedPtr<FReflectionMetaData> Meta = W->GetMetaData<FReflectionMetaData>();
	const UClass* MetaClass = Meta.IsValid() ? Meta->Class.Get() : nullptr;
	if (Meta.IsValid())
	{
		E.Source = TEXT("umg");
		E.Name = Meta->Name.ToString();
		E.Class = MetaClass ? MetaClass->GetName() : W->GetTypeAsString();
	}
	else
	{
		E.Source = TEXT("slate");
		E.Name = W->GetTag().IsNone() ? W->GetTypeAsString() : W->GetTag().ToString();
		E.Class = W->GetTypeAsString();
	}
	Out.Add(MoveTemp(E));
}

/** The Slate tree under the game viewport, visible widgets only: a collapsed or hidden widget, or one at render opacity
 *  0, and everything under it is not on screen (a widget switcher gives only its active child). */
static void UiSlate(const TSharedRef<SWidget>& W, TArray<FUiElement>& Out, int32 Depth = 0)
{
	if (Depth > 256 || !W->GetVisibility().IsVisible() || W->GetRenderOpacity() <= 0.001f)
	{
		return;
	}
	UiSlateElement(W, Out);
	if (FChildren* Children = W->GetChildren())
	{
		for (int32 i = 0; i < Children->Num(); ++i)
		{
			UiSlate(Children->GetChildAt(i), Out, Depth + 1);
		}
	}
}

// The canvas's batched triangles and the font cache's glyphs are private engine data with no accessor. They are read
// through member pointers named in an explicit instantiation, where access is not checked ([temp.spec] of the C++
// standard), by a friend function each tag declares and the instantiation defines. Read only, on the game thread.

/** A triangle the canvas batched: its texture and its vertices' indices into the batch's vertices. */
struct FUiTri
{
	const FTexture* Texture = nullptr;
	int32 V[3] = {0, 0, 0};
};

struct FUiBatchTag
{
	friend void ReadBatch(FUiBatchTag, const FBatchedElements& B, TArray<FUiTri>& OutTris, const TArray<FSimpleElementVertex>*& OutVerts);
};
template<typename Tag, auto Elements, auto Vertices>
struct TUiBatchReader
{
	friend void ReadBatch(Tag, const FBatchedElements& B, TArray<FUiTri>& OutTris, const TArray<FSimpleElementVertex>*& OutVerts)
	{
		OutVerts = &(B.*Vertices);
		for (const auto& Mesh : B.*Elements)
		{
			for (int32 i = 0; i + 2 < Mesh.Indices.Num(); i += 3)
			{
				FUiTri T;
				T.Texture = Mesh.Texture;
				for (int32 k = 0; k < 3; ++k)
				{
					T.V[k] = (int32)Mesh.MinVertex + (int32)Mesh.Indices[i + k];
				}
				OutTris.Add(T);
			}
		}
	}
};
template struct TUiBatchReader<FUiBatchTag, &FBatchedElements::MeshElements, &FBatchedElements::MeshVertices>;

struct FUiFontListsTag
{
	friend void ReadFontLists(FUiFontListsTag, const FSlateFontCache& Cache, TArray<const FCharacterList*>& Out);
};
template<typename Tag, auto Lists>
struct TUiFontListsReader
{
	friend void ReadFontLists(Tag, const FSlateFontCache& Cache, TArray<const FCharacterList*>& Out)
	{
		for (const auto& Pair : Cache.*Lists)
		{
			if (Pair.Value)
			{
				Out.Add(Pair.Value.Get());
			}
		}
	}
};
template struct TUiFontListsReader<FUiFontListsTag, &FSlateFontCache::FontToCharacterListCache>;

struct FUiCharsTag
{
	friend void ReadCharacters(FUiCharsTag, const FCharacterList& List, TArray<const FCharacterEntry*>& Out);
};
template<typename Tag, auto Entries>
struct TUiCharsReader
{
	friend void ReadCharacters(Tag, const FCharacterList& List, TArray<const FCharacterEntry*>& Out)
	{
		for (const auto& Pair : List.*Entries)
		{
			Out.Add(&Pair.Value);
		}
	}
};
template struct TUiCharsReader<FUiCharsTag, &FCharacterList::MappedEntries>;

/** A line the canvas batched (DrawLine, K2_DrawLine, each side of K2_DrawBox): its ends and thickness (0: one pixel),
 *  in canvas units. */
struct FUiStroke
{
	FVector2D A = FVector2D::ZeroVector;
	FVector2D B = FVector2D::ZeroVector;
	double Thickness = 0.0;
};

struct FUiLinesTag
{
	friend void ReadLines(FUiLinesTag, const FBatchedElements& B, TArray<FUiStroke>& Out);
};
template<typename Tag, auto Thin, auto Thick>
struct TUiLinesReader
{
	friend void ReadLines(Tag, const FBatchedElements& B, TArray<FUiStroke>& Out)
	{
		// one-pixel lines: their ends in pairs; thick lines: one entry each
		const TArray<FSimpleElementVertex>& Ends = B.*Thin;
		for (int32 i = 0; i + 1 < Ends.Num(); i += 2)
		{
			const FVector4d P = Ends[i].Position.GetVector4d(), Q = Ends[i + 1].Position.GetVector4d();
			FUiStroke S;
			S.A = FVector2D(P.X, P.Y);
			S.B = FVector2D(Q.X, Q.Y);
			Out.Add(S);
		}
		for (const auto& L : B.*Thick)
		{
			FUiStroke S;
			S.A = FVector2D(L.Start.X, L.Start.Y);
			S.B = FVector2D(L.End.X, L.End.Y);
			S.Thickness = L.Thickness;
			Out.Add(S);
		}
	}
};
template struct TUiLinesReader<FUiLinesTag, &FBatchedElements::LineVertices, &FBatchedElements::ThickLines>;

/** A glyph placed in a font texture: the character and how a string lays it out (in the font's own pixels; a canvas
 *  draw scales them by the quad's size over USize). */
/** AHUD's canvas is protected: read through a member pointer taken in a derived scope (never constructed). */
struct FTaskProbeHudPeek : public AHUD
{
	static UCanvas* CanvasOf(const AHUD& Hud) { return (Hud.*(&FTaskProbeHudPeek::Canvas)).Get(); }
};

static bool SharesVertex(const FUiTri& A, const FUiTri& B)
{
	for (int32 a : A.V)
	{
		for (int32 b : B.V)
		{
			if (a == b)
			{
				return true;
			}
		}
	}
	return false;
}

struct FUiGlyph
{
	TCHAR Char = 0;
	const void* Font = nullptr;  // the character list or offline font it belongs to: one string is one font
	float HorizontalOffset = 0.f;
	float Advance = 0.f;
	float Space = 0.f;  // the font's space advance (0: unknown)
	float USize = 1.f;
	float RenderScale = 1.f;
};

using FUiGlyphKey = TPair<const FTexture*, uint32>;  // a font texture and a glyph's top-left texel (u << 16 | v)

/** Every glyph the fonts in memory have placed in their textures: the game thread's runtime font cache (every character
 *  list it holds) and the offline fonts (UFont characters on their own texture pages). OutFontTextures: every texture
 *  a glyph is on. */
static void UiGlyphs(TMap<FUiGlyphKey, FUiGlyph>& Out, TSet<const FTexture*>& OutFontTextures)
{
	const TSharedPtr<FSlateFontCache> Cache = FEngineFontServices::IsInitialized() ? FEngineFontServices::Get().GetFontCache() : nullptr;
	if (Cache.IsValid())
	{
		const int32 Pages = Cache->GetNumAtlasPages();
		TArray<const FCharacterList*> Lists;
		ReadFontLists(FUiFontListsTag(), *Cache, Lists);
		for (const FCharacterList* List : Lists)
		{
			TArray<const FCharacterEntry*> Entries;
			ReadCharacters(FUiCharsTag(), *List, Entries);
			float Space = 0.f;
			for (const FCharacterEntry* E : Entries)
			{
				if (E->Character == TEXT(' ') && E->Valid)
				{
					Space = E->XAdvance;
				}
			}
			for (const FCharacterEntry* E : Entries)
			{
				if (!E->Valid || E->USize == 0 || E->VSize == 0 || (int32)E->TextureIndex >= Pages)
				{
					continue;
				}
				ISlateFontTexture* SlateTexture = Cache->GetFontTexture(E->TextureIndex);
				const FTexture* Texture = SlateTexture ? SlateTexture->GetEngineTexture() : nullptr;
				if (!Texture)
				{
					continue;
				}
				FUiGlyph G;
				G.Char = E->Character;
				G.Font = List;
				G.HorizontalOffset = E->HorizontalOffset;
				G.Advance = E->XAdvance;
				G.Space = Space;
				G.USize = E->USize;
				G.RenderScale = E->BitmapRenderScale > 0.f ? E->BitmapRenderScale : 1.f;
				Out.Add(FUiGlyphKey(Texture, ((uint32)E->StartU << 16) | E->StartV), G);
				OutFontTextures.Add(Texture);
			}
		}
	}
	for (TObjectIterator<UFont> It; It; ++It)
	{
		const UFont* Font = *It;
		if (!IsValid(Font) || Font->FontCacheType != EFontCacheType::Offline || Font->Characters.Num() == 0)
		{
			continue;
		}
		TMap<int32, TCHAR> CharOf;  // a Characters index -> the character it draws
		if (Font->IsRemapped)
		{
			for (const TPair<uint16, uint16>& Pair : Font->CharRemap)
			{
				CharOf.Add(Pair.Value, (TCHAR)Pair.Key);
			}
		}
		const int32 SpaceIndex = Font->IsRemapped ? (Font->CharRemap.Contains(TEXT(' ')) ? Font->CharRemap[TEXT(' ')] : -1) : TEXT(' ');
		const float Space = Font->Characters.IsValidIndex(SpaceIndex) ? (float)Font->Characters[SpaceIndex].USize : 0.f;
		for (int32 i = 0; i < Font->Characters.Num(); ++i)
		{
			const FFontCharacter& C = Font->Characters[i];
			const UTexture2D* Page = Font->Textures.IsValidIndex(C.TextureIndex) ? Font->Textures[C.TextureIndex].Get() : nullptr;
			const FTexture* Texture = Page ? Page->GetResource() : nullptr;
			if (!Texture || C.USize <= 0 || C.VSize <= 0)
			{
				continue;
			}
			FUiGlyph G;
			G.Char = Font->IsRemapped ? CharOf.FindRef(i) : (TCHAR)i;
			G.Font = Font;
			G.Advance = (float)(C.USize + Font->Kerning);
			G.Space = Space;
			G.USize = (float)C.USize;
			Out.Add(FUiGlyphKey(Texture, ((uint32)C.StartU << 16) | (uint32)C.StartV), G);
			OutFontTextures.Add(Texture);
		}
	}
}

/** A quad of glyph texels drawn on the canvas, in canvas pixels. */
struct FUiGlyphQuad
{
	FUiGlyphKey Key;
	const FUiGlyph* Glyph = nullptr;  // null: a texel no font in memory has a glyph at
	FBox2D Box = FBox2D(ForceInit);
};

/** Strings back from the glyph quads a frame's canvas holds, in the order drawn: a text effect (a shadow, an outline)
 *  is the same glyph drawn just before it a few pixels off, so it gives way to the glyph after it (a letter repeated
 *  in a word sits on the same line a whole advance on); a glyph joins the string
 *  before it when it is of the same font, on the same line (their heights overlap by a third) and where that string's
 *  pen left off, the gap read as spaces of the font's space advance; anything else starts a new string. */
static void UiStrings(const TArray<FUiGlyphQuad>& Quads, TArray<FUiElement>& Out, const FVector2D& Pixels)
{
	TArray<FUiGlyphQuad> Glyphs;
	for (const FUiGlyphQuad& Q : Quads)
	{
		if (Glyphs.Num() > 0 && Glyphs.Last().Key == Q.Key)
		{
			const FVector2D D = Q.Box.Min - Glyphs.Last().Box.Min;
			if (FMath::Abs(D.Y) > 0.25 || FMath::Abs(D.X) <= 2.5)
			{
				Glyphs.Last() = Q;  // the glyph drawn over its effect
				continue;
			}
		}
		Glyphs.Add(Q);
	}
	FString Text;
	FBox2D Box(ForceInit);
	const FUiGlyph* Font = nullptr;
	double PenEnd = 0.0;  // where the string's pen stands after its last glyph
	double Scale = 1.0;  // the string's scale: canvas pixels per font pixel
	auto Flush = [&]()
	{
		if (!Text.TrimStartAndEnd().IsEmpty() && Box.bIsValid && Pixels.X > 0.0 && Pixels.Y > 0.0)
		{
			FUiElement E;
			E.Source = TEXT("canvas");
			E.Kind = TEXT("text");
			E.Name = TEXT("CanvasText");
			E.Class = TEXT("CanvasText");
			E.Text = Text.TrimStartAndEnd();
			E.bHasRect = true;
			E.X = Box.Min.X / Pixels.X;
			E.Y = Box.Min.Y / Pixels.Y;
			E.W = (Box.Max.X - Box.Min.X) / Pixels.X;
			E.H = (Box.Max.Y - Box.Min.Y) / Pixels.Y;
			Out.Add(MoveTemp(E));
		}
		Text.Reset();
		Box = FBox2D(ForceInit);
		Font = nullptr;
	};
	for (const FUiGlyphQuad& Q : Glyphs)
	{
		const FUiGlyph* G = Q.Glyph;
		const double Width = Q.Box.Max.X - Q.Box.Min.X;
		const double Height = Q.Box.Max.Y - Q.Box.Min.Y;
		const double S = G ? Width / FMath::Max(1.0, (double)G->USize * G->RenderScale) : 1.0;
		const double Pen = G ? Q.Box.Min.X - G->HorizontalOffset * S : Q.Box.Min.X;
		bool bJoins = Font != nullptr && G != nullptr && G->Font == Font->Font;
		if (bJoins)
		{
			const double Overlap = FMath::Min(Box.Max.Y, Q.Box.Max.Y) - FMath::Max(Box.Min.Y, Q.Box.Min.Y);
			const double Em = FMath::Max(Box.Max.Y - Box.Min.Y, Height);
			const double SpaceWidth = G->Space > 0.f ? G->Space * Scale : 0.3 * Em;
			const double Gap = Pen - PenEnd;
			bJoins = Overlap >= FMath::Min(Box.Max.Y - Box.Min.Y, Height) / 3.0 && Gap > -0.5 * Em && Gap < 4.0 * FMath::Max(SpaceWidth, 0.25 * Em);
			if (bJoins)
			{
				const int32 Spaces = SpaceWidth > 0.0 ? FMath::RoundToInt(Gap / SpaceWidth) : 0;
				for (int32 i = 0; i < Spaces; ++i)
				{
					Text.AppendChar(TEXT(' '));
				}
			}
		}
		if (!bJoins)
		{
			Flush();
			Font = G;
			Scale = S;
		}
		Text.AppendChar(G ? G->Char : TEXT('?'));
		Box += Q.Box;
		PenEnd = G ? Pen + G->Advance * S : Q.Box.Max.X;
	}
	Flush();
}

/** A canvas element's rectangle in viewport fractions from a box in canvas pixels. */
static void CanvasRect(const FBox2D& Box, const FVector2D& Pixels, FUiElement& E)
{
	E.bHasRect = true;
	E.X = Box.Min.X / Pixels.X;
	E.Y = Box.Min.Y / Pixels.Y;
	E.W = (Box.Max.X - Box.Min.X) / Pixels.X;
	E.H = (Box.Max.Y - Box.Min.Y) / Pixels.Y;
}

/** A stroke's box as drawn: its ends, widened by half its thickness (a one-pixel line by half a pixel). */
static FBox2D StrokeBox(const FUiStroke& S)
{
	const double Half = FMath::Max(S.Thickness, 1.0) / 2.0;
	FBox2D Box(ForceInit);
	Box += S.A;
	Box += S.B;
	return Box.ExpandBy(Half);
}

/** Four strokes, one after another, that close an axis-aligned rectangle (K2_DrawBox draws its four sides so; so do four
 *  DrawLine calls around a box): each lies on a different side of their box and runs its length. */
static bool ClosesBox(const FUiStroke* S, FBox2D& OutBox)
{
	FBox2D Box(ForceInit);
	for (int32 i = 0; i < 4; ++i)
	{
		Box += S[i].A;
		Box += S[i].B;
	}
	const double W = Box.Max.X - Box.Min.X, H = Box.Max.Y - Box.Min.Y;
	if (W < 1.0 || H < 1.0)
	{
		return false;
	}
	const double Tol = FMath::Max(1.0, 0.02 * FMath::Max(W, H));
	uint8 Sides = 0;  // top, bottom, left, right
	for (int32 i = 0; i < 4; ++i)
	{
		const FUiStroke& L = S[i];
		const double X0 = FMath::Min(L.A.X, L.B.X), X1 = FMath::Max(L.A.X, L.B.X), Y0 = FMath::Min(L.A.Y, L.B.Y), Y1 = FMath::Max(L.A.Y, L.B.Y);
		const bool bAcross = X1 - X0 >= W - 2.0 * Tol && Y1 - Y0 <= Tol;
		const bool bDown = Y1 - Y0 >= H - 2.0 * Tol && X1 - X0 <= Tol;
		uint8 Side = 0;
		if (bAcross && FMath::Abs(Y0 - Box.Min.Y) <= Tol) Side = 1;
		else if (bAcross && FMath::Abs(Y1 - Box.Max.Y) <= Tol) Side = 2;
		else if (bDown && FMath::Abs(X0 - Box.Min.X) <= Tol) Side = 4;
		else if (bDown && FMath::Abs(X1 - Box.Max.X) <= Tol) Side = 8;
		if (!Side || (Sides & Side))
		{
			return false;
		}
		Sides |= Side;
	}
	OutBox = Box.ExpandBy(FMath::Max(S[0].Thickness, 1.0) / 2.0);
	return Sides == 15;
}

/** The line elements of a frame's strokes, in the order drawn: one per stroke, an outline (four strokes closing a
 *  rectangle one after another) once, as its rectangle. Off-canvas and zero-length strokes are left out. */
static void UiLines(const TArray<FUiStroke>& Strokes, const FVector2D& Pixels, TArray<FUiElement>& Out)
{
	for (int32 i = 0; i < Strokes.Num();)
	{
		FBox2D Box(ForceInit);
		const bool bOutline = i + 3 < Strokes.Num() && ClosesBox(&Strokes[i], Box);
		if (!bOutline)
		{
			Box = StrokeBox(Strokes[i]);
		}
		const int32 Used = bOutline ? 4 : 1;
		const bool bOnCanvas = Box.Max.X > 0.0 && Box.Min.X < Pixels.X && Box.Max.Y > 0.0 && Box.Min.Y < Pixels.Y;
		if (bOnCanvas && (bOutline || FVector2D::Distance(Strokes[i].A, Strokes[i].B) >= 0.5))
		{
			FUiElement E;
			E.Source = TEXT("canvas");
			E.Kind = TEXT("line");
			E.Name = bOutline ? TEXT("CanvasOutline") : TEXT("CanvasLine");
			E.Class = E.Name;
			CanvasRect(Box, Pixels, E);
			Out.Add(MoveTemp(E));
		}
		i += Used;
	}
}

// Digits drawn with strokes (UiStrokeText). A seven-segment digit is three horizontal strokes at most (top, middle,
// bottom) of one width, one above the other, and upright strokes at their left and right ends; a 1 is upright strokes
// alone in one column. The reading groups a frame's strokes into such cells, reads each, and refuses whatever is
// ambiguous (a stroke it could not place, a cell inside a box, a stroke left over at a digit's edge): what it can't
// tell apart reads no text rather than a wrong one.

static double StrokeLength(const FUiStroke& S) { return FVector2D::Distance(S.A, S.B); }
static double StrokeWidth(const FUiStroke& S) { return FMath::Max(S.Thickness, 1.0); }
static double MidX(const FUiStroke& S) { return (S.A.X + S.B.X) / 2.0; }
static double MidY(const FUiStroke& S) { return (S.A.Y + S.B.Y) / 2.0; }
static double MinX(const FUiStroke& S) { return FMath::Min(S.A.X, S.B.X); }
static double MaxX(const FUiStroke& S) { return FMath::Max(S.A.X, S.B.X); }
static double MinY(const FUiStroke& S) { return FMath::Min(S.A.Y, S.B.Y); }
static double MaxY(const FUiStroke& S) { return FMath::Max(S.A.Y, S.B.Y); }
static bool Level(const FUiStroke& S) { return FMath::Abs(S.B.Y - S.A.Y) <= 0.2 * FMath::Abs(S.B.X - S.A.X); }
static bool Upright(const FUiStroke& S) { return !Level(S) && FMath::Abs(S.B.X - S.A.X) <= 0.2 * FMath::Abs(S.B.Y - S.A.Y); }

static double PointToStroke(const FVector2D& P, const FUiStroke& S)
{
	return FMath::Sqrt(FMath::PointDistToSegmentSquared(FVector(P, 0.0), FVector(S.A, 0.0), FVector(S.B, 0.0)));
}

/** A seven-segment digit by its lit segments (a top, b top right, c bottom right, d bottom, e bottom left, f top left,
 *  g middle: bits 0-6), with the usual variants (a 6 without its top, a 7 with its top left, a 9 without its bottom);
 *  0 for none. */
static TCHAR SevenSegment(uint8 Mask)
{
	switch (Mask)
	{
	case 0x3F: return TEXT('0');
	case 0x06: return TEXT('1');
	case 0x5B: return TEXT('2');
	case 0x4F: return TEXT('3');
	case 0x66: return TEXT('4');
	case 0x6D: return TEXT('5');
	case 0x7D: case 0x7C: return TEXT('6');
	case 0x07: case 0x27: return TEXT('7');
	case 0x7F: return TEXT('8');
	case 0x6F: case 0x67: return TEXT('9');
	default: return 0;
	}
}

/** The box around strokes' centre lines. */
static constexpr int32 NoDigit = INDEX_NONE;  // in a cell: its strokes are no digit (a box's side)

static FBox2D CentreBox(const TArray<int32>& Cell, const TArray<FUiStroke>& Strokes)
{
	FBox2D Box(ForceInit);
	for (const int32 i : Cell)
	{
		if (i == NoDigit)
		{
			continue;
		}
		Box += Strokes[i].A;
		Box += Strokes[i].B;
	}
	return Box;
}

/** One cell's strokes read as a seven-segment digit: horizontal strokes across its width at its top, middle or bottom,
 *  upright strokes at its left or right over its upper half, lower half or both; a cell of upright strokes alone in one
 *  column (no wider than a fifth of its height, without a gap of more than 0.3 of it) is a 1. 0 when the strokes are
 *  anything else: a slanted stroke, a stroke inside the cell, a shape no digit has, a cell not 1.2-4 times as tall as
 *  wide, more than three heights of horizontal strokes. */
static TCHAR StrokeDigit(const TArray<int32>& Cell, const TArray<FUiStroke>& Strokes)
{
	const FBox2D Box = CentreBox(Cell, Strokes);
	const double W = Box.Max.X - Box.Min.X, H = Box.Max.Y - Box.Min.Y;
	if (Cell.IsEmpty() || Cell.Contains(NoDigit) || H < 4.0)
	{
		return 0;
	}
	if (W <= 0.2 * H)
	{
		TArray<FVector2D> Spans;
		for (const int32 i : Cell)
		{
			if (!Upright(Strokes[i]))
			{
				return 0;
			}
			Spans.Add(FVector2D(MinY(Strokes[i]), MaxY(Strokes[i])));
		}
		Spans.Sort([](const FVector2D& L, const FVector2D& R) { return L.X < R.X; });
		double Reach = Spans[0].Y, Gaps = 0.0;
		for (const FVector2D& Span : Spans)
		{
			Gaps += FMath::Max(0.0, Span.X - Reach);
			Reach = FMath::Max(Reach, Span.Y);
		}
		return Gaps <= 0.3 * H ? TEXT('1') : 0;
	}
	if (H < 1.2 * W || H > 4.0 * W)
	{
		return 0;
	}
	uint8 Mask = 0;
	const double Mid = Box.Min.Y + H / 2.0;
	TArray<double> Heights;
	for (const int32 i : Cell)
	{
		const FUiStroke& S = Strokes[i];
		if (Level(S))
		{
			if (MaxX(S) - MinX(S) < 0.6 * W)
			{
				return 0;
			}
			const double R = (MidY(S) - Box.Min.Y) / H;
			Mask |= (uint8)(R <= 0.2 ? 0x01 : (R >= 0.35 && R <= 0.65) ? 0x40 : R >= 0.8 ? 0x08 : 0x80);
			Heights.Add(MidY(S));
		}
		else if (Upright(S))
		{
			const double Q = (MidX(S) - Box.Min.X) / W;
			const bool bLeft = Q <= 0.2, bRight = Q >= 0.8;
			const bool bUpper = FMath::Min(MaxY(S), Mid) - FMath::Max(MinY(S), Box.Min.Y) >= 0.25 * H;
			const bool bLower = FMath::Min(MaxY(S), Box.Max.Y) - FMath::Max(MinY(S), Mid) >= 0.25 * H;
			if ((!bLeft && !bRight) || (!bUpper && !bLower))
			{
				return 0;
			}
			Mask |= (uint8)((bRight && bUpper ? 0x02 : 0) | (bRight && bLower ? 0x04 : 0) | (bLeft && bLower ? 0x10 : 0) | (bLeft && bUpper ? 0x20 : 0));
		}
		else
		{
			return 0;
		}
	}
	// at most three heights of horizontal strokes (a box drawn around a digit adds more)
	Heights.Sort();
	int32 Levels = 0;
	for (int32 k = 0; k < Heights.Num(); ++k)
	{
		Levels += k == 0 || Heights[k] - Heights[k - 1] > FMath::Max(1.5, 0.1 * (Heights.Last() - Heights[0])) ? 1 : 0;
	}
	return (Mask & 0x80) || Levels > 3 ? 0 : SevenSegment(Mask);
}

/** A frame's strokes grouped into digit cells (indices into Strokes): each run of horizontal strokes of one width one
 *  above the other (both ends within 15% of their length, at most 4.5 lengths apart) is a cell, and each upright stroke
 *  of a digit's proportions joins the cell at whose left or right end it stands (within 0.3 of the cell's width), at the
 *  cell's height, nearest first; upright strokes farther out than a cell's own on one side go free; free upright
 *  strokes in one column, one under the other, are a cell each (a 1), unless they meet a horizontal stroke (a box's
 *  side). A slanted stroke joins every cell it is near, which then reads nothing. */
static void StrokeCells(const TArray<FUiStroke>& Strokes, TArray<TArray<int32>>& OutCells)
{
	TArray<int32> Hs, Vs, Others;
	for (int32 i = 0; i < Strokes.Num(); ++i)
	{
		const FUiStroke& S = Strokes[i];
		if (Level(S))
		{
			if (StrokeLength(S) >= 2.0)
			{
				Hs.Add(i);
			}
		}
		else if (Upright(S))
		{
			if (StrokeLength(S) >= 2.0)
			{
				Vs.Add(i);
			}
		}
		else
		{
			Others.Add(i);
		}
	}
	// cells of horizontal strokes
	TArray<int32> Parent;
	for (int32 k = 0; k < Hs.Num(); ++k)
	{
		Parent.Add(k);
	}
	auto Find = [&Parent](int32 k)
	{
		while (Parent[k] != k)
		{
			Parent[k] = Parent[Parent[k]];
			k = Parent[k];
		}
		return k;
	};
	for (int32 p = 0; p < Hs.Num(); ++p)
	{
		for (int32 q = p + 1; q < Hs.Num(); ++q)
		{
			const FUiStroke& A = Strokes[Hs[p]];
			const FUiStroke& B = Strokes[Hs[q]];
			const double La = StrokeLength(A), Lb = StrokeLength(B);
			const double Tol = FMath::Max(1.5, 0.15 * FMath::Min(La, Lb)) + (StrokeWidth(A) + StrokeWidth(B)) / 4.0;
			if (FMath::Abs(MinX(A) - MinX(B)) <= Tol && FMath::Abs(MaxX(A) - MaxX(B)) <= Tol && FMath::Abs(MinY(A) - MinY(B)) <= 4.5 * FMath::Min(La, Lb))
			{
				Parent[Find(p)] = Find(q);
			}
		}
	}
	struct FCell
	{
		TArray<int32> Strokes;
		double X0, X1, Y0, Y1;
	};
	TArray<FCell> Cells;
	TMap<int32, int32> CellOf;
	for (int32 k = 0; k < Hs.Num(); ++k)
	{
		const FUiStroke& S = Strokes[Hs[k]];
		const int32 Root = Find(k);
		if (const int32* Found = CellOf.Find(Root))
		{
			FCell& C = Cells[*Found];
			C.Strokes.Add(Hs[k]);
			C.X0 = FMath::Min(C.X0, MinX(S));
			C.X1 = FMath::Max(C.X1, MaxX(S));
			C.Y0 = FMath::Min(C.Y0, MinY(S));
			C.Y1 = FMath::Max(C.Y1, MaxY(S));
		}
		else
		{
			CellOf.Add(Root, Cells.Num());
			Cells.Add({{Hs[k]}, MinX(S), MaxX(S), MinY(S), MaxY(S)});
		}
	}
	// upright strokes join cells, best first
	TArray<int32> Left = Vs;
	while (Left.Num() > 0)
	{
		int32 BestV = INDEX_NONE, BestC = INDEX_NONE;
		int32 BestBand = 2;
		double BestD = 0.0;
		for (int32 vi = 0; vi < Left.Num(); ++vi)
		{
			const FUiStroke& V = Strokes[Left[vi]];
			const double X = MidX(V), Vy0 = MinY(V), Vy1 = MaxY(V), Lv = Vy1 - Vy0;
			for (int32 ci = 0; ci < Cells.Num(); ++ci)
			{
				const FCell& C = Cells[ci];
				const double W = C.X1 - C.X0;
				const double D = FMath::Min(FMath::Abs(X - C.X0), FMath::Abs(X - C.X1));
				if (D > 0.3 * W + StrokeWidth(V) / 2.0 || W > 3.0 * Lv || Lv > 4.5 * W || Vy1 < C.Y0 - Lv || Vy0 > C.Y1 + Lv)
				{
					continue;
				}
				const double Overlap = FMath::Max(0.0, FMath::Min(Vy1, C.Y1 + Lv) - FMath::Max(Vy0, C.Y0 - Lv));
				const int32 Band = Overlap >= 0.5 * Lv ? 0 : 1;
				if (Band < BestBand || (Band == BestBand && D < BestD))
				{
					BestBand = Band;
					BestD = D;
					BestV = vi;
					BestC = ci;
				}
			}
		}
		if (BestV == INDEX_NONE)
		{
			break;
		}
		const FUiStroke& V = Strokes[Left[BestV]];
		FCell& C = Cells[BestC];
		C.Strokes.Add(Left[BestV]);
		C.Y0 = FMath::Min(C.Y0, MinY(V));
		C.Y1 = FMath::Max(C.Y1, MaxY(V));
		Left.RemoveAt(BestV);
	}
	TArray<int32> Free = Left;
	for (FCell& C : Cells)
	{
		const double W = C.X1 - C.X0, Centre = (C.X0 + C.X1) / 2.0;
		auto Release = [&](TFunctionRef<bool(const FUiStroke&)> Out)
		{
			for (int32 k = C.Strokes.Num() - 1; k >= 0; --k)
			{
				const FUiStroke& S = Strokes[C.Strokes[k]];
				if (Upright(S) && Out(S))
				{
					Free.Add(C.Strokes[k]);
					C.Strokes.RemoveAt(k);
				}
			}
		};
		// a side with upright strokes in two columns: the ones nearest the edge are the digit's, the others go free
		for (const bool bRightSide : {false, true})
		{
			const double Edge = bRightSide ? C.X1 : C.X0;
			double Near = TNumericLimits<double>::Max();
			int32 Count = 0;
			for (const int32 i : C.Strokes)
			{
				const FUiStroke& S = Strokes[i];
				if (Upright(S) && (MidX(S) > Centre) == bRightSide)
				{
					Near = FMath::Min(Near, FMath::Abs(MidX(S) - Edge));
					++Count;
				}
			}
			if (Count >= 2)
			{
				Release([&](const FUiStroke& S)
				{
					return (MidX(S) > Centre) == bRightSide && FMath::Abs(MidX(S) - Edge) > Near + FMath::Max(1.0, 0.05 * W) + StrokeWidth(S) / 2.0;
				});
			}
		}
		// a digit's own upright strokes stand as far out on its left as on its right: farther ones on the left are a 1's
		double Own = TNumericLimits<double>::Max();
		bool bLefts = false;
		for (const int32 i : C.Strokes)
		{
			const FUiStroke& S = Strokes[i];
			if (Upright(S) && MidX(S) > Centre)
			{
				Own = FMath::Min(Own, FMath::Max(0.0, MidX(S) - C.X1));
			}
			bLefts |= Upright(S) && MidX(S) < Centre;
		}
		if (bLefts && Own < TNumericLimits<double>::Max())
		{
			Release([&](const FUiStroke& S)
			{
				return MidX(S) < Centre && C.X0 - MidX(S) > Own + FMath::Max(1.0, 0.05 * W) + StrokeWidth(S) / 2.0;
			});
		}
	}
	for (const int32 o : Others)
	{
		const FUiStroke& S = Strokes[o];
		for (FCell& C : Cells)
		{
			const double M = 0.3 * (C.X1 - C.X0) + StrokeWidth(S);
			if (MaxX(S) >= C.X0 - M && MinX(S) <= C.X1 + M && MaxY(S) >= C.Y0 - M && MinY(S) <= C.Y1 + M)
			{
				C.Strokes.Add(o);
			}
		}
	}
	for (const FCell& C : Cells)
	{
		OutCells.Add(C.Strokes);
	}
	// 1s: free upright strokes in one column, one under the other
	Parent.Reset();
	for (int32 k = 0; k < Free.Num(); ++k)
	{
		Parent.Add(k);
	}
	for (int32 p = 0; p < Free.Num(); ++p)
	{
		for (int32 q = p + 1; q < Free.Num(); ++q)
		{
			const FUiStroke& P = Strokes[Free[p]];
			const FUiStroke& Q = Strokes[Free[q]];
			const double Lmin = FMath::Min(StrokeLength(P), StrokeLength(Q));
			const double Gap = FMath::Max(MinY(Q) - MaxY(P), MinY(P) - MaxY(Q));
			if (FMath::Abs(MidX(P) - MidX(Q)) <= FMath::Max(1.5, 0.1 * Lmin) + (StrokeWidth(P) + StrokeWidth(Q)) / 2.0 && Gap <= Lmin)
			{
				Parent[Find(p)] = Find(q);
			}
		}
	}
	TMap<int32, int32> OneOf;
	TArray<TArray<int32>> Ones;
	for (int32 k = 0; k < Free.Num(); ++k)
	{
		const int32 Root = Find(k);
		const int32* Found = OneOf.Find(Root);
		const int32 At = Found ? *Found : Ones.AddDefaulted();
		OneOf.Add(Root, At);
		Ones[At].Add(Free[k]);
	}
	for (TArray<int32>& One : Ones)
	{
		// one that meets a horizontal stroke is a box's side, no 1: the cell gets a stroke that reads nothing
		bool bTouches = false;
		for (const int32 v : One)
		{
			for (const int32 h : Hs)
			{
				const double Reach = 1.5 + (StrokeWidth(Strokes[v]) + StrokeWidth(Strokes[h])) / 2.0;
				bTouches |= PointToStroke(Strokes[v].A, Strokes[h]) <= Reach || PointToStroke(Strokes[v].B, Strokes[h]) <= Reach;
			}
		}
		if (bTouches)
		{
			One.Add(NoDigit);
		}
		OutCells.Add(MoveTemp(One));
	}
}

/** Numbers drawn with strokes (DrawLine and the like) read back as text: the strokes grouped into digit cells
 *  (StrokeCells), each read as a seven-segment digit (StrokeDigit), and digits of one height side by side on one line
 *  joined into a string. Refused, so read as nothing: a cell that holds another stroke inside it (a box around a
 *  number), a digit with a stroke left over at its edge (one that may have been its own), a join across strokes left
 *  over between two digits, a string of 1s alone (a lone upright stroke is more often a rule than a 1). Letters,
 *  slanted strokes and other shapes read no text. In canvas pixels. */
static void UiStrokeText(const TArray<FUiStroke>& All, const FVector2D& Pixels, TArray<FUiElement>& Out)
{
	if (All.Num() == 0 || All.Num() > 1000)
	{
		return;  // none, or more strokes than a HUD draws numbers with: no reading
	}
	TArray<TArray<int32>> Cells;
	StrokeCells(All, Cells);
	struct FDigit
	{
		TCHAR Char = 0;
		FBox2D Box = FBox2D(ForceInit);  // the centre lines'
		FBox2D Drawn = FBox2D(ForceInit);  // as drawn
	};
	TArray<FDigit> Read;
	TArray<int32> Unread;  // the strokes of cells that read nothing
	for (const TArray<int32>& Cell : Cells)
	{
		TCHAR C = StrokeDigit(Cell, All);
		const FBox2D Box = CentreBox(Cell, All);
		if (C)
		{
			// a cell with another stroke inside it is a box around something, not a digit
			double M = 1.0;
			for (const int32 i : Cell)
			{
				M = FMath::Max(M, 1.0 + StrokeWidth(All[i]));  // a digit's cell holds no NoDigit
			}
			for (int32 i = 0; i < All.Num() && C; ++i)
			{
				const double X = MidX(All[i]), Y = MidY(All[i]);
				if (!Cell.Contains(i) && X > Box.Min.X + M && X < Box.Max.X - M && Y > Box.Min.Y + M && Y < Box.Max.Y - M)
				{
					C = 0;
				}
			}
		}
		if (C)
		{
			FDigit D;
			D.Char = C;
			D.Box = Box;
			for (const int32 i : Cell)
			{
				D.Drawn += StrokeBox(All[i]);
			}
			Read.Add(D);
		}
		else
		{
			for (const int32 i : Cell)
			{
				if (i != NoDigit)
				{
					Unread.Add(i);
				}
			}
		}
	}
	// a stroke of a digit's size left over at a digit's edge may have been part of it: that digit reads nothing
	auto Between = [&](double X0, double X1, double Y0, double Y1, double MaxLength)
	{
		for (const int32 i : Unread)
		{
			const FUiStroke& S = All[i];
			if (StrokeLength(S) <= MaxLength && MidX(S) >= X0 && MidX(S) <= X1 && MinY(S) < Y1 && MaxY(S) > Y0)
			{
				return true;
			}
		}
		return false;
	};
	TArray<FDigit> Digits;
	for (const FDigit& D : Read)
	{
		const double H = D.Box.Max.Y - D.Box.Min.Y;
		const double Tol = 0.3 * (D.Box.Max.X - D.Box.Min.X) + (D.Drawn.Max.X - D.Drawn.Min.X - (D.Box.Max.X - D.Box.Min.X));
		if (!Between(D.Box.Min.X - Tol, D.Box.Max.X + Tol, D.Box.Min.Y, D.Box.Max.Y, 1.5 * H))
		{
			Digits.Add(D);
		}
	}
	Digits.Sort([](const FDigit& L, const FDigit& R) { return L.Box.Min.X < R.Box.Min.X; });
	TArray<bool> Taken;
	Taken.Init(false, Digits.Num());
	for (int32 i = 0; i < Digits.Num(); ++i)
	{
		if (Taken[i])
		{
			continue;
		}
		Taken[i] = true;
		FString Text;
		Text.AppendChar(Digits[i].Char);
		FBox2D Drawn = Digits[i].Drawn;
		const FDigit* Last = &Digits[i];
		const double H = Digits[i].Box.Max.Y - Digits[i].Box.Min.Y;
		for (int32 j = i + 1; j < Digits.Num(); ++j)
		{
			const FDigit& D = Digits[j];
			const double Hj = D.Box.Max.Y - D.Box.Min.Y;
			const double Overlap = FMath::Min(D.Box.Max.Y, Last->Box.Max.Y) - FMath::Max(D.Box.Min.Y, Last->Box.Min.Y);
			const double Gap = D.Box.Min.X - Last->Box.Max.X;
			if (Taken[j] || Hj < 0.75 * H || Hj > 1.33 * H || Overlap < 0.7 * FMath::Min(H, Hj) || Gap < -0.1 * H || Gap > 1.6 * FMath::Max(H, Hj))
			{
				continue;
			}
			if (Between(Last->Box.Max.X + 1e-3, D.Box.Min.X - 1e-3, D.Box.Min.Y, D.Box.Max.Y, 1.5 * H))
			{
				continue;  // a digit between them didn't read
			}
			Taken[j] = true;
			Text.AppendChar(D.Char);
			Drawn += D.Drawn;
			Last = &D;
		}
		bool bOnlyOnes = true;
		for (const TCHAR C : Text)
		{
			bOnlyOnes &= C == TEXT('1');
		}
		const bool bOnCanvas = Drawn.Max.X > 0.0 && Drawn.Min.X < Pixels.X && Drawn.Max.Y > 0.0 && Drawn.Min.Y < Pixels.Y;
		if (bOnlyOnes || !bOnCanvas)
		{
			continue;
		}
		FUiElement E;
		E.Source = TEXT("canvas");
		E.Kind = TEXT("text");
		E.Name = TEXT("CanvasStrokeText");
		E.Class = E.Name;
		E.Text = Text;
		CanvasRect(Drawn, Pixels, E);
		Out.Add(MoveTemp(E));
	}
}

/** What a canvas holds when the HUD has drawn: its batched triangles, read back as strings (quads on a font texture),
 *  boxes (on the white texture) and images (on any other texture), each run of triangles that share vertices one
 *  element; its batched lines as line elements (UiLines), and as text where they draw digits (UiStrokeText); nearly
 *  transparent ones and ones off the canvas left out (a line is always drawn opaque). Positions in canvas pixels, the
 *  DPI scale applied to what was not drawn already scaled (glyphs are). */
static void UiCanvas(FCanvas& Canvas, TArray<FUiElement>& Out)
{
	const FRenderTarget* Target = Canvas.GetRenderTarget();
	const FIntPoint Size = Target ? Target->GetSizeXY() : FIntPoint::ZeroValue;
	if (Size.X <= 0 || Size.Y <= 0)
	{
		return;
	}
	const FVector2D Pixels(Size.X, Size.Y);
	const double Dpi = Canvas.GetDPIScale() > 0.f ? Canvas.GetDPIScale() : 1.0;
	TMap<FUiGlyphKey, FUiGlyph> Glyphs;
	TSet<const FTexture*> FontTextures;
	bool bGlyphsRead = false;
	TArray<FUiGlyphQuad> Quads;  // the frame's glyph quads in the order drawn
	TArray<FUiElement> Shapes;
	TArray<FUiStroke> Strokes;  // every line of the frame, for digits drawn with strokes
	for (FCanvas::FCanvasSortElement& Sorted : Canvas.SortedElements)
	{
		for (FCanvasBaseRenderItem* Item : Sorted.RenderBatchArray)
		{
			FCanvasBatchedElementRenderItem* Batch = Item ? Item->GetCanvasBatchedElementRenderItem() : nullptr;
			const FBatchedElements* Elements = Batch ? Batch->GetBatchedElements() : nullptr;
			if (!Elements)
			{
				continue;
			}
			// lines (DrawLine, K2_DrawLine, K2_DrawBox's sides): line elements, and strokes that may draw digits
			TArray<FUiStroke> Lines;
			ReadLines(FUiLinesTag(), *Elements, Lines);
			for (FUiStroke& S : Lines)
			{
				S.A *= Dpi;
				S.B *= Dpi;
				S.Thickness *= Dpi;
			}
			UiLines(Lines, Pixels, Shapes);
			Strokes.Append(Lines);
			TArray<FUiTri> Tris;
			const TArray<FSimpleElementVertex>* Verts = nullptr;
			ReadBatch(FUiBatchTag(), *Elements, Tris, Verts);
			if (!Verts || Tris.Num() == 0)
			{
				continue;
			}
			if (!bGlyphsRead)
			{
				UiGlyphs(Glyphs, FontTextures);
				bGlyphsRead = true;
			}
			for (int32 i = 0; i < Tris.Num();)
			{
				// a run: the triangles after the first that share a vertex with the one before them (a quad's two)
				int32 End = i + 1;
				while (End < Tris.Num() && Tris[End].Texture == Tris[i].Texture && SharesVertex(Tris[End], Tris[End - 1]))
				{
					++End;
				}
				const bool bGlyph = FontTextures.Contains(Tris[i].Texture);
				const double Scale = bGlyph ? 1.0 : Dpi;
				FBox2D Box(ForceInit);
				float Alpha = 0.f;
				int32 TopLeft = -1;  // a glyph's texel: the vertex with the smallest texture coordinates
				for (int32 t = i; t < End; ++t)
				{
					for (int32 k : Tris[t].V)
					{
						if (!Verts->IsValidIndex(k))
						{
							continue;
						}
						const FSimpleElementVertex& V = (*Verts)[k];
						const FVector4d P = V.Position.GetVector4d();
						const double W = FMath::Abs(P.W) > 1e-6 ? P.W : 1.0;
						Box += FVector2D(P.X / W * Scale, P.Y / W * Scale);
						Alpha = FMath::Max(Alpha, V.Color.A);
						if (TopLeft < 0 || V.TextureCoordinate.X + V.TextureCoordinate.Y < (*Verts)[TopLeft].TextureCoordinate.X + (*Verts)[TopLeft].TextureCoordinate.Y)
						{
							TopLeft = k;
						}
					}
				}
				const bool bOnCanvas = Box.bIsValid && Box.Max.X > 0.0 && Box.Min.X < Pixels.X && Box.Max.Y > 0.0 && Box.Min.Y < Pixels.Y &&
					Box.Max.X - Box.Min.X >= 0.5 && Box.Max.Y - Box.Min.Y >= 0.5;
				if (Alpha > UiAlphaFloor && bOnCanvas && bGlyph && TopLeft >= 0)
				{
					const FVector2f UV = (*Verts)[TopLeft].TextureCoordinate;
					const FIntPoint TexSize(FMath::Max(1u, Tris[i].Texture->GetSizeX()), FMath::Max(1u, Tris[i].Texture->GetSizeY()));
					FUiGlyphQuad Q;
					Q.Key = FUiGlyphKey(Tris[i].Texture, ((uint32)FMath::RoundToInt(UV.X * TexSize.X) << 16) | (uint32)FMath::RoundToInt(UV.Y * TexSize.Y));
					Q.Glyph = Glyphs.Find(Q.Key);
					Q.Box = Box;
					Quads.Add(Q);
				}
				else if (Alpha > UiAlphaFloor && bOnCanvas && !bGlyph)
				{
					FUiElement E;
					E.Source = TEXT("canvas");
					const bool bBox = Tris[i].Texture == GWhiteTexture;
					E.Kind = bBox ? TEXT("box") : TEXT("image");
					E.Name = bBox ? TEXT("CanvasRect") : TEXT("CanvasTexture");
					E.Class = E.Name;
					E.bHasRect = true;
					E.X = Box.Min.X / Pixels.X;
					E.Y = Box.Min.Y / Pixels.Y;
					E.W = (Box.Max.X - Box.Min.X) / Pixels.X;
					E.H = (Box.Max.Y - Box.Min.Y) / Pixels.Y;
					Shapes.Add(MoveTemp(E));
				}
				i = End;
			}
		}
	}
	UiStrings(Quads, Out, Pixels);
	UiStrokeText(Strokes, Pixels, Out);
	Out.Append(MoveTemp(Shapes));
}

static TSharedPtr<FJsonValue> UiField(const FUiElement& E, const FString& F)
{
	if (F == TEXT("count"))
	{
		return Num(1.0);
	}
	if (F == TEXT("text"))
	{
		return E.Kind == TEXT("text") ? Str(E.Text) : Null();
	}
	if (IsRectField(F) && E.bHasRect)
	{
		return Num(F == TEXT("x") ? E.X : F == TEXT("y") ? E.Y : F == TEXT("w") ? E.W : E.H);
	}
	return Null();
}

// Text read from the frame as drawn (UiOcr): the fallback for text no reading above reads, whatever drew it (lines,
// textures, materials, widgets that paint their own text). Only a ui query that asks for text inside a rect reads it:
// the frame is captured after the UI is drawn, cropped to the rect, and read here. The reader is small and strict:
// the text must stand out from an even background in one colour; its marks are split into lines and glyphs, and each
// glyph is matched against the centre lines of 0-9, A-Z and a few signs (each in the shapes stroke fonts draw them:
// plain strokes, cut corners, segments, slashed zeros, diagonal 1, 4 and 7). A glyph reads only when one character
// matches it closely and no other comes near; anything else (a glyph that fits two characters, an unknown mark, a
// line cut by the rect, a busy background) reads nothing for that line rather than a guess.

struct FOcrPoint
{
	double X = 0.0, Y = 0.0;
};

/** One character's shape: its centre-line segments in the normalised glyph space (OcrNormal), points along them, and
 *  the distance from every cell of the glyph grid to them. */
struct FOcrShape
{
	TCHAR Char = 0;
	double Aspect = 0.0;  // max(width, 0.3 height) / height of its centre lines
	double Step = 0.0;  // the length (in heights) each sample stands for
	bool bSquare = false;  // it has a square corner (an upright and a level line meeting): a segment font's shape
	TArray<FOcrPoint> Samples;
	TArray<float> Dist;
};

/** One line of text read in an image: its text and its pixel box (x0, y0 inclusive; x1, y1 exclusive). */
struct FOcrLine
{
	FString Text;
	int32 X0 = 0, Y0 = 0, X1 = 0, Y1 = 0;
};

// the glyph grid: normalised x (centred, a glyph's width scaled to OcrWidth) and y (0 top, 1 bottom), with a margin
static constexpr double OcrWidth = 0.6;
static constexpr double OcrGridX0 = -0.5, OcrGridY0 = -0.25, OcrCell = 0.02;
static constexpr int32 OcrGridW = 50, OcrGridH = 75;
// reading a glyph (OcrGlyphScores, OcrGlyphDecide): the loose distance's base (in heights), the tight one's share of it, how much a shape
// may miss and still fit (loose) and in detail (tight), how much every other character must miss (loose) and by how
// much more (tight)
static constexpr double OcrLoose = 0.04, OcrTight = 0.6, OcrFits = 0.1, OcrDetail = 0.4, OcrApart = 0.03, OcrMargin = 0.2;
// how much worse in detail a glyph's square-cornered shapes must be for it to show cut or round corners
static constexpr double OcrCorner = 0.08;
// the marks' cut, a share of the way from the background to the ink
static constexpr double OcrCut = 0.33;

// Character shapes as centre lines on a 4 x 6 box (x right, y down): polylines of "x,y" points split by ';'. A
// character has every shape it is commonly drawn in, so characters that look alike in some font (0, O, D; 5, S;
// 8, B; 1, I) all match such a glyph and it reads nothing.
static const struct
{
	TCHAR Char;
	const char* Lines;
} OcrShapeDefs[] = {
	{TEXT('0'), "1,0 3,0 4,1 4,5 3,6 1,6 0,5 0,1 1,0"},
	{TEXT('0'), "0,0 4,0 4,6 0,6 0,0"},
	{TEXT('0'), "1.5,0 2.5,0 4,1.5 4,4.5 2.5,6 1.5,6 0,4.5 0,1.5 1.5,0"},
	{TEXT('0'), "1,0 3,0 4,1 4,5 3,6 1,6 0,5 0,1 1,0;4,1 0,5"},
	{TEXT('0'), "1,0 3,0 4,1 4,5 3,6 1,6 0,5 0,1 1,0;3,1.5 1,4.5"},
	{TEXT('0'), "0,0 4,0 4,6 0,6 0,0;4,0 0,6"},
	{TEXT('0'), "1.5,0 2.5,0 4,1.5 4,4.5 2.5,6 1.5,6 0,4.5 0,1.5 1.5,0;3.5,1 0.5,5"},
	{TEXT('O'), "1,0 3,0 4,1 4,5 3,6 1,6 0,5 0,1 1,0"},
	{TEXT('O'), "0,0 4,0 4,6 0,6 0,0"},
	{TEXT('O'), "1.5,0 2.5,0 4,1.5 4,4.5 2.5,6 1.5,6 0,4.5 0,1.5 1.5,0"},
	{TEXT('D'), "0,0 2.5,0 4,1.5 4,4.5 2.5,6 0,6 0,0"},
	{TEXT('D'), "0,0 4,0 4,6 0,6 0,0"},
	{TEXT('Q'), "1,0 3,0 4,1 4,5 3,6 1,6 0,5 0,1 1,0;2.5,4.5 4,6"},
	{TEXT('Q'), "0,0 4,0 4,6 0,6 0,0;2.5,4.5 4,6"},
	{TEXT('1'), "2,0 2,6"},
	{TEXT('1'), "1,1 2,0 2,6"},
	{TEXT('1'), "0.5,1.5 2,0 2,6"},
	{TEXT('1'), "1,1 2,0 2,6;1,6 3,6"},
	{TEXT('I'), "2,0 2,6"},
	{TEXT('I'), "1,0 3,0;2,0 2,6;1,6 3,6"},
	{TEXT('2'), "0,1 1,0 3,0 4,1 4,2 0,6 4,6"},
	{TEXT('2'), "0,1 1,0 3,0 4,1 4,2.5 0,6 4,6"},
	{TEXT('2'), "0,0 4,0 4,3 0,3 0,6 4,6"},
	{TEXT('2'), "0,1 1,0 3,0 4,1 4,2 3,3 1,3 0,4 0,6 4,6"},
	{TEXT('2'), "0,0 4,0 4,2 0,6 4,6"},
	{TEXT('Z'), "0,0 4,0 0,6 4,6"},
	{TEXT('Z'), "0,0 4,0 4,1 0,5 0,6 4,6"},
	{TEXT('3'), "0,0 4,0 4,6 0,6;0,3 4,3"},
	{TEXT('3'), "0,1 1,0 3,0 4,1 4,2 3,3 4,4 4,5 3,6 1,6 0,5;1,3 3,3"},
	{TEXT('3'), "0,1 1,0 3,0 4,1 4,2 3,3 4,4 4,5 3,6 1,6 0,5;2,3 3,3"},
	{TEXT('3'), "0,0 4,0 2,2.5 3,2.5 4,3.5 4,5 3,6 1,6 0,5"},
	{TEXT('3'), "0,0 4,0 1.5,3 3,3 4,4 4,5 3,6 0,6"},
	{TEXT('4'), "3,6 3,0 0,4 4,4"},
	{TEXT('4'), "3,6 3,0 0,4.5 4,4.5"},
	{TEXT('4'), "0,0 0,3 4,3;4,0 4,6"},
	{TEXT('4'), "0,0 0,4 4,4;3,2 3,6"},
	{TEXT('4'), "2.5,6 2.5,0 0,4 4,4"},
	{TEXT('5'), "4,0 0,0 0,3 4,3 4,6 0,6"},
	{TEXT('5'), "4,0 0,0 0,3 3,3 4,4 4,5 3,6 0,6"},
	{TEXT('5'), "4,0 0,0 0,2.5 3,2.5 4,3.5 4,5 3,6 1,6 0,5"},
	{TEXT('5'), "4,0 0,0 0,3 3,3 4,4 4,5 3,6 1,6 0,5"},
	{TEXT('5'), "4,0 1,0 0,1 0,3 3,3 4,4 4,5 3,6 0,6"},
	{TEXT('5'), "4,0 1,0 0,1 0,2 1,3 3,3 4,4 4,5 3,6 0,6"},
	{TEXT('S'), "4,1 3,0 1,0 0,1 0,2 1,3 3,3 4,4 4,5 3,6 1,6 0,5"},
	{TEXT('S'), "4,0 0,0 0,3 4,3 4,6 0,6"},
	{TEXT('S'), "4,1 3,0 1,0 0,1 0,2 1,3 3,3 4,4 4,5 3,6 0,6"},
	{TEXT('S'), "4,0.5 3.5,0 1,0 0,1 0,2 1,3 3,3 4,4 4,5 3,6 1,6 0,5"},
	{TEXT('6'), "4,0 0,0 0,6 4,6 4,3 0,3"},
	{TEXT('6'), "0,0 0,6 4,6 4,3 0,3"},
	{TEXT('6'), "3,0 1,0 0,1 0,5 1,6 3,6 4,5 4,4 3,3 0,3"},
	{TEXT('6'), "4,1 3,0 1,0 0,1 0,5 1,6 3,6 4,5 4,4 3,3 0,3"},
	{TEXT('6'), "3,0 0,3 0,5 1,6 3,6 4,5 4,4 3,3 0,3"},
	{TEXT('6'), "4,0 1,0 0,1 0,5 1,6 3,6 4,5 4,4 3,3 0,3"},
	{TEXT('G'), "4,1 3,0 1,0 0,1 0,5 1,6 3,6 4,5 4,3 2,3"},
	{TEXT('G'), "4,0 0,0 0,6 4,6 4,3 2,3"},
	{TEXT('G'), "4,0 1,0 0,1 0,5 1,6 4,6 4,3 2,3"},
	{TEXT('7'), "0,0 4,0 1,6"},
	{TEXT('7'), "0,0 4,0 4,6"},
	{TEXT('7'), "0,1 0,0 4,0 4,6"},
	{TEXT('7'), "0,0 4,0 4,1 1.5,6"},
	{TEXT('7'), "0,0 4,0 2,6"},
	{TEXT('7'), "0,0 4,0 4,1.5 2,6"},
	{TEXT('8'), "1,0 3,0 4,1 4,2 3,3 1,3 0,2 0,1 1,0;1,3 0,4 0,5 1,6 3,6 4,5 4,4 3,3"},
	{TEXT('8'), "0,0 4,0 4,6 0,6 0,0;0,3 4,3"},
	{TEXT('8'), "1,0 3,0 4,1 4,5 3,6 1,6 0,5 0,1 1,0;0,3 4,3"},
	{TEXT('B'), "0,0 3,0 4,1 4,2 3,3 0,3;3,3 4,4 4,5 3,6 0,6 0,0"},
	{TEXT('B'), "0,0 4,0 4,6 0,6 0,0;0,3 4,3"},
	{TEXT('B'), "0,0 3,0 4,1 4,2 3,3 4,4 4,5 3,6 0,6 0,0;0,3 3,3"},
	{TEXT('9'), "4,3 0,3 0,0 4,0 4,6 0,6"},
	{TEXT('9'), "4,3 0,3 0,0 4,0 4,6"},
	{TEXT('9'), "4,3 1,3 0,2 0,1 1,0 3,0 4,1 4,5 3,6 1,6"},
	{TEXT('9'), "4,3 1,3 0,2 0,1 1,0 3,0 4,1 4,6"},
	{TEXT('9'), "4,3 1,3 0,2 0,1 1,0 3,0 4,1 4,3 1,6"},
	{TEXT('9'), "4,3 1,3 0,2 0,1 1,0 3,0 4,1 4,5 3,6 0,6"},
	{TEXT('A'), "0,6 2,0 4,6;1,3.5 3,3.5"},
	{TEXT('A'), "0,6 0,1 1,0 3,0 4,1 4,6;0,3 4,3"},
	{TEXT('A'), "0,6 0,0 4,0 4,6;0,3 4,3"},
	{TEXT('A'), "0,6 0,2 2,0 4,2 4,6;0,3.5 4,3.5"},
	{TEXT('A'), "0,6 1.5,0 2.5,0 4,6;0.75,3.5 3.25,3.5"},
	{TEXT('C'), "4,0 1,0 0,1 0,5 1,6 4,6"},
	{TEXT('C'), "4,0 0,0 0,6 4,6"},
	{TEXT('C'), "4,1 3,0 1,0 0,1 0,5 1,6 3,6 4,5"},
	{TEXT('E'), "4,0 0,0 0,6 4,6;0,3 3,3"},
	{TEXT('E'), "4,0 0,0 0,6 4,6;0,3 4,3"},
	{TEXT('F'), "4,0 0,0 0,6;0,3 3,3"},
	{TEXT('F'), "4,0 0,0 0,6;0,3 4,3"},
	{TEXT('H'), "0,0 0,6;4,0 4,6;0,3 4,3"},
	{TEXT('J'), "4,0 4,5 3,6 1,6 0,5 0,4"},
	{TEXT('J'), "4,0 4,6 0,6 0,4"},
	{TEXT('J'), "1,0 4,0;3,0 3,5 2,6 1,6 0,5"},
	{TEXT('K'), "0,0 0,6;4,0 0,3.5;1.5,2.5 4,6"},
	{TEXT('K'), "0,0 0,6;4,0 0,3 4,6"},
	{TEXT('K'), "0,0 0,6;0,3 2,3 4,0;2,3 4,6"},
	{TEXT('L'), "0,0 0,6 4,6"},
	{TEXT('M'), "0,6 0,0 2,3 4,0 4,6"},
	{TEXT('M'), "0,6 0,0 2,4 4,0 4,6"},
	{TEXT('M'), "0,6 0,0 2,2 4,0 4,6"},
	{TEXT('M'), "0,6 1,0 2,3 3,0 4,6"},
	{TEXT('M'), "0,6 0,0 2,6 4,0 4,6"},
	{TEXT('N'), "0,6 0,0 4,6 4,0"},
	{TEXT('P'), "0,6 0,0 3,0 4,1 4,2 3,3 0,3"},
	{TEXT('P'), "0,6 0,0 4,0 4,3 0,3"},
	{TEXT('R'), "0,6 0,0 3,0 4,1 4,2 3,3 0,3;2,3 4,6"},
	{TEXT('R'), "0,6 0,0 4,0 4,3 0,3;2,3 4,6"},
	{TEXT('R'), "0,6 0,0 3,0 4,1 4,2 3,3 0,3;3,3 4,4 4,6"},
	{TEXT('R'), "0,6 0,0 3,0 4,1 4,2 3,3 0,3;1,3 4,6"},
	{TEXT('T'), "0,0 4,0;2,0 2,6"},
	{TEXT('U'), "0,0 0,5 1,6 3,6 4,5 4,0"},
	{TEXT('U'), "0,0 0,6 4,6 4,0"},
	{TEXT('V'), "0,0 2,6 4,0"},
	{TEXT('V'), "0,0 0,3 2,6 4,3 4,0"},
	{TEXT('W'), "0,0 1,6 2,3 3,6 4,0"},
	{TEXT('W'), "0,0 0,6 2,3 4,6 4,0"},
	{TEXT('W'), "0,0 1,6 2,2 3,6 4,0"},
	{TEXT('W'), "0,0 0,6 2,4 4,6 4,0"},
	{TEXT('X'), "0,0 4,6;4,0 0,6"},
	{TEXT('Y'), "0,0 2,3 4,0;2,3 2,6"},
	{TEXT('Y'), "0,0 2,2.5 4,0;2,2.5 2,6"},
	{TEXT('%'), "4,0 0,6;0,0 1.2,0 1.2,1.5 0,1.5 0,0;2.8,4.5 4,4.5 4,6 2.8,6 2.8,4.5"},
	{TEXT('%'), "4,0 0,6;0.5,0 1,0 1.5,0.5 1.5,1 1,1.5 0.5,1.5 0,1 0,0.5 0.5,0;3,4.5 3.5,4.5 4,5 4,5.5 3.5,6 3,6 2.5,5.5 2.5,5 3,4.5"},
	{TEXT('/'), "4,0 0,6"},
};

static FOcrPoint OcrNormal(double X, double Y, double CentreX, double Top, double ScaleX, double Height)
{
	return FOcrPoint{(X - CentreX) / ScaleX * OcrWidth, (Y - Top) / Height};
}

static int32 OcrCellAt(const FOcrPoint& P)
{
	const int32 Cx = FMath::Clamp(FMath::FloorToInt((P.X - OcrGridX0) / OcrCell), 0, OcrGridW - 1);
	const int32 Cy = FMath::Clamp(FMath::FloorToInt((P.Y - OcrGridY0) / OcrCell), 0, OcrGridH - 1);
	return Cy * OcrGridW + Cx;
}

static double OcrSegDist(const FOcrPoint& P, const FOcrPoint& A, const FOcrPoint& B)
{
	const double Dx = B.X - A.X, Dy = B.Y - A.Y;
	const double L = Dx * Dx + Dy * Dy;
	const double T = L > 0.0 ? FMath::Clamp(((P.X - A.X) * Dx + (P.Y - A.Y) * Dy) / L, 0.0, 1.0) : 0.0;
	const double Ex = A.X + T * Dx - P.X, Ey = A.Y + T * Dy - P.Y;
	return FMath::Sqrt(Ex * Ex + Ey * Ey);
}

/** Every character shape, parsed and laid on the glyph grid once. */
static const TArray<FOcrShape>& OcrShapes()
{
	static TArray<FOcrShape> Shapes;
	if (!Shapes.IsEmpty())
	{
		return Shapes;
	}
	for (const auto& Def : OcrShapeDefs)
	{
		// parse the polylines into segments
		TArray<FOcrPoint> A, B;
		TArray<FOcrPoint> Line;
		const char* S = Def.Lines;
		auto Flush = [&]()
		{
			for (int32 i = 0; i + 1 < Line.Num(); ++i)
			{
				A.Add(Line[i]);
				B.Add(Line[i + 1]);
			}
			Line.Reset();
		};
		while (*S)
		{
			if (*S == ';')
			{
				Flush();
				++S;
				continue;
			}
			if (*S == ' ')
			{
				++S;
				continue;
			}
			double V[2] = {0.0, 0.0};
			for (int32 k = 0; k < 2; ++k)
			{
				double Whole = 0.0, Frac = 0.0, Scale = 1.0;
				bool bFrac = false;
				while ((*S >= '0' && *S <= '9') || *S == '.')
				{
					if (*S == '.')
					{
						bFrac = true;
					}
					else if (bFrac)
					{
						Scale *= 0.1;
						Frac += (*S - '0') * Scale;
					}
					else
					{
						Whole = Whole * 10.0 + (*S - '0');
					}
					++S;
				}
				V[k] = Whole + Frac;
				if (k == 0 && *S == ',')
				{
					++S;
				}
			}
			Line.Add(FOcrPoint{V[0], V[1]});
		}
		Flush();
		FOcrShape Shape;
		for (int32 i = 0; i + 1 < A.Num(); ++i)
		{
			const bool bJoin = A[i + 1].X == B[i].X && A[i + 1].Y == B[i].Y;
			const bool bLevelUpright = (A[i].Y == B[i].Y && A[i + 1].X == B[i + 1].X) || (A[i].X == B[i].X && A[i + 1].Y == B[i + 1].Y);
			Shape.bSquare = Shape.bSquare || (bJoin && bLevelUpright);
		}
		double X0 = 1e9, X1 = -1e9, Y0 = 1e9, Y1 = -1e9;
		for (int32 i = 0; i < A.Num(); ++i)
		{
			X0 = FMath::Min(X0, FMath::Min(A[i].X, B[i].X));
			X1 = FMath::Max(X1, FMath::Max(A[i].X, B[i].X));
			Y0 = FMath::Min(Y0, FMath::Min(A[i].Y, B[i].Y));
			Y1 = FMath::Max(Y1, FMath::Max(A[i].Y, B[i].Y));
		}
		const double H = FMath::Max(Y1 - Y0, 1e-6);
		const double Sx = FMath::Max(X1 - X0, 0.3 * H);
		Shape.Char = Def.Char;
		Shape.Aspect = Sx / H;
		for (int32 i = 0; i < A.Num(); ++i)
		{
			A[i] = OcrNormal(A[i].X, A[i].Y, (X0 + X1) / 2.0, Y0, Sx, H);
			B[i] = OcrNormal(B[i].X, B[i].Y, (X0 + X1) / 2.0, Y0, Sx, H);
			const double Dx = B[i].X - A[i].X, Dy = B[i].Y - A[i].Y;
			const int32 Steps = FMath::Max(1, FMath::RoundToInt(FMath::Sqrt(Dx * Dx + Dy * Dy) / 0.02));
			for (int32 k = (i > 0 && A[i].X == B[i - 1].X && A[i].Y == B[i - 1].Y) ? 1 : 0; k <= Steps; ++k)
			{
				Shape.Samples.Add(FOcrPoint{A[i].X + Dx * k / Steps, A[i].Y + Dy * k / Steps});
			}
		}
		double Length = 0.0;
		for (int32 i = 0; i < A.Num(); ++i)
		{
			// lengths in heights: x back from the normalised width
			const double Dx = (B[i].X - A[i].X) / OcrWidth * Sx / H, Dy = B[i].Y - A[i].Y;
			Length += FMath::Sqrt(Dx * Dx + Dy * Dy);
		}
		Shape.Step = Length / FMath::Max(1, Shape.Samples.Num());
		Shape.Dist.SetNumUninitialized(OcrGridW * OcrGridH);
		for (int32 Cy = 0; Cy < OcrGridH; ++Cy)
		{
			for (int32 Cx = 0; Cx < OcrGridW; ++Cx)
			{
				const FOcrPoint P{OcrGridX0 + (Cx + 0.5) * OcrCell, OcrGridY0 + (Cy + 0.5) * OcrCell};
				double D = 1e9;
				for (int32 i = 0; i < A.Num(); ++i)
				{
					D = FMath::Min(D, OcrSegDist(P, A[i], B[i]));
				}
				Shape.Dist[Cy * OcrGridW + Cx] = (float)D;
			}
		}
		Shapes.Add(Shape);
	}
	return Shapes;
}

/** Thins a binary image (1 = mark, a blank border of one pixel) to lines one pixel wide (Zhang-Suen). */
static void OcrThin(TArray<uint8>& Im, int32 W, int32 H)
{
	TArray<int32> Del;
	bool bChanged = true;
	while (bChanged)
	{
		bChanged = false;
		for (int32 Pass = 0; Pass < 2; ++Pass)
		{
			Del.Reset();
			for (int32 y = 1; y < H - 1; ++y)
			{
				for (int32 x = 1; x < W - 1; ++x)
				{
					const int32 i = y * W + x;
					if (!Im[i])
					{
						continue;
					}
					const uint8 P[8] = {Im[i - W], Im[i - W + 1], Im[i + 1], Im[i + W + 1], Im[i + W], Im[i + W - 1], Im[i - 1], Im[i - W - 1]};
					int32 Count = 0, Turns = 0;
					for (int32 k = 0; k < 8; ++k)
					{
						Count += P[k];
						Turns += (!P[k] && P[(k + 1) % 8]) ? 1 : 0;
					}
					if (Count < 2 || Count > 6 || Turns != 1)
					{
						continue;
					}
					// P: 0 north, 2 east, 4 south, 6 west
					if (Pass == 0 ? (P[0] && P[2] && P[4]) || (P[2] && P[4] && P[6]) : (P[0] && P[2] && P[6]) || (P[0] && P[4] && P[6]))
					{
						continue;
					}
					Del.Add(i);
				}
			}
			for (const int32 i : Del)
			{
				Im[i] = 0;
			}
			bChanged = bChanged || !Del.IsEmpty();
		}
	}
}

/** A connected mark (8-connected pixels), its box (inclusive) and pixels. */
struct FOcrMark
{
	int32 X0 = 0, Y0 = 0, X1 = 0, Y1 = 0;
	TArray<int32> Pixels;
	bool bEdge = false;  // touches the image's edge
	int32 W() const { return X1 - X0 + 1; }
	int32 H() const { return Y1 - Y0 + 1; }
};

/** How a glyph scores against one character's shapes (OcrGlyphScores): the best of all its shapes [0], of those
 *  without square corners [1] and of those with [2]; Fit loose, Detail tight (lengths in heights; lower is better). */
struct FOcrScore
{
	TCHAR Char = 0;
	double Fit[3] = {1e9, 1e9, 1e9};
	double Detail[3] = {1e9, 1e9, 1e9};
	const FOcrShape* Shape[3] = {nullptr, nullptr, nullptr};
};

/** A glyph: marks side by side merged, its box (inclusive), how it scored, and what it read as (0: nothing). */
struct FOcrGlyph
{
	int32 X0 = 0, Y0 = 0, X1 = 0, Y1 = 0;
	TArray<int32> Marks;
	TArray<FOcrScore> Scores;
	double Stroke = 0.0, CentreX = 0.0, Top = 0.0, ScaleX = 0.0, Height = 0.0, Loose = 0.0;  // its centre lines' frame
	TCHAR Char = 0;
	int32 W() const { return X1 - X0 + 1; }
	int32 H() const { return Y1 - Y0 + 1; }
};

/** Which pixels are marks: the image's edge must be one even colour (its median), the marks must stand far apart from
 *  it (Otsu's split of the colour distance to it, the two classes well separated) and be the fewer. False when not. */
static bool OcrMarks(const TArray<FColor>& Px, int32 W, int32 H, TArray<uint8>& Mask)
{
	if (W < 8 || H < 8 || Px.Num() < W * H)
	{
		return false;
	}
	TArray<int32> Rs, Gs, Bs;
	auto Edge = [&](int32 x, int32 y)
	{
		const FColor& C = Px[y * W + x];
		Rs.Add(C.R);
		Gs.Add(C.G);
		Bs.Add(C.B);
	};
	for (int32 x = 0; x < W; ++x)
	{
		Edge(x, 0);
		Edge(x, H - 1);
	}
	for (int32 y = 1; y < H - 1; ++y)
	{
		Edge(0, y);
		Edge(W - 1, y);
	}
	auto Median = [](TArray<int32>& V)
	{
		V.Sort([](int32 L, int32 R) { return L < R; });
		return V[V.Num() / 2];
	};
	const int32 Br = Median(Rs), Bg = Median(Gs), Bb = Median(Bs);
	TArray<float> D;
	D.SetNumUninitialized(W * H);
	int32 Hist[256] = {0};
	for (int32 i = 0; i < W * H; ++i)
	{
		const double Dr = Px[i].R - Br, Dg = Px[i].G - Bg, Db = Px[i].B - Bb;
		D[i] = (float)FMath::Sqrt((Dr * Dr + Dg * Dg + Db * Db) / 3.0);
		++Hist[FMath::Clamp(FMath::FloorToInt(D[i]), 0, 255)];
	}
	// Otsu's split
	const double N = (double)W * H;
	double Sum = 0.0, SumSq = 0.0;
	for (int32 k = 0; k < 256; ++k)
	{
		Sum += (k + 0.5) * Hist[k];
		SumSq += (k + 0.5) * (k + 0.5) * Hist[k];
	}
	const double Total = SumSq / N - (Sum / N) * (Sum / N);
	double BestBetween = -1.0, Below = 0.0, SumBelow = 0.0;
	int32 Split = 0;
	for (int32 k = 0; k < 255; ++k)
	{
		Below += Hist[k];
		SumBelow += (k + 0.5) * Hist[k];
		if (Below <= 0.0 || Below >= N)
		{
			continue;
		}
		const double M0 = SumBelow / Below, M1 = (Sum - SumBelow) / (N - Below);
		const double Between = Below * (N - Below) / (N * N) * (M1 - M0) * (M1 - M0);
		if (Between > BestBetween)
		{
			BestBetween = Between;
			Split = k + 1;  // marks: distance >= Split
		}
	}
	if (Total <= 1.0 || BestBetween / Total < 0.8)
	{
		return false;  // no clear split between the background and the marks
	}
	TArray<float> Fore, Back;
	for (int32 i = 0; i < W * H; ++i)
	{
		(D[i] >= Split ? Fore : Back).Add(D[i]);
	}
	if (Fore.Num() < 8 || Fore.Num() > 0.45 * N)
	{
		return false;
	}
	Fore.Sort([](float L, float R) { return L < R; });
	Back.Sort([](float L, float R) { return L < R; });
	const double Ink = Fore[(int32)(Fore.Num() * 0.9)];
	const double Paper = Back[(int32)(Back.Num() * 0.98)];
	if (Ink < 40.0 || Ink < 3.0 * Paper)
	{
		return false;  // too faint, or a background that varies
	}
	// marks at a third of the way from the background to the ink (a thin line half on two rows still reads); faint
	// ink from a sixth of the way, to see strokes the marks lost
	const double Cut = Paper + OcrCut * (Ink - Paper), Faint = Paper + 0.16 * (Ink - Paper);
	Mask.SetNumZeroed(W * H);
	int32 EdgeMarks = 0;
	for (int32 i = 0; i < W * H; ++i)
	{
		Mask[i] = (uint8)(D[i] >= Cut ? 2 : (D[i] >= Faint ? 1 : 0));
	}
	for (int32 x = 0; x < W; ++x)
	{
		EdgeMarks += (Mask[x] == 2) + (Mask[(H - 1) * W + x] == 2);
	}
	for (int32 y = 1; y < H - 1; ++y)
	{
		EdgeMarks += (Mask[y * W] == 2) + (Mask[y * W + W - 1] == 2);
	}
	return EdgeMarks <= 0.1 * (2 * W + 2 * H);
}

/** Scores one glyph against every character shape (FOcrGlyph::Scores), by how much of the glyph's centre lines lies
 *  far from the shape's and how much of the shape's lies far from the glyph's (lengths in capital heights): at a loose
 *  distance whether it fits at all (the larger of the two), at a tight one the detail that tells near shapes apart
 *  (the two added). False when the glyph is too small or too bold to read. */
static bool OcrGlyphScores(FOcrGlyph& G, const TArray<FOcrMark>& Marks, int32 W)
{
	// the glyph alone, with a blank border, thinned to its centre lines
	const int32 Gw = G.W() + 2, Gh = G.H() + 2;
	TArray<uint8> Im;
	Im.SetNumZeroed(Gw * Gh);
	int32 Area = 0;
	for (const int32 m : G.Marks)
	{
		for (const int32 p : Marks[m].Pixels)
		{
			Im[(p / W - G.Y0 + 1) * Gw + p % W - G.X0 + 1] = 1;
			++Area;
		}
	}
	OcrThin(Im, Gw, Gh);
	TArray<FOcrPoint> Skel;
	for (int32 y = 0; y < Gh; ++y)
	{
		for (int32 x = 0; x < Gw; ++x)
		{
			if (Im[y * Gw + x])
			{
				Skel.Add(FOcrPoint{x - 1 + 0.5, y - 1 + 0.5});
			}
		}
	}
	if (Skel.Num() < 4)
	{
		return false;
	}
	// stroke width, and the box of the centre lines (the glyph's box less half a stroke on each side)
	G.Stroke = FMath::Max(1.0, (double)Area / Skel.Num());
	const double Cx0 = 0.5 * FMath::Min(G.Stroke, (double)G.W());
	G.CentreX = G.W() / 2.0;
	G.Top = 0.5 * G.Stroke;
	G.Height = G.H() - G.Stroke;
	if (G.Height < 4.0)
	{
		return false;
	}
	// how far a centre line may stray (in heights): a little, a pixel's rounding and half a stroke. A glyph too small
	// or too bold for that to stay small reads nothing.
	G.Loose = OcrLoose + 0.6 / G.Height + 0.5 * G.Stroke / G.Height;
	const double Tight = OcrTight * G.Loose;
	if (G.Loose > 0.15)
	{
		return false;
	}
	G.ScaleX = FMath::Max(G.W() - 2.0 * Cx0, 0.3 * G.Height);
	const double Aspect = G.ScaleX / G.Height;
	for (FOcrPoint& P : Skel)
	{
		P = OcrNormal(P.X, P.Y, G.CentreX, G.Top, G.ScaleX, G.Height);
	}
	// distance from every cell of the grid to the glyph's centre lines
	TArray<float> Dist;
	Dist.SetNumUninitialized(OcrGridW * OcrGridH);
	for (int32 Cy = 0; Cy < OcrGridH; ++Cy)
	{
		for (int32 Cx = 0; Cx < OcrGridW; ++Cx)
		{
			const double Px = OcrGridX0 + (Cx + 0.5) * OcrCell, Py = OcrGridY0 + (Cy + 0.5) * OcrCell;
			double D = 1e9;
			for (const FOcrPoint& S : Skel)
			{
				D = FMath::Min(D, (S.X - Px) * (S.X - Px) + (S.Y - Py) * (S.Y - Py));
			}
			Dist[Cy * OcrGridW + Cx] = (float)FMath::Sqrt(D);
		}
	}
	// each character's best shapes: of all, of those without square corners, of those with
	for (const FOcrShape& Shape : OcrShapes())
	{
		if (FMath::Max(Aspect, Shape.Aspect) / FMath::Min(Aspect, Shape.Aspect) > 1.8)
		{
			continue;  // far too narrow or too wide for it
		}
		int32 FarG = 0, FarS = 0, OffG = 0, OffS = 0;
		for (const FOcrPoint& P : Skel)
		{
			const double D = Shape.Dist[OcrCellAt(P)];
			FarG += D > G.Loose ? 1 : 0;
			OffG += D > Tight ? 1 : 0;
		}
		for (const FOcrPoint& P : Shape.Samples)
		{
			const double D = Dist[OcrCellAt(P)];
			FarS += D > G.Loose ? 1 : 0;
			OffS += D > Tight ? 1 : 0;
		}
		const double L = FMath::Max(FarG / G.Height, FarS * Shape.Step), T = OffG / G.Height + OffS * Shape.Step;
		int32 c = 0;
		while (c < G.Scores.Num() && G.Scores[c].Char != Shape.Char)
		{
			++c;
		}
		if (c == G.Scores.Num())
		{
			FOcrScore S;
			S.Char = Shape.Char;
			G.Scores.Add(S);
		}
		FOcrScore& S = G.Scores[c];
		S.Fit[0] = FMath::Min(S.Fit[0], L);
		if (T < S.Detail[0])
		{
			S.Detail[0] = T;
			S.Shape[0] = &Shape;
		}
		const int32 k = Shape.bSquare ? 2 : 1;
		S.Fit[k] = FMath::Min(S.Fit[k], L);
		if (T < S.Detail[k])
		{
			S.Detail[k] = T;
			S.Shape[k] = &Shape;
		}
	}
	return true;
}

/** Reads a scored glyph: the character whose shape fits and is best in detail, when every other character's best
 *  shape both misses by some length when loose and is far worse in detail, and no ink around the glyph (faint ink
 *  too) lies away from that shape (a stroke the marks lost); else 0. When the glyph shows cut or round corners (its
 *  character's best shape has none square, and its square-cornered shapes are worse in detail), other characters'
 *  square-cornered shapes are not near it: a 5 with cut corners is not a seven-segment S, while a 5 drawn with
 *  square segments is one, and reads nothing. */
static TCHAR OcrGlyphDecide(const FOcrGlyph& G, const TArray<uint8>& Mask, int32 W, int32 H)
{
	int32 Best = INDEX_NONE;
	for (int32 c = 0; c < G.Scores.Num(); ++c)
	{
		if (G.Scores[c].Fit[0] <= OcrFits && (Best == INDEX_NONE || G.Scores[c].Detail[0] < G.Scores[Best].Detail[0]))
		{
			Best = c;
		}
	}
	if (Best == INDEX_NONE || G.Scores[Best].Detail[0] > OcrDetail)
	{
		return 0;  // nothing fits, or nothing fits in detail
	}
	const FOcrScore& B = G.Scores[Best];
	const bool bCut = !B.Shape[0]->bSquare && B.Shape[2] && B.Detail[2] - B.Detail[0] >= OcrCorner;
	const int32 k = bCut ? 1 : 0;
	for (int32 c = 0; c < G.Scores.Num(); ++c)
	{
		const FOcrScore& S = G.Scores[c];
		if (c != Best && S.Shape[k] && (S.Fit[k] < OcrApart || S.Detail[k] - B.Detail[0] < OcrMargin))
		{
			return 0;  // another character comes near
		}
	}
	// ink around the glyph (faint too) away from the lines of every shape of the character: a stroke the marks lost,
	// so it may be another
	TArray<FOcrPoint> Ink;
	for (int32 y = FMath::Max(0, G.Y0 - 1); y <= FMath::Min(H - 1, G.Y1 + 1); ++y)
	{
		for (int32 x = FMath::Max(0, G.X0 - 1); x <= FMath::Min(W - 1, G.X1 + 1); ++x)
		{
			if (Mask[y * W + x])
			{
				Ink.Add(OcrNormal(x - G.X0 + 0.5, y - G.Y0 + 0.5, G.CentreX, G.Top, G.ScaleX, G.Height));
			}
		}
	}
	int32 Stray = Ink.Num();
	for (const FOcrShape& Shape : OcrShapes())
	{
		if (Shape.Char != B.Char)
		{
			continue;
		}
		int32 Far = 0;
		for (const FOcrPoint& P : Ink)
		{
			Far += Shape.Dist[OcrCellAt(P)] > G.Loose + 0.5 * G.Stroke / G.Height ? 1 : 0;
		}
		Stray = FMath::Min(Stray, Far);
	}
	return Stray <= FMath::Max(2.0, 0.03 * Ink.Num()) ? B.Char : 0;
}

/** A glyph shorter than the line's capitals: a full stop, a hyphen or a colon by its place and shape, else 0. */
static TCHAR OcrSmallChar(const FOcrGlyph& G, const TArray<FOcrMark>& Marks, int32 Top, int32 Bottom)
{
	const double Cap = Bottom - Top + 1;
	auto Dot = [&](const FOcrMark& M)
	{
		const double Fill = (double)M.Pixels.Num() / (M.W() * M.H());
		return M.H() <= 0.3 * Cap && M.W() <= 0.35 * Cap && M.W() <= 2.5 * M.H() && M.H() <= 2.5 * M.W() && Fill >= 0.5;
	};
	if (G.Marks.Num() == 1)
	{
		const FOcrMark& M = Marks[G.Marks[0]];
		const double Fill = (double)M.Pixels.Num() / (M.W() * M.H());
		if (Dot(M) && Bottom - M.Y1 <= 0.12 * Cap)
		{
			return TEXT('.');
		}
		const double Mid = (M.Y0 + M.Y1) / 2.0 - Top;
		if (M.H() <= 0.25 * Cap && M.W() >= 2 * M.H() && M.W() >= 0.25 * Cap && M.W() <= 0.9 * Cap && Fill >= 0.6 && Mid >= 0.3 * Cap &&
			Mid <= 0.7 * Cap)
		{
			return TEXT('-');
		}
	}
	if (G.Marks.Num() == 2)
	{
		const FOcrMark& A = Marks[G.Marks[0]].Y0 < Marks[G.Marks[1]].Y0 ? Marks[G.Marks[0]] : Marks[G.Marks[1]];
		const FOcrMark& B = &A == &Marks[G.Marks[0]] ? Marks[G.Marks[1]] : Marks[G.Marks[0]];
		if (Dot(A) && Dot(B) && B.Y0 > A.Y1 && Bottom - B.Y1 <= 0.12 * Cap && A.Y0 - Top >= 0.15 * Cap)
		{
			return TEXT(':');
		}
	}
	return 0;
}

/** Reads the text lines in an image (W x H): each line of glyphs read whole, or not at all. */
static void OcrRead(const TArray<FColor>& Px, int32 W, int32 H, TArray<FOcrLine>& Out)
{
	TArray<uint8> Mask;
	if (!OcrMarks(Px, W, H, Mask))
	{
		return;
	}
	// connected marks
	TArray<FOcrMark> All;
	TArray<int32> Label;
	Label.Init(INDEX_NONE, W * H);
	TArray<int32> Stack;
	for (int32 Start = 0; Start < W * H; ++Start)
	{
		if (Mask[Start] != 2 || Label[Start] != INDEX_NONE)
		{
			continue;
		}
		FOcrMark M;
		M.X0 = M.X1 = Start % W;
		M.Y0 = M.Y1 = Start / W;
		const int32 Id = All.Num();
		Stack.Reset();
		Stack.Add(Start);
		Label[Start] = Id;
		while (!Stack.IsEmpty())
		{
			const int32 p = Stack.Pop();
			M.Pixels.Add(p);
			const int32 x = p % W, y = p / W;
			M.X0 = FMath::Min(M.X0, x);
			M.X1 = FMath::Max(M.X1, x);
			M.Y0 = FMath::Min(M.Y0, y);
			M.Y1 = FMath::Max(M.Y1, y);
			for (int32 dy = -1; dy <= 1; ++dy)
			{
				for (int32 dx = -1; dx <= 1; ++dx)
				{
					const int32 nx = x + dx, ny = y + dy;
					if (nx < 0 || ny < 0 || nx >= W || ny >= H)
					{
						continue;
					}
					const int32 q = ny * W + nx;
					if (Mask[q] == 2 && Label[q] == INDEX_NONE)
					{
						Label[q] = Id;
						Stack.Add(q);
					}
				}
			}
		}
		M.bEdge = M.X0 == 0 || M.Y0 == 0 || M.X1 == W - 1 || M.Y1 == H - 1;
		All.Add(M);
	}
	// set aside: specks (two pixels or less), frames (a hollow mark around others a quarter to 0.7 of its height) and
	// rules (long marks a fifth of a glyph's height thin or less), and marks the edge cuts. Each refuses a line it
	// crosses, unless it is around the line or a speck inside one of its glyphs.
	TArray<int32> Kept, Aside;
	TArray<int32> Heights;
	for (const FOcrMark& M : All)
	{
		if (M.Pixels.Num() > 2 && M.W() < 4 * M.H())
		{
			Heights.Add(M.H());
		}
	}
	Heights.Sort([](int32 L, int32 R) { return L < R; });
	const int32 Typical = Heights.IsEmpty() ? 0 : Heights[Heights.Num() / 2];
	for (int32 i = 0; i < All.Num(); ++i)
	{
		const FOcrMark& M = All[i];
		bool bAside = M.Pixels.Num() <= 2 || M.bEdge;
		if (!bAside && Typical > 0 && M.W() >= 2.5 * Typical && M.H() <= FMath::Max(2.0, 0.2 * Typical))
		{
			bAside = true;  // a rule
		}
		if (!bAside)
		{
			int32 Inner = 0;
			for (int32 j = 0; j < All.Num(); ++j)
			{
				const FOcrMark& O = All[j];
				if (j != i && O.Pixels.Num() > 2 && O.X0 > M.X0 && O.X1 < M.X1 && O.Y0 > M.Y0 && O.Y1 < M.Y1)
				{
					Inner = FMath::Max(Inner, O.H());
				}
			}
			if (Inner >= 0.25 * M.H() && M.H() >= 1.4 * Inner)
			{
				const int32 Band = FMath::Max(2, FMath::RoundToInt(0.12 * FMath::Min(M.W(), M.H())));
				int32 Rim = 0;
				for (const int32 p : M.Pixels)
				{
					const int32 x = p % W, y = p / W;
					Rim += (x - M.X0 < Band || M.X1 - x < Band || y - M.Y0 < Band || M.Y1 - y < Band) ? 1 : 0;
				}
				bAside = Rim >= 0.95 * M.Pixels.Num();  // a frame
			}
		}
		(bAside ? Aside : Kept).Add(i);
	}
	// lines: marks that overlap in height by at least half the shorter one
	TArray<int32> Parent;
	for (int32 k = 0; k < Kept.Num(); ++k)
	{
		Parent.Add(k);
	}
	auto Root = [&](int32 k)
	{
		while (Parent[k] != k)
		{
			k = Parent[k] = Parent[Parent[k]];
		}
		return k;
	};
	for (int32 a = 0; a < Kept.Num(); ++a)
	{
		for (int32 b = a + 1; b < Kept.Num(); ++b)
		{
			const FOcrMark& A = All[Kept[a]];
			const FOcrMark& B = All[Kept[b]];
			const int32 Over = FMath::Min(A.Y1, B.Y1) - FMath::Max(A.Y0, B.Y0) + 1;
			if (Over >= 0.5 * FMath::Min(A.H(), B.H()))
			{
				Parent[Root(a)] = Root(b);
			}
		}
	}
	for (int32 r = 0; r < Kept.Num(); ++r)
	{
		if (Root(r) != r)
		{
			continue;
		}
		TArray<int32> Line;
		for (int32 k = 0; k < Kept.Num(); ++k)
		{
			if (Root(k) == r)
			{
				Line.Add(Kept[k]);
			}
		}
		Line.Sort([&](int32 L, int32 R) { return All[L].X0 < All[R].X0; });
		// glyphs: marks that overlap side to side by at least 0.4 of the narrower
		TArray<FOcrGlyph> Glyphs;
		for (const int32 i : Line)
		{
			const FOcrMark& M = All[i];
			if (!Glyphs.IsEmpty())
			{
				FOcrGlyph& G = Glyphs.Last();
				const int32 Over = FMath::Min(G.X1, M.X1) - FMath::Max(G.X0, M.X0) + 1;
				if (Over > 0 && Over >= 0.4 * FMath::Min(G.W(), M.W()))
				{
					G.X0 = FMath::Min(G.X0, M.X0);
					G.X1 = FMath::Max(G.X1, M.X1);
					G.Y0 = FMath::Min(G.Y0, M.Y0);
					G.Y1 = FMath::Max(G.Y1, M.Y1);
					G.Marks.Add(i);
					continue;
				}
			}
			FOcrGlyph G;
			G.X0 = M.X0;
			G.X1 = M.X1;
			G.Y0 = M.Y0;
			G.Y1 = M.Y1;
			G.Marks.Add(i);
			Glyphs.Add(G);
		}
		int32 Top = H, Bottom = -1, Cap = 0;
		for (const FOcrGlyph& G : Glyphs)
		{
			Cap = FMath::Max(Cap, G.H());
		}
		for (const FOcrGlyph& G : Glyphs)
		{
			if (G.H() >= 0.75 * Cap)
			{
				Top = FMath::Min(Top, G.Y0);
				Bottom = FMath::Max(Bottom, G.Y1);
			}
		}
		if (Cap < 7 || Bottom - Top + 1 > 1.25 * Cap)
		{
			continue;  // too small to read, or capitals not on one line
		}
		// a mark set aside that crosses the line: a cut glyph, a stroke through it, a speck between its glyphs
		bool bCrossed = false;
		for (const int32 i : Aside)
		{
			const FOcrMark& M = All[i];
			if (M.X0 <= Glyphs[0].X0 && M.X1 >= Glyphs.Last().X1 && M.Y0 <= Top && M.Y1 >= Bottom)
			{
				continue;  // around the line
			}
			if (M.Y1 < Top || M.Y0 > Bottom || M.X1 < Glyphs[0].X0 - Cap || M.X0 > Glyphs.Last().X1 + Cap)
			{
				continue;  // clear of it
			}
			bool bInGlyph = false;
			for (const FOcrGlyph& G : Glyphs)
			{
				bInGlyph = bInGlyph || (M.Pixels.Num() <= 2 && M.X0 >= G.X0 - 1 && M.X1 <= G.X1 + 1 && M.Y0 >= G.Y0 - 1 && M.Y1 <= G.Y1 + 1);
			}
			bCrossed = bCrossed || !bInGlyph;
		}
		if (bCrossed)
		{
			continue;
		}
		for (FOcrGlyph& G : Glyphs)
		{
			if (G.H() < 0.75 * Cap)
			{
				G.Char = OcrSmallChar(G, All, Top, Bottom);
			}
			else if (G.Y0 - Top <= 0.2 * Cap && Bottom - G.Y1 <= 0.2 * Cap && OcrGlyphScores(G, All, W))
			{
				G.Char = OcrGlyphDecide(G, Mask, W, H);
			}
		}
		// spaces: a gap of half a capital's height where glyphs stand further apart than the line's usual pitch; items:
		// glyphs two and a half capitals' heights apart are separate texts
		TArray<double> Pitch;
		for (int32 g = 1; g < Glyphs.Num(); ++g)
		{
			Pitch.Add((Glyphs[g].X0 + Glyphs[g].X1 - Glyphs[g - 1].X0 - Glyphs[g - 1].X1) / 2.0);
		}
		TArray<double> Sorted = Pitch;
		Sorted.Sort([](double L, double R) { return L < R; });
		const double Usual = Sorted.IsEmpty() ? 0.0 : Sorted[(Sorted.Num() - 1) / 2];
		int32 First = 0;
		for (int32 g = 1; g <= Glyphs.Num(); ++g)
		{
			const int32 Gap = g < Glyphs.Num() ? Glyphs[g].X0 - Glyphs[g - 1].X1 - 1 : 0;
			if (g < Glyphs.Num() && Gap < 2.5 * Cap)
			{
				continue;
			}
			// one item: glyphs First .. g-1
			FOcrLine L;
			L.X0 = W;
			L.Y0 = H;
			bool bAll = true;
			int32 Letters = 0;
			for (int32 k = First; k < g; ++k)
			{
				const FOcrGlyph& G = Glyphs[k];
				if (k > First)
				{
					const int32 Space = G.X0 - Glyphs[k - 1].X1 - 1;
					if (Space >= 0.9 * Cap || (Space >= 0.45 * Cap && Pitch[k - 1] >= 1.45 * Usual && Glyphs.Num() > 2))
					{
						L.Text.AppendChar(TEXT(' '));
					}
				}
				bAll = bAll && G.Char != 0;
				L.Text.AppendChar(G.Char ? G.Char : TEXT('?'));
				Letters += (G.Char >= TEXT('A') && G.Char <= TEXT('Z')) || (G.Char >= TEXT('0') && G.Char <= TEXT('9')) ? 1 : 0;
				L.X0 = FMath::Min(L.X0, G.X0);
				L.Y0 = FMath::Min(L.Y0, G.Y0);
				L.X1 = FMath::Max(L.X1, G.X1 + 1);
				L.Y1 = FMath::Max(L.Y1, G.Y1 + 1);
			}
			// two glyphs at least: a lone shape (a bar, a ring, a cross, an icon) is as likely a mark as a character
			if (bAll && Letters > 0 && g - First >= 2)
			{
				Out.Add(L);
			}
			First = g;
		}
	}
}

/** The frame as drawn, the UI included, for ui text in a rect (UiOcr): the game's window drawn again and read back the
 *  way the engine takes a screenshot with its UI (FSlateApplication::TakeScreenshot, from the same point of the
 *  frame), cut to the game viewport. False without a renderer or a window. */
static bool UiFrame(TArray<FColor>& Out, int32& OutW, int32& OutH)
{
	UGameViewportClient* GVC = GEngine ? GEngine->GameViewport.Get() : nullptr;
	const TSharedPtr<SWindow> Window = GVC ? GVC->GetWindow() : nullptr;
	FVector2D Pos, Size;
	if (!FApp::CanEverRender() || !FSlateApplication::IsInitialized() || !Window.IsValid() || !ViewportRect(Pos, Size))
	{
		return false;
	}
	TArray<FColor> Shot;
	FIntVector Got(0, 0, 0);
	if (!FSlateApplication::Get().TakeScreenshot(Window.ToSharedRef(), Shot, Got) || Got.X <= 0 || Got.Y <= 0 || Shot.Num() < Got.X * Got.Y)
	{
		return false;
	}
	// the viewport inside the window, as TakeScreenshot places a widget
	const FVector2D Off = Pos - FVector2D(Window->GetPositionInScreen());
	const int32 X0 = FMath::Clamp(FMath::RoundToInt(Off.X), 0, Got.X - 1), Y0 = FMath::Clamp(FMath::RoundToInt(Off.Y), 0, Got.Y - 1);
	OutW = FMath::Clamp(FMath::RoundToInt(Size.X), 1, Got.X - X0);
	OutH = FMath::Clamp(FMath::RoundToInt(Size.Y), 1, Got.Y - Y0);
	Out.SetNumUninitialized(OutW * OutH);
	for (int32 y = 0; y < OutH; ++y)
	{
		FMemory::Memcpy(Out.GetData() + y * OutW, Shot.GetData() + (int64)(Y0 + y) * Got.X + X0, OutW * sizeof(FColor));
	}
	return true;
}

/** ui text read from the frame as drawn inside a select rect (viewport fractions): the rect cut from the frame and read
 *  (OcrRead), each line a text element, "source" "ocr". A line where a text element already read stands (UMG, Slate,
 *  canvas) is left to that element, so nothing reads twice. */
static void UiOcr(const TArray<FColor>& Frame, int32 W, int32 H, const double Rect[4], const TArray<FUiElement>& Found, TArray<FUiElement>& Out)
{
	const int32 X0 = FMath::Clamp(FMath::FloorToInt(FMath::Min(Rect[0], Rect[2]) * W), 0, W - 1);
	const int32 Y0 = FMath::Clamp(FMath::FloorToInt(FMath::Min(Rect[1], Rect[3]) * H), 0, H - 1);
	const int32 X1 = FMath::Clamp(FMath::CeilToInt(FMath::Max(Rect[0], Rect[2]) * W), X0 + 1, W);
	const int32 Y1 = FMath::Clamp(FMath::CeilToInt(FMath::Max(Rect[1], Rect[3]) * H), Y0 + 1, H);
	const int32 Cw = X1 - X0, Ch = Y1 - Y0;
	TArray<FColor> Crop;
	Crop.SetNumUninitialized(Cw * Ch);
	for (int32 y = 0; y < Ch; ++y)
	{
		FMemory::Memcpy(Crop.GetData() + y * Cw, Frame.GetData() + (int64)(Y0 + y) * W + X0, Cw * sizeof(FColor));
	}
	TArray<FOcrLine> Lines;
	OcrRead(Crop, Cw, Ch, Lines);
	for (const FOcrLine& L : Lines)
	{
		FUiElement E;
		E.Source = TEXT("ocr");
		E.Kind = TEXT("text");
		E.Name = TEXT("ScreenText");
		E.Class = E.Name;
		E.Text = L.Text;
		E.bHasRect = true;
		E.X = (double)(X0 + L.X0) / W;
		E.Y = (double)(Y0 + L.Y0) / H;
		E.W = (double)(L.X1 - L.X0) / W;
		E.H = (double)(L.Y1 - L.Y0) / H;
		bool bRead = false;
		for (const FUiElement& T : Found)
		{
			bRead = bRead || (T.Kind == TEXT("text") && T.bHasRect && T.X < E.X + E.W && E.X < T.X + T.W && T.Y < E.Y + E.H && E.Y < T.Y + T.H);
		}
		if (!bRead)
		{
			Out.Add(E);
		}
	}
}
// ---------------------------------------------------------------- ui: what a widget paints itself

/** The widget types the Slate walk reads as elements (UiSlateElement): what they paint is theirs, so the paint reading
 *  leaves it to them. */
static bool WalkReads(const FName& Type)
{
	static const TSet<FName> Read = {TEXT("STextBlock"), TEXT("SRichTextBlock"), TEXT("SEditableText"), TEXT("SMultiLineEditableText"),
		TEXT("SImage"), TEXT("SBorder"), TEXT("SButton"), TEXT("SProgressBar"), TEXT("SColorBlock")};
	return Read.Contains(Type);
}

/** A draw element's rectangle in viewport fractions: the local box [Min, Max] through the element's render transform
 *  (window space), against the game viewport's paint rect; a line's box widened to a pixel. False when it lies off
 *  the viewport. */
static bool PaintRect(const FSlateDrawElement& El, const FVector2f& Min, const FVector2f& Max, const FVector2D& ViewPos, const FVector2D& ViewSize, FUiElement& E)
{
	if (ViewSize.X <= 0.0 || ViewSize.Y <= 0.0)
	{
		return false;
	}
	const FSlateRenderTransform& X = El.GetRenderTransform();
	FBox2D Box(ForceInit);
	for (const FVector2f& Corner : {Min, FVector2f(Max.X, Min.Y), FVector2f(Min.X, Max.Y), Max})
	{
		const FVector2f P = X.TransformPoint(Corner);
		Box += FVector2D(P.X, P.Y);
	}
	const FVector2D Size(FMath::Max(Box.Max.X - Box.Min.X, 1.0), FMath::Max(Box.Max.Y - Box.Min.Y, 1.0));
	E.X = (Box.Min.X - ViewPos.X) / ViewSize.X;
	E.Y = (Box.Min.Y - ViewPos.Y) / ViewSize.Y;
	E.W = Size.X / ViewSize.X;
	E.H = Size.Y / ViewSize.Y;
	E.bHasRect = true;
	return E.X + E.W > 0.0 && E.X < 1.0 && E.Y + E.H > 0.0 && E.Y < 1.0;
}

/** A texture a brush paints with that is a picture, not a solid fill (Slate fills with a small white square). */
static bool PaintsPicture(const FSlateBoxElement& Box)
{
	const FSlateShaderResourceProxy* Proxy = Box.GetResourceProxy();
	return Proxy && (Proxy->ActualSize.X > 16 || Proxy->ActualSize.Y > 16);
}

/** One painted draw element as a ui element (source "paint", named by the widget type that painted it): a string
 *  (text), a box or border (box, or image with a picture texture), a gradient (box), a line or spline (line). False for
 *  anything else (a viewport, custom drawing, shaped text, an element at alpha 0 or off the viewport). */
static bool PaintElement(const FSlateWindowElementList& List, const FPaintRecord& R, const FVector2D& ViewPos, const FVector2D& ViewSize, FUiElement& E)
{
	const FSlateDrawElementMap& Map = List.GetUncachedDrawElements();
	E.Source = TEXT("paint");
	E.Name = R.Widget.ToString();
	E.Class = E.Name;
	auto Boxed = [&](const FSlateBoxElement& Box)
	{
		if (Box.GetBrushDrawType() == ESlateBrushDrawType::NoDrawType || Box.GetTint().A <= UiAlphaFloor)
		{
			return false;
		}
		E.Kind = PaintsPicture(Box) ? TEXT("image") : TEXT("box");
		return PaintRect(Box, FVector2f::ZeroVector, Box.GetLocalSize(), ViewPos, ViewSize, E);
	};
	switch ((EElementType)R.Type)
	{
	case EElementType::ET_Text:
	{
		const auto& All = Map.Get<(uint8)EElementType::ET_Text>();
		if (!All.IsValidIndex(R.Index))
		{
			return false;
		}
		const FSlateTextElement& T = All[R.Index];
		E.Kind = TEXT("text");
		E.Text = T.GetText();
		if (E.Text.TrimStartAndEnd().IsEmpty() || T.GetTint().A <= UiAlphaFloor)
		{
			return false;
		}
		// the string's own extent from the font (the element holds the area it was given), within that area
		FVector2f Max = T.GetLocalSize();
		if (FSlateApplication::IsInitialized() && FSlateApplication::Get().GetRenderer())
		{
			const FVector2f Measured = FSlateApplication::Get().GetRenderer()->GetFontMeasureService()->Measure(FStringView(E.Text), T.GetFontInfo(), 1.0f);
			Max = FVector2f(Max.X > 0.f ? FMath::Min(Max.X, Measured.X) : Measured.X, Max.Y > 0.f ? FMath::Min(Max.Y, Measured.Y) : Measured.Y);
		}
		return PaintRect(T, FVector2f::ZeroVector, Max, ViewPos, ViewSize, E);
	}
	case EElementType::ET_Box:
	{
		const auto& All = Map.Get<(uint8)EElementType::ET_Box>();
		return All.IsValidIndex(R.Index) && Boxed(All[R.Index]);
	}
	case EElementType::ET_Border:
	{
		const auto& All = Map.Get<(uint8)EElementType::ET_Border>();
		return All.IsValidIndex(R.Index) && Boxed(All[R.Index]);
	}
	case EElementType::ET_RoundedBox:
	{
		const auto& All = Map.Get<(uint8)EElementType::ET_RoundedBox>();
		return All.IsValidIndex(R.Index) && Boxed(All[R.Index]);
	}
	case EElementType::ET_Gradient:
	{
		const auto& All = Map.Get<(uint8)EElementType::ET_Gradient>();
		if (!All.IsValidIndex(R.Index))
		{
			return false;
		}
		E.Kind = TEXT("box");
		return PaintRect(All[R.Index], FVector2f::ZeroVector, All[R.Index].GetLocalSize(), ViewPos, ViewSize, E);
	}
	case EElementType::ET_Line:
	{
		const auto& All = Map.Get<(uint8)EElementType::ET_Line>();
		if (!All.IsValidIndex(R.Index) || All[R.Index].GetPoints().Num() < 2 || All[R.Index].GetTint().A <= UiAlphaFloor)
		{
			return false;
		}
		const FSlateLineElement& L = All[R.Index];
		FVector2f Min(TNumericLimits<float>::Max()), Max(TNumericLimits<float>::Lowest());
		for (const FVector2f& P : L.GetPoints())
		{
			Min = FVector2f(FMath::Min(Min.X, P.X), FMath::Min(Min.Y, P.Y));
			Max = FVector2f(FMath::Max(Max.X, P.X), FMath::Max(Max.Y, P.Y));
		}
		E.Kind = TEXT("line");
		return PaintRect(L, Min, Max, ViewPos, ViewSize, E);
	}
	case EElementType::ET_Spline:
	{
		const auto& All = Map.Get<(uint8)EElementType::ET_Spline>();
		if (!All.IsValidIndex(R.Index))
		{
			return false;
		}
		E.Kind = TEXT("line");
		return PaintRect(All[R.Index], FVector2f::ZeroVector, All[R.Index].GetLocalSize(), ViewPos, ViewSize, E);
	}
	default:
		return false;
	}
}

// ---------------------------------------------------------------- drawn: what is drawn in a place, rendered

static constexpr int32 DrawnNearSize = 64;  // pixels square, each of the four views of a place near a point
static constexpr int32 DrawnLineSize = 128;  // pixels square, each of the two views of a line
static constexpr int32 DrawnLineBins = 128;  // the line's length read in at most this many steps (length), none finer than a pixel
static constexpr double DrawnBackground = 1.0e6;  // cm: a pixel this deep or deeper has nothing opaque drawn
static constexpr double DrawnEnclosing = 20.0;  // a primitive around the whole place and this many times its size is left out
static constexpr double DrawnStep = 1.0 / 255.0;  // motion: a pixel changed when its colour (c / (1 + c)) moved more
static constexpr double DrawnFaint = 1.0e-4;  // a translucent pixel with nothing opaque behind it counts above this luminance
static constexpr int32 DrawnPrimitiveCap = 1024;  // primitives one place renders at most

/** Show flags off in a drawn render: what is not the place's own drawing lit directly: global illumination,
 *  reflections, ambient occlusion, shadows, fog, the atmosphere and clouds, and what blurs, rescales or accumulates a
 *  frame over time. Direct lights, the sky light, emissive, unlit and translucent shading stay. */
static const TCHAR* const DrawnOffFlags[] = {
	TEXT("GlobalIllumination"), TEXT("LumenGlobalIllumination"), TEXT("LumenReflections"), TEXT("ReflectionEnvironment"),
	TEXT("ScreenSpaceReflections"), TEXT("AmbientOcclusion"), TEXT("ScreenSpaceAO"), TEXT("DistanceFieldAO"), TEXT("DynamicShadows"),
	TEXT("ContactShadows"), TEXT("CapsuleShadows"), TEXT("LightShafts"), TEXT("Atmosphere"), TEXT("Fog"), TEXT("VolumetricFog"),
	TEXT("Cloud"), TEXT("TemporalAA"), TEXT("AntiAliasing"), TEXT("MotionBlur"), TEXT("Bloom"), TEXT("EyeAdaptation"),
	TEXT("LocalExposure"), TEXT("DepthOfField")};

/** One orthographic view of a place: where the camera is, which way it looks, how wide it sees (cm, square). */
struct FDrawnView
{
	FVector Location = FVector::ZeroVector;
	FRotator Rotation = FRotator::ZeroRotator;
	double Width = 0.0;
};

/** Its materials' shaders are there to draw with: one still compiling is finished first (as FGlowRender's). */
static bool DrawnReady(const UPrimitiveComponent* P, const UWorld* World)
{
	TArray<UMaterialInterface*> Used;
	P->GetUsedMaterials(Used);
	for (UMaterialInterface* MI : Used)
	{
		if (!MI || !MI->IsCompiling())
		{
			continue;
		}
		if (FMaterialResource* Res = World->Scene ? MI->GetMaterialResource(World->Scene->GetShaderPlatform()) : nullptr)
		{
			Res->FinishCompilation();
		}
		if (MI->IsCompiling())
		{
			return false;
		}
	}
	return true;
}

/** Renders a set of primitives alone (a scene capture showing only them) from up to four orthographic views and reads
 *  the pixels back as linear colour: lit by direct lights and the sky light, without shadows, global illumination,
 *  reflections, fog or anything that accumulates over frames, at exposure 1. One per query set; its capture and render
 *  targets are transient objects registered with the world only while it renders. */
class FDrawnRender
{
public:
	bool Render(UWorld* World, const TArray<UPrimitiveComponent*>& Show, const TArray<FDrawnView>& Views, int32 Size, ESceneCaptureSource Source,
		TArray<TArray<FLinearColor>>& Out)
	{
		Out.Reset();
		if (!World || !World->Scene || !FApp::CanEverRender() || Views.Num() == 0 || Views.Num() > 4)
		{
			return false;
		}
		for (const UPrimitiveComponent* P : Show)
		{
			DrawnReady(P, World);
		}
		Setup();
		USceneCaptureComponent2D* C = Capture.Get();
		C->CaptureSource = Source;
		C->RegisterComponentWithWorld(World);
		for (const TCHAR* Name : DrawnOffFlags)
		{
			const int32 Index = FEngineShowFlags::FindIndexByName(Name);
			if (Index != INDEX_NONE)
			{
				C->ShowFlags.SetSingleFlag(Index, false);
			}
		}
		C->ShowOnlyComponents.Reset();
		for (UPrimitiveComponent* P : Show)
		{
			C->ShowOnlyComponents.Add(P);
		}
		for (int32 v = 0; v < Views.Num(); ++v)
		{
			C->OrthoWidth = (float)Views[v].Width;
			C->SetWorldLocationAndRotation(Views[v].Location, Views[v].Rotation);
			C->TextureTarget = Target(Size, v);
			C->CaptureScene();
		}
		bool bRead = true;
		for (int32 v = 0; v < Views.Num() && bRead; ++v)
		{
			FTextureRenderTargetResource* Res = Target(Size, v)->GameThread_GetRenderTargetResource();
			TArray<FLinearColor>& Pixels = Out.AddDefaulted_GetRef();
			bRead = Res && Res->ReadLinearColorPixels(Pixels) && Pixels.Num() >= Size * Size;
		}
		C->ShowOnlyComponents.Reset();
		C->TextureTarget = nullptr;
		C->UnregisterComponent();
		return bRead;
	}

private:
	void Setup()
	{
		if (Capture.IsValid())
		{
			return;
		}
		USceneCaptureComponent2D* C = NewObject<USceneCaptureComponent2D>(GetTransientPackage(), NAME_None, RF_Transient);
		C->bCaptureEveryFrame = false;
		C->bCaptureOnMovement = false;
		C->bAlwaysPersistRenderingState = false;
		C->PrimitiveRenderMode = ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
		C->ProjectionType = ECameraProjectionMode::Orthographic;
		C->bAutoCalculateOrthoPlanes = false;  // the view starts at the camera, so a pixel's depth is its distance from it
		C->PostProcessBlendWeight = 1.f;
		C->PostProcessSettings.bOverride_AutoExposureMethod = true;
		C->PostProcessSettings.AutoExposureMethod = AEM_Manual;
		C->PostProcessSettings.bOverride_AutoExposureBias = true;
		C->PostProcessSettings.AutoExposureBias = 0.f;
		C->PostProcessSettings.bOverride_AutoExposureApplyPhysicalCameraExposure = true;
		C->PostProcessSettings.AutoExposureApplyPhysicalCameraExposure = false;
		TArray<FEngineShowFlagsSetting> Settings;
		for (const TCHAR* Name : DrawnOffFlags)
		{
			FEngineShowFlagsSetting Setting;
			Setting.ShowFlagName = Name;
			Setting.Enabled = false;
			Settings.Add(Setting);
		}
		C->SetShowFlagSettings(Settings);
		Capture.Reset(C);
	}

	UTextureRenderTarget2D* Target(int32 Size, int32 Index)
	{
		TStrongObjectPtr<UTextureRenderTarget2D>& T = Targets.FindOrAdd(Size * 8 + Index);
		if (!T.IsValid())
		{
			UTextureRenderTarget2D* RT = NewObject<UTextureRenderTarget2D>(GetTransientPackage(), NAME_None, RF_Transient);
			RT->RenderTargetFormat = RTF_RGBA32f;
			RT->ClearColor = FLinearColor::Black;
			RT->bAutoGenerateMips = false;
			RT->InitAutoFormat(Size, Size);
			RT->UpdateResourceImmediate(true);
			T.Reset(RT);
		}
		return T.Get();
	}

	TStrongObjectPtr<USceneCaptureComponent2D> Capture;
	TMap<int32, TStrongObjectPtr<UTextureRenderTarget2D>> Targets;
};

/** The primitives drawn in game (visible, not hidden in game, the owner not hidden, with something to render) whose
 *  world bounds Touches says reach the place, but for one whose bounds enclose the whole place and are many times its
 *  size (a sky dome, a room seen from inside: only its far side would show). */
static void DrawnPrimitives(UWorld* World, const FBox& Place, TFunctionRef<bool(const FBox&)> Touches, TArray<UPrimitiveComponent*>& Out)
{
	const double PlaceSize = FMath::Max(Place.GetSize().GetMax(), 1.0);
	for (TObjectIterator<UPrimitiveComponent> It; It; ++It)
	{
		UPrimitiveComponent* P = *It;
		if (!IsValid(P) || P->HasAnyFlags(RF_ClassDefaultObject | RF_ArchetypeObject) || !P->IsRegistered() || P->GetWorld() != World ||
			P->IsEditorOnly() || !P->SceneProxy)
		{
			continue;
		}
		const AActor* Owner = P->GetOwner();
		if (!P->IsVisible() || P->bHiddenInGame || (Owner && Owner->IsHidden()))
		{
			continue;
		}
		const FBox B = P->Bounds.GetBox();
		if (!Touches(B) || (B.IsInside(Place) && B.GetSize().GetMin() >= DrawnEnclosing * PlaceSize))
		{
			continue;
		}
		Out.Add(P);
		if (Out.Num() >= DrawnPrimitiveCap)
		{
			break;
		}
	}
}

/** A view's camera axes (forward, right, up) and the world point of pixel (x, y) at depth D (cm) from it. */
struct FDrawnFrame
{
	FVector Origin, Forward, Right, Up;
	double Width = 0.0;
	int32 Size = 1;

	FDrawnFrame(const FDrawnView& V, int32 InSize)
		: Origin(V.Location), Width(V.Width), Size(InSize)
	{
		const FRotationMatrix M(V.Rotation);
		Forward = M.GetUnitAxis(EAxis::X);
		Right = M.GetUnitAxis(EAxis::Y);
		Up = M.GetUnitAxis(EAxis::Z);
	}
	/** The pixel's point on the camera plane. */
	FVector Plane(int32 X, int32 Y) const
	{
		const double U = ((X + 0.5) / Size - 0.5) * Width;
		const double V = (0.5 - (Y + 0.5) / Size) * Width;
		return Origin + Right * U + Up * V;
	}
};

static double Compressed(double C) { return C > 0.0 ? C / (1.0 + C) : 0.0; }

/** A sound that started during the play (audio's started fields): what it is, where it started (a sound with a place:
 *  its location defined, not a UI sound), the play time it was first seen at, and the first time it was loud enough at
 *  the listener to hear. */
struct FSoundStart
{
	FString Sound;
	bool bNamed = false;  // a saved asset, not a sound made at run time (a procedural wave): its name tells it apart
	TArray<FString> Classes;  // its sound class and the parents of it
	bool bPlaced = false;
	FVector Location = FVector::ZeroVector;
	double T = 0.0;
	double AudibleT = -1.0;  // -1: never yet
	double Peak = 0.0;  // its loudest at the listener so far
};

/** Every sound that starts in the play (FTaskProbeQueries::Listen), followed on the audio thread and read on the game
 *  thread after a fence, both under Lock. */
struct FSoundStarts
{
	struct FSeen
	{
		int32 Index = INDEX_NONE;  // its start in Starts; none: a sound that was playing already (not a start)
		float Playback = 0.f;  // its playback time when last seen (-1: the engine doesn't say)
		const USoundBase* Sound = nullptr;
		uint64 Component = 0;  // its audio component's id (0: none)
	};
	FCriticalSection Lock;
	TArray<FSoundStart> Starts;
	TMap<const FActiveSound*, FSeen> Live;  // the active sounds seen at the last look
	TSet<TPair<uint64, const USoundBase*>> Loops;  // a looping sound's component and sound, once seen
	bool bLooked = false;  // the first look is done: what played then started at the play's start
	bool bCapped = false;  // more than MaxSoundStarts started: the later ones aren't followed
};

// FActiveSound's members the started fields read, each only where this engine lets the plugin read it (a member that
// is private or gone reads as unknown, so the plugin still compiles into every game: 2026-11-11_game-grader-audio
// spec.md 3.6)
template <typename T>
static float PlaybackOf(const T& A)
{
	if constexpr (requires(const T& X) { X.PlaybackTime; })
	{
		return A.PlaybackTime;
	}
	else
	{
		return -1.f;
	}
}

template <typename T>
static uint64 ComponentOf(const T& A)
{
	if constexpr (requires(const T& X) { X.GetAudioComponentID(); })
	{
		return (uint64)A.GetAudioComponentID();
	}
	else
	{
		return 0;
	}
}

template <typename T>
static bool LoopsOf(const T* S)
{
	if constexpr (requires(const T* X) { (bool)X->IsLooping(); })
	{
		return S && S->IsLooping();
	}
	else
	{
		return false;
	}
}

/** Whether a sound has a place (its location defined, else spatialized; never a UI sound), and where; no place when the
 *  engine doesn't say. */
template <typename T>
static bool PlaceOf(const T& A, FVector& Out)
{
	bool bPlaced = false;
	if constexpr (requires(const T& X) { (bool)X.bLocationDefined; })
	{
		bPlaced = A.bLocationDefined;
	}
	else if constexpr (requires(const T& X) { (bool)X.bAllowSpatialization; })
	{
		bPlaced = A.bAllowSpatialization;
	}
	if constexpr (requires(const T& X) { (bool)X.bIsUISound; })
	{
		bPlaced = bPlaced && !A.bIsUISound;
	}
	if constexpr (requires(const T& X) { X.Transform.GetTranslation(); })
	{
		Out = A.Transform.GetTranslation();
		return bPlaced;
	}
	else
	{
		return false;
	}
}

/** An active sound's volume at the listener: its wave instances' volume (its own, its class's and mixes', the game's
 *  multipliers) times their distance and occlusion attenuation and dynamic volume, summed. The audio thread's. */
static double HeardVolume(const FActiveSound& Active)
{
	double Volume = 0.0;
	for (const TPair<UPTRINT, FWaveInstance*>& W : Active.GetWaveInstances())
	{
		if (W.Value)
		{
			Volume += W.Value->GetVolumeWithDistanceAndOcclusionAttenuation() * W.Value->GetDynamicVolume();
		}
	}
	return Volume;
}

/** A sound's sound class and its parents, by name. */
static TArray<FString> SoundClasses(const FActiveSound& Active)
{
	TArray<FString> Out;
	for (const USoundClass* K = Active.GetSoundClass(); K && Out.Num() < 16; K = K->ParentClass)
	{
		Out.Add(K->GetName());
	}
	return Out;
}
}  // namespace TaskProbe

using namespace TaskProbe;

/** Before the first rendered view: the named post-process properties blended here (the unbound and enclosing volumes by
 *  priority and weight, then the camera's own): overridden floats lerp by weight, other values switch at weight 0.5. */
static void BlendPost(UWorld* World, APlayerController* PC, const TArray<FString>& Names, FPostProcessSettings& Out)
{
	const UScriptStruct* Struct = FPostProcessSettings::StaticStruct();
	auto Apply = [&](const FPostProcessSettings& S, float W)
	{
		if (W <= 0.f)
		{
			return;
		}
		for (const FString& Name : Names)
		{
			const FProperty* P = FindFProperty<FProperty>(Struct, *Name);
			const FBoolProperty* Ov = FindFProperty<FBoolProperty>(Struct, *(TEXT("bOverride_") + Name));
			if (!P || !Ov || !Ov->GetPropertyValue_InContainer(&S))
			{
				continue;
			}
			const FNumericProperty* N = CastField<FNumericProperty>(P);
			if (N && N->IsFloatingPoint())
			{
				void* Dst = P->ContainerPtrToValuePtr<void>(&Out);
				const double A = N->GetFloatingPointPropertyValue(Dst);
				const double B = N->GetFloatingPointPropertyValue(P->ContainerPtrToValuePtr<void>(const_cast<FPostProcessSettings*>(&S)));
				N->SetFloatingPointPropertyValue(Dst, A + (B - A) * W);
			}
			else if (W >= 0.5f)
			{
				P->CopyCompleteValue_InContainer(&Out, &S);
			}
		}
	};
	for (IInterface_PostProcessVolume* Vol : World ? World->PostProcessVolumes : TArray<IInterface_PostProcessVolume*>())
	{
		const FPostProcessVolumeProperties Props = Vol ? Vol->GetProperties() : FPostProcessVolumeProperties();
		if (!Vol || !Props.bIsEnabled || !Props.Settings)
		{
			continue;
		}
		const APlayerCameraManager* View = PC ? PC->PlayerCameraManager.Get() : nullptr;
		float W = FMath::Clamp(Props.BlendWeight, 0.f, 1.f);
		if (!Props.bIsUnbound)
		{
			float Dist = 0.f;
			if (!View || !Vol->EncompassesPoint(View->GetCameraLocation(), Props.BlendRadius, &Dist) || Dist < 0.f)
			{
				continue;
			}
			if (Dist > 0.f && Props.BlendRadius >= 1.f)
			{
				W *= FMath::Clamp(1.f - Dist / Props.BlendRadius, 0.f, 1.f);
			}
		}
		Apply(*Props.Settings, W);
	}
	if (const APlayerCameraManager* View = PC ? PC->PlayerCameraManager.Get() : nullptr)
	{
		const FMinimalViewInfo& POV = View->GetCameraCacheView();
		Apply(POV.PostProcessSettings, POV.PostProcessBlendWeight);
	}
}

// ---------------------------------------------------------------- the player's view, as the renderer set it up

/** Sees every game view as the engine sets it up (after its post-process settings are final): the exposure the view's
 *  eye adaptation settled on (FSceneView::GetLastEyeAdaptationExposure, the view state's read-back exposure scale) and
 *  the final colour-grading settings (post-process volumes by priority and weight, the camera's own and its modifiers'). */
class FTaskProbeViewExtension : public FSceneViewExtensionBase
{
public:
	FTaskProbeViewExtension(const FAutoRegister& AutoRegister) : FSceneViewExtensionBase(AutoRegister) {}

	virtual void SetupView(FSceneViewFamily& InViewFamily, FSceneView& InView) override
	{
		if (InView.bIsSceneCapture || InView.bIsReflectionCapture || InView.bIsPlanarReflection || !InViewFamily.Scene)
		{
			return;
		}
		const UWorld* World = InViewFamily.Scene->GetWorld();
		if (!World || !World->IsGameWorld())
		{
			return;
		}
		bSeen = true;
		Exposure = InView.GetLastEyeAdaptationExposure();
		Grade.From(InView.FinalPostProcessSettings);
		if (bWantPost)
		{
			if (!Full.IsValid())
			{
				Full = MakeShared<FPostProcessSettings>();
			}
			*Full = InView.FinalPostProcessSettings;  // every property, for post:<name>
		}
	}

	bool bSeen = false;
	float Exposure = 0.f;
	FGrade Grade;
	bool bWantPost = false;
	TSharedPtr<FPostProcessSettings> Full;
};

// ---------------------------------------------------------------- FTaskProbeQueries

FTaskProbeQueries::FTaskProbeQueries()
	: GlowRender(MakeUnique<FGlowRender>())
{
	WorldInitHandle = FWorldDelegates::OnPostWorldInitialization.AddRaw(this, &FTaskProbeQueries::OnWorldInit);
}

FTaskProbeQueries::~FTaskProbeQueries()
{
	FWorldDelegates::OnPostWorldInitialization.Remove(WorldInitHandle);
	if (ViewportHandle.IsValid())
	{
		UGameViewportClient::OnViewportRendered().Remove(ViewportHandle);
	}
	if (HudHandle.IsValid())
	{
		AHUD::OnHUDPostRender.Remove(HudHandle);
	}
#if WITH_SLATE_DEBUGGING
	if (PaintHandles[0].IsValid())
	{
		FSlateDebugging::BeginWindow.Remove(PaintHandles[0]);
		FSlateDebugging::EndWindow.Remove(PaintHandles[1]);
		FSlateDebugging::BeginWidgetPaint.Remove(PaintHandles[2]);
		FSlateDebugging::EndWidgetPaint.Remove(PaintHandles[3]);
		FSlateDebugging::ElementTypeAdded.Remove(PaintHandles[4]);
	}
#endif
	Unhook();
	ViewExtension.Reset();
}

void FTaskProbeQueries::Load(const FString& Path)
{
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *Path))
	{
		ErrorList.Add(FString::Printf(TEXT("queries file not readable: %s"), *Path));
		return;
	}
	TSharedPtr<FJsonObject> Root;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
	{
		ErrorList.Add(TEXT("queries file is not a JSON object"));
		return;
	}
	FString Format;
	Root->TryGetStringField(TEXT("format"), Format);
	if (Format != TEXT("game-probe-queries/1"))
	{
		ErrorList.Add(FString::Printf(TEXT("queries format '%s' is not game-probe-queries/1"), *Format));
		return;
	}
	const TArray<TSharedPtr<FJsonValue>>* List = nullptr;
	if (!Root->TryGetArrayField(TEXT("queries"), List))
	{
		ErrorList.Add(TEXT("queries file has no queries array"));
		return;
	}
	static const TSet<FString> Kinds = {TEXT("actors"), TEXT("widgets"), TEXT("light"), TEXT("grading"), TEXT("spawns"), TEXT("camera"), TEXT("components"),
		TEXT("pieces"), TEXT("screen"), TEXT("audio"), TEXT("ground"), TEXT("ui"), TEXT("drawn"), TEXT("world")};
	TSet<FString> Ids;
	for (const TSharedPtr<FJsonValue>& Item : *List)
	{
		const TSharedPtr<FJsonObject>* Obj = nullptr;
		if (!Item.IsValid() || !Item->TryGetObject(Obj) || !Obj->IsValid())
		{
			ErrorList.Add(TEXT("a query is not an object"));
			continue;
		}
		FQuery Q;
		Q.Def = *Obj;
		if (!Q.Def->TryGetStringField(TEXT("id"), Q.Id) || Q.Id.IsEmpty() || Ids.Contains(Q.Id))
		{
			ErrorList.Add(FString::Printf(TEXT("a query has a missing or repeated id '%s'"), *Q.Id));
			continue;
		}
		if (Queries.Num() >= MaxQueries)
		{
			ErrorList.Add(FString::Printf(TEXT("more than %d queries: '%s' and later ones dropped"), MaxQueries, *Q.Id));
			break;
		}
		Q.Def->TryGetStringField(TEXT("kind"), Q.Kind);
		if (!Kinds.Contains(Q.Kind))
		{
			ErrorList.Add(FString::Printf(TEXT("query '%s': unknown kind '%s' (null values)"), *Q.Id, *Q.Kind));
		}
		const TArray<TSharedPtr<FJsonValue>>* Fields = nullptr;
		if (Q.Def->TryGetArrayField(TEXT("fields"), Fields))
		{
			for (const TSharedPtr<FJsonValue>& F : *Fields)
			{
				FString Name;
				if (F.IsValid() && F->TryGetString(Name) && !Name.IsEmpty())
				{
					Q.Fields.AddUnique(Name);
				}
			}
		}
		if (Q.Fields.Num() == 0 && (Q.Kind == TEXT("actors") || Q.Kind == TEXT("widgets") || Q.Kind == TEXT("components") || Q.Kind == TEXT("ui")))
		{
			Q.Fields.Add(TEXT("count"));
		}
		bHasWorld = bHasWorld || Q.Kind == TEXT("world");
		if (Q.Kind == TEXT("spawns"))
		{
			Q.Def->TryGetStringField(TEXT("class"), Q.SpawnClass);
			bHasSpawns = true;
		}
		if (Q.Kind == TEXT("audio") && !SoundStarts.IsValid())
		{
			SoundStarts = MakeShared<FSoundStarts, ESPMode::ThreadSafe>();
		}
		if (Q.Kind == TEXT("screen"))
		{
			// rect: [x0, y0, x1, y1] in viewport fractions (default the whole frame)
			const TArray<TSharedPtr<FJsonValue>>* Rect = nullptr;
			if (Q.Def->TryGetArrayField(TEXT("rect"), Rect) && Rect->Num() == 4)
			{
				for (int32 i = 0; i < 4; ++i)
				{
					double V = 0.0;
					if ((*Rect)[i].IsValid() && (*Rect)[i]->TryGetNumber(V))
					{
						Q.Rect[i] = FMath::Clamp(V, 0.0, 1.0);
					}
				}
			}
			if (!ViewportHandle.IsValid())
			{
				ViewportHandle = UGameViewportClient::OnViewportRendered().AddRaw(this, &FTaskProbeQueries::OnViewportRendered);
			}
		}
		if (Q.Kind == TEXT("ui"))
		{
			// a select of text in a rect also reads the frame as drawn (UiOcr); only such a query pays for the capture.
			// The select alone decides, so every measure on it counts and reads the same elements.
			const TSharedPtr<FJsonObject>* UiSel = nullptr;
			const TArray<TSharedPtr<FJsonValue>>* UiRect = nullptr;
			FString UiKind, UiText;
			if (Q.Def->TryGetObjectField(TEXT("select"), UiSel) && UiSel->IsValid() && (*UiSel)->TryGetArrayField(TEXT("rect"), UiRect) && UiRect->Num() == 4)
			{
				(*UiSel)->TryGetStringField(TEXT("kind"), UiKind);
				(*UiSel)->TryGetStringField(TEXT("text"), UiText);
				Q.bOcr = UiKind == TEXT("text") || (UiKind.IsEmpty() && !UiText.IsEmpty());
			}
			// filled in from the next frame the viewport draws: what the HUD canvas held, the Slate tree then
			if (!ViewportHandle.IsValid())
			{
				ViewportHandle = UGameViewportClient::OnViewportRendered().AddRaw(this, &FTaskProbeQueries::OnViewportRendered);
			}
			if (!HudHandle.IsValid())
			{
				HudHandle = AHUD::OnHUDPostRender.AddRaw(this, &FTaskProbeQueries::OnHudPostRender);
			}
#if WITH_SLATE_DEBUGGING
			// what widgets paint themselves: the game window's draw elements as each paint makes them
			if (!PaintHandles[0].IsValid())
			{
				PaintHandles[0] = FSlateDebugging::BeginWindow.AddRaw(this, &FTaskProbeQueries::OnPaintBeginWindow);
				PaintHandles[1] = FSlateDebugging::EndWindow.AddRaw(this, &FTaskProbeQueries::OnPaintEndWindow);
				PaintHandles[2] = FSlateDebugging::BeginWidgetPaint.AddRaw(this, &FTaskProbeQueries::OnPaintBeginWidget);
				PaintHandles[3] = FSlateDebugging::EndWidgetPaint.AddRaw(this, &FTaskProbeQueries::OnPaintEndWidget);
				PaintHandles[4] = FSlateDebugging::ElementTypeAdded.AddRaw(this, &FTaskProbeQueries::OnPaintElement);
			}
#endif
		}
		if (Q.Kind == TEXT("ground"))
		{
			// xy: [x, y] (one point), or box: [x0, y0, x1, y1] sampled on a grid of grid x grid points (2-32, default 8)
			const TArray<TSharedPtr<FJsonValue>>* Xy = nullptr;
			const TArray<TSharedPtr<FJsonValue>>* Box = nullptr;
			double V[4] = {0.0, 0.0, 0.0, 0.0};
			auto Numbers = [&V](const TArray<TSharedPtr<FJsonValue>>& A)
			{
				for (int32 i = 0; i < A.Num(); ++i)
				{
					if (!A[i].IsValid() || !A[i]->TryGetNumber(V[i]))
					{
						return false;
					}
				}
				return true;
			};
			if (Q.Def->TryGetArrayField(TEXT("box"), Box) && Box->Num() == 4 && Numbers(*Box))
			{
				Q.bGroundBox = true;
				Q.Ground[0] = FMath::Min(V[0], V[2]);
				Q.Ground[1] = FMath::Min(V[1], V[3]);
				Q.Ground[2] = FMath::Max(V[0], V[2]);
				Q.Ground[3] = FMath::Max(V[1], V[3]);
				double Grid = 8.0;
				Q.Def->TryGetNumberField(TEXT("grid"), Grid);
				Q.Grid = FMath::Clamp(FMath::RoundToInt(Grid), 2, 32);
			}
			else if (Q.Def->TryGetArrayField(TEXT("xy"), Xy) && Xy->Num() == 2 && Numbers(*Xy))
			{
				Q.Ground[0] = Q.Ground[2] = V[0];
				Q.Ground[1] = Q.Ground[3] = V[1];
			}
			else
			{
				ErrorList.Add(FString::Printf(TEXT("query '%s': a ground query takes xy [x, y] or box [x0, y0, x1, y1] (null values)"), *Q.Id));
				Q.Grid = 0;  // nothing to trace
			}
		}
		if ((Q.Kind == TEXT("light") || Q.Kind == TEXT("grading")) && !ViewExtension.IsValid())
		{
			ViewExtension = FSceneViewExtensions::NewExtension<FTaskProbeViewExtension>();
		}
		if (Q.Kind == TEXT("grading") && Q.Fields.ContainsByPredicate([](const FString& F) { return F.StartsWith(TEXT("post:")); }))
		{
			ViewExtension->bWantPost = true;
		}
		Ids.Add(Q.Id);
		Queries.Add(MoveTemp(Q));
	}
}

void FTaskProbeQueries::OnWorldInit(UWorld* World, const UWorld::InitializationValues IVS)
{
	if (bHasSpawns && World && World->IsGameWorld())
	{
		Hook(World);
	}
}

void FTaskProbeQueries::Hook(UWorld* World)
{
	if (!bHasSpawns || !World || HookedWorld.Get() == World)
	{
		return;
	}
	Unhook();
	HookedWorld = World;
	SpawnHandle = World->AddOnActorSpawnedHandler(FOnActorSpawned::FDelegate::CreateRaw(this, &FTaskProbeQueries::OnSpawned));
	DestroyHandle = World->AddOnActorDestroyedHandler(FOnActorDestroyed::FDelegate::CreateRaw(this, &FTaskProbeQueries::OnDestroyed));
}

void FTaskProbeQueries::Unhook()
{
	if (UWorld* World = HookedWorld.Get())
	{
		World->RemoveOnActorSpawnedHandler(SpawnHandle);
		World->RemoveOnActorDestroyedHandler(DestroyHandle);
	}
	HookedWorld.Reset();
	SpawnHandle.Reset();
	DestroyHandle.Reset();
}

void FTaskProbeQueries::OnSpawned(AActor* Actor)
{
	if (!Actor)
	{
		return;
	}
	for (FQuery& Q : Queries)
	{
		if (Q.Kind == TEXT("spawns") && ClassMatches(Actor->GetClass(), Q.SpawnClass))
		{
			++Q.Spawned;
		}
	}
}

void FTaskProbeQueries::OnDestroyed(AActor* Actor)
{
	if (!Actor)
	{
		return;
	}
	for (FQuery& Q : Queries)
	{
		if (Q.Kind == TEXT("spawns") && ClassMatches(Actor->GetClass(), Q.SpawnClass))
		{
			++Q.Destroyed;
		}
	}
}

void FTaskProbeQueries::Sample(UWorld* World, APlayerController* PC, double T)
{
	Hook(World);
	GlowRender->NewSample();
	TGuardValue<TaskProbe::FGlowRender*> SelectScope(TaskProbe::SelectRender, GlowRender.Get());  // has: lit
	for (FQuery& Q : Queries)
	{
		const TSharedRef<FJsonObject> S = MakeShared<FJsonObject>();
		S->SetNumberField(TEXT("t"), T);
		if (Q.Kind == TEXT("actors"))
		{
			SampleActors(Q, World, PC, *S);
		}
		else if (Q.Kind == TEXT("widgets"))
		{
			SampleWidgets(Q, World, *S);
		}
		else if (Q.Kind == TEXT("light"))
		{
			SampleLight(Q, World, PC, *S);
		}
		else if (Q.Kind == TEXT("grading"))
		{
			SampleGrading(Q, World, PC, *S);
		}
		else if (Q.Kind == TEXT("components"))
		{
			SampleComponents(Q, World, PC, T, *S);
		}
		else if (Q.Kind == TEXT("camera"))
		{
			SampleCamera(World, PC, *S);
		}
		else if (Q.Kind == TEXT("pieces"))
		{
			SamplePieces(Q, World, PC, *S);
		}
		else if (Q.Kind == TEXT("audio"))
		{
			SampleAudio(Q, World, PC, T, *S);
		}
		else if (Q.Kind == TEXT("ground"))
		{
			SampleGround(Q, World, PC, *S);
		}
		else if (Q.Kind == TEXT("screen"))
		{
			// filled in from the next frame the viewport draws (OnViewportRendered); null if none comes
			S->SetField(TEXT("value"), Null());
			Q.Pending.Add(S);
			bWantFrame = true;
		}
		else if (Q.Kind == TEXT("ui"))
		{
			// filled in from the next frame the viewport draws (FillUi); no rows if none comes
			Q.Pending.Add(S);
			bWantUi = true;
		}
		else if (Q.Kind == TEXT("drawn"))
		{
			SampleDrawn(Q, World, PC, *S);
		}
		else if (Q.Kind == TEXT("world"))
		{
			SampleWorld(*S);
		}
		else if (Q.Kind == TEXT("spawns"))
		{
			const TSharedRef<FJsonObject> V = MakeShared<FJsonObject>();
			V->SetNumberField(TEXT("spawned"), Q.Spawned);
			V->SetNumberField(TEXT("destroyed"), Q.Destroyed);
			S->SetObjectField(TEXT("value"), V);
		}
		else
		{
			S->SetField(TEXT("value"), Null());
		}
		Q.Samples.Add(MakeShared<FJsonValueObject>(S));
	}
	// world: the lowest time dilation and any pause are noted afresh from this sample on
	MinDilation = -1.0;
	bPausedSince = false;
	// frozen: the actors read this sample are followed frame by frame until the next one, and only those; a stillness
	// under way goes on into the next interval
	for (auto It = Stills.CreateIterator(); It; ++It)
	{
		if (!StillRead.Contains(It.Key()))
		{
			It.RemoveCurrent();
			continue;
		}
		It.Value().Longest = 0.0;  // a stop still under way is told in the interval it ends in
		It.Value().Time = 0.0;
	}
	for (const FObjectKey& Key : StillRead)
	{
		if (!Stills.Contains(Key))
		{
			if (const AActor* A = Cast<AActor>(Key.ResolveObjectPtr()))
			{
				Stills.Add(Key).Actor = A;
			}
		}
	}
	StillRead.Reset();
	// spin: the components read this sample are followed frame by frame until the next one, and only those
	for (auto It = Spins.CreateIterator(); It; ++It)
	{
		if (!SpinRead.Contains(It.Key()))
		{
			It.RemoveCurrent();
			continue;
		}
		It.Value().Angle = 0.0;
		It.Value().Time = 0.0;
	}
	for (const FObjectKey& Key : SpinRead)
	{
		if (!Spins.Contains(Key))
		{
			if (const USceneComponent* C = Cast<USceneComponent>(Key.ResolveObjectPtr()))
			{
				FSpinTrack& Track = Spins.Add(Key);
				Track.Component = C;
				Track.Last = C->GetComponentQuat();
			}
		}
	}
	SpinRead.Reset();
}

TSharedRef<FJsonObject> FTaskProbeQueries::MeasuresJson() const
{
	const TSharedRef<FJsonObject> Out = MakeShared<FJsonObject>();
	for (const FQuery& Q : Queries)
	{
		Out->SetArrayField(Q.Id, Q.Samples);
	}
	return Out;
}

void FTaskProbeQueries::SampleActors(FQuery& Q, UWorld* World, APlayerController* PC, FJsonObject& Out)
{
	const TSharedPtr<FJsonObject>* SelObj = nullptr;
	Q.Def->TryGetObjectField(TEXT("select"), SelObj);
	TArray<AActor*> Found;
	int32 Total = 0;
	FindActors(World, PC, ParseSel(SelObj ? *SelObj : TSharedPtr<FJsonObject>()), 0, MAX_int32, Found, Total);
	// every match is read; rows hold the first MaxRows, and "full" sums up all of them when there are more
	const bool bFull = Found.Num() > MaxRows;
	TMap<FString, FFull> Full;
	TArray<TSharedPtr<FJsonValue>> Rows;
	for (int32 i = 0; i < Found.Num(); ++i)
	{
		AActor* A = Found[i];
		const TSharedRef<FJsonObject> Row = MakeShared<FJsonObject>();
		// changed, bounds_change, pose_change: against the first sample this query saw the actor in
		const FChangeReading Change = Q.Fields.ContainsByPredicate(IsChangeField) ? ActorChange(A, Q.Firsts, Q.FirstParts) : FChangeReading();
		// lit, glow: over its lights and meshes
		const bool bGlow = Q.Fields.ContainsByPredicate(IsGlowField);
		const FGlowReading Glow = bGlow ? ActorGlow(A, World, GlowRender.Get()) : FGlowReading();
		for (const FString& F : Q.Fields)
		{
			const TSharedPtr<FJsonValue> V = IsChangeField(F) ? ChangeField(Change, F) : IsGlowField(F) ? GlowField(Glow, F)
				: F == TEXT("spin") ? ActorSpin(A) : F == TEXT("frozen") ? ActorStill(A) : F == TEXT("focus_player") ? FocusField(A, PC) : ActorField(A, F);
			if (bFull)
			{
				Full.FindOrAdd(F).Add(V);
			}
			if (i < MaxRows)
			{
				Row->SetField(F, V);
			}
		}
		if (i < MaxRows)
		{
			Row->SetStringField(TEXT("name"), A->GetName());
			Row->SetStringField(TEXT("class"), A->GetClass()->GetName());
			if (bGlow && Glow.bRead)
			{
				Row->SetStringField(TEXT("glow_sources"), GlowSources(Glow));  // for logs, never a threshold
				if (Glow.Reads)
				{
					Row->SetStringField(TEXT("glow_read"), GlowReads(Glow));  // for logs, never a threshold
				}
			}
			Rows.Add(MakeShared<FJsonValueObject>(Row));
		}
	}
	Out.SetArrayField(TEXT("rows"), Rows);
	SetTotal(Out, Total, Rows.Num(), Q.Fields, Full);
}

void FTaskProbeQueries::SampleWidgets(FQuery& Q, UWorld* World, FJsonObject& Out)
{
	FString Class, Name, Slate, TextRegex;
	bool bOnScreen = false;  // select.visible: only the widgets drawn (the visible field's test), never a collapsed or hidden one
	const TSharedPtr<FJsonObject>* SelObj = nullptr;
	if (Q.Def->TryGetObjectField(TEXT("select"), SelObj) && SelObj->IsValid())
	{
		(*SelObj)->TryGetStringField(TEXT("class"), Class);
		(*SelObj)->TryGetStringField(TEXT("name"), Name);
		(*SelObj)->TryGetStringField(TEXT("slate"), Slate);
		(*SelObj)->TryGetStringField(TEXT("text"), TextRegex);
		(*SelObj)->TryGetBoolField(TEXT("visible"), bOnScreen);
	}
	TArray<TSharedPtr<FJsonValue>> Rows;
	int32 Total = 0;
	TMap<FString, FFull> Full;  // every match's values, when more matched than the rows hold
	if (!Slate.IsEmpty())
	{
		// Slate widgets under the game viewport, by type name (STextBlock, SImage, a game's own S... type), optionally
		// with their text matching a regex
		const UGameViewportClient* GVC = World && GEngine ? GEngine->GameViewport.Get() : nullptr;
		const TSharedPtr<SViewport> Root = GVC ? GVC->GetGameViewportWidget() : nullptr;
		TArray<TSharedRef<SWidget>> Found;
		if (Root.IsValid())
		{
			const TOptional<FRegexPattern> Pattern = TextRegex.IsEmpty() ? TOptional<FRegexPattern>() : TOptional<FRegexPattern>(FRegexPattern(TextRegex));
			WalkSlate(Root.ToSharedRef(), [&](const TSharedRef<SWidget>& W)
			{
				if (!W->GetTypeAsString().MatchesWildcard(Slate))
				{
					return;
				}
				if (Pattern.IsSet())
				{
					if (W->GetType() != TEXT("STextBlock"))
					{
						return;
					}
					FRegexMatcher Matcher(Pattern.GetValue(), StaticCastSharedRef<STextBlock>(W)->GetText().ToString());
					if (!Matcher.FindNext())
					{
						return;
					}
				}
				if (bOnScreen && !SlateVisible(W))
				{
					return;
				}
				++Total;
				Found.Add(W);
			});
		}
		for (int32 i = 0; i < Found.Num(); ++i)
		{
			const TSharedRef<SWidget>& W = Found[i];
			const TSharedRef<FJsonObject> Row = MakeShared<FJsonObject>();
			for (const FString& F : Q.Fields)
			{
				const TSharedPtr<FJsonValue> V = SlateField(W, F);
				if (Found.Num() > MaxRows)
				{
					Full.FindOrAdd(F).Add(V);
				}
				Row->SetField(F, V);
			}
			if (i < MaxRows)
			{
				const FName Tag = W->GetTag();
				Row->SetStringField(TEXT("name"), Tag.IsNone() ? W->GetTypeAsString() : Tag.ToString());
				Row->SetStringField(TEXT("class"), W->GetTypeAsString());
				Rows.Add(MakeShared<FJsonValueObject>(Row));
			}
		}
	}
	else
	{
		TArray<UUserWidget*> Tops;
		ViewportWidgets(World, Tops);
		// class alone: the widget's own class; class with name: the widget's class or an enclosing user widget's
		const bool bWithOwners = !Name.IsEmpty();
		TArray<UWidget*> Found;
		auto Visit = [&](UWidget* W)
		{
			if (!W || (!Class.IsEmpty() && !WidgetClassMatches(W, Class, bWithOwners)) || (!Name.IsEmpty() && !W->GetName().MatchesWildcard(Name)) ||
				(bOnScreen && !WidgetVisible(W)))
			{
				return;
			}
			++Total;
			Found.AddUnique(W);
		};
		for (UUserWidget* Top : Tops)
		{
			ForEachWidgetDeep(Top, Visit);
		}
		for (int32 i = 0; i < Found.Num(); ++i)
		{
			UWidget* W = Found[i];
			const TSharedRef<FJsonObject> Row = MakeShared<FJsonObject>();
			for (const FString& F : Q.Fields)
			{
				const TSharedPtr<FJsonValue> V = WidgetField(W, F);
				if (Found.Num() > MaxRows)
				{
					Full.FindOrAdd(F).Add(V);
				}
				Row->SetField(F, V);
			}
			if (i < MaxRows)
			{
				Row->SetStringField(TEXT("name"), W->GetName());
				Row->SetStringField(TEXT("class"), W->GetClass()->GetName());
				Rows.Add(MakeShared<FJsonValueObject>(Row));
			}
		}
	}
	Out.SetArrayField(TEXT("rows"), Rows);
	SetTotal(Out, Total, Rows.Num(), Q.Fields, Full);
}

void FTaskProbeQueries::SampleComponents(FQuery& Q, UWorld* World, APlayerController* PC, double T, FJsonObject& Out)
{
	TArray<TSharedPtr<FJsonValue>> Rows;
	TArray<UActorComponent*> Matched;
	int32 Total = 0;
	const TSharedPtr<FJsonObject>* SelObj = nullptr;
	Q.Def->TryGetObjectField(TEXT("select"), SelObj);
	const FSel Sel = ParseSel(SelObj ? *SelObj : TSharedPtr<FJsonObject>());
	// mesh: a wildcard on a mesh component's mesh asset; visible: only components drawn (as the visible field reads them);
	// effect: only live effects (LiveEffect: an active particle system, a drawn decal)
	FString MeshSel;
	bool bDrawnOnly = false;
	bool bEffect = false;
	if (SelObj && SelObj->IsValid())
	{
		(*SelObj)->TryGetStringField(TEXT("mesh"), MeshSel);
		(*SelObj)->TryGetBoolField(TEXT("visible"), bDrawnOnly);
		(*SelObj)->TryGetBoolField(TEXT("effect"), bEffect);
	}
	bool bOk = World != nullptr;
	// owner: an actor selection the component's owner must be in
	TSet<const AActor*> Owners;
	const TSharedPtr<FJsonObject>* OwnerObj = nullptr;
	const bool bOwner = SelObj && SelObj->IsValid() && (*SelObj)->TryGetObjectField(TEXT("owner"), OwnerObj);
	if (bOk && bOwner)
	{
		TArray<AActor*> Found;
		int32 OwnerTotal = 0;
		FindActors(World, PC, ParseSel(*OwnerObj), 0, MAX_int32, Found, OwnerTotal);
		Owners.Append(Found);
	}
	FVector NearP = FVector::ZeroVector;
	if (bOk && Sel.Near.IsSet() && !ResolvePoint(Sel.Near.Point, World, PC, 1, NearP))
	{
		bOk = false;
	}
	if (bOk)
	{
		TMap<const UClass*, bool> ClassCache;  // most components share a few classes
		for (TObjectIterator<UActorComponent> It; It; ++It)
		{
			UActorComponent* C = *It;
			if (!IsValid(C) || C->HasAnyFlags(RF_ClassDefaultObject | RF_ArchetypeObject) || !C->IsRegistered() || C->GetWorld() != World)
			{
				continue;
			}
			const UClass* K = C->GetClass();
			const bool* Cached = ClassCache.Find(K);
			const bool bClass = Cached ? *Cached : ClassCache.Add(K, ClassMatches(K, Sel.Class));
			if (!bClass || (!Sel.Name.IsEmpty() && !C->GetName().MatchesWildcard(Sel.Name)) || (bOwner && !Owners.Contains(C->GetOwner())))
			{
				continue;
			}
			const USceneComponent* SC = Cast<USceneComponent>(C);
			if (Sel.Near.IsSet() && (!SC || !Sel.Near.Holds(NearP, SC->GetComponentLocation())))
			{
				continue;
			}
			if (!MeshSel.IsEmpty())
			{
				const UMeshComponent* M = Cast<UMeshComponent>(C);
				if (!M || !MeshAssetName(M).MatchesWildcard(MeshSel))
				{
					continue;
				}
			}
			if (bDrawnOnly)
			{
				const AActor* Owner = C->GetOwner();
				if (!SC || !SC->IsVisible() || SC->bHiddenInGame || (Owner && Owner->IsHidden()))
				{
					continue;
				}
			}
			if (bEffect && !LiveEffect(C))
			{
				continue;
			}
			++Total;
			Matched.Add(C);
		}
	}
	// speed: where each matched component was at this query's previous sample
	const bool bSpeed = Q.Fields.Contains(TEXT("speed"));
	TMap<FObjectKey, FVector> Places;
	// every match is read; rows hold the first MaxRows, and "full" sums up all of them when there are more
	TMap<FString, FFull> Full;
	for (int32 i = 0; i < Matched.Num(); ++i)
	{
		UActorComponent* C = Matched[i];
		const USceneComponent* SC = Cast<USceneComponent>(C);
		UPrimitiveComponent* Prim = Cast<UPrimitiveComponent>(C);
		const ULightComponentBase* Light = Cast<ULightComponentBase>(C);
		if (bSpeed && SC)
		{
			Places.Add(FObjectKey(C), SC->GetComponentLocation());
		}
		// changed, bounds_change, pose_change: a primitive against the first sample this query saw it in
		FChangeReading Change;
		if (Prim && Q.Fields.ContainsByPredicate(IsChangeField))
		{
			const FObjectKey Key(C);
			const FPartState Now = PartState(Prim);
			if (const FPartState* First = Q.Firsts.Find(Key))
			{
				Change = PartChange(*First, Now);
			}
			else
			{
				Change.bAny = true;
				Change.bPose = Now.bSkinned;
				Q.Firsts.Add(Key, Now);
			}
		}
		// lit, glow: a light component or a mesh component as a source; null for any other component
		const bool bGlow = Q.Fields.ContainsByPredicate(IsGlowField);
		FGlowReading Glow;
		if (bGlow && Light)
		{
			AddLight(Glow, Light, World);
		}
		else if (const UMeshComponent* Mesh = bGlow ? Cast<UMeshComponent>(C) : nullptr)
		{
			AddMesh(Glow, Mesh, World, GlowRender.Get());
		}
		else if (const UFXSystemComponent* FX = bGlow ? Cast<UFXSystemComponent>(C) : nullptr)
		{
			AddEffect(Glow, FX, World, GlowRender.Get());
		}
		const TSharedRef<FJsonObject> Row = MakeShared<FJsonObject>();
		for (const FString& F : Q.Fields)
		{
			TSharedPtr<FJsonValue> V = Null();
			if (F == TEXT("count"))
			{
				V = Num(1.0);
			}
			else if (F == TEXT("active"))
			{
				V = Num(C->IsActive() ? 1.0 : 0.0);
			}
			else if (F == TEXT("visible"))
			{
				// visible and not hidden in game, nor its owner
				const AActor* Owner = C->GetOwner();
				V = SC ? Num(SC->IsVisible() && !SC->bHiddenInGame && !(Owner && Owner->IsHidden()) ? 1.0 : 0.0) : Null();
			}
			else if (SC && (F == TEXT("x") || F == TEXT("y") || F == TEXT("z")))
			{
				const FVector L = SC->GetComponentLocation();
				V = Num(F == TEXT("x") ? L.X : F == TEXT("y") ? L.Y : L.Z);
			}
			else if (SC && F == TEXT("speed"))
			{
				// cm/s: its physics body's speed while it simulates, else its own velocity (a movement component's), else
				// how far it moved since this query's previous sample (null the first time it is seen)
				const FVector Velocity = Prim && Prim->IsSimulatingPhysics() ? Prim->GetPhysicsLinearVelocity() : SC->GetComponentVelocity();
				const FVector* Before = Q.LastPlaces.Find(FObjectKey(C));
				if (!Velocity.IsNearlyZero())
				{
					V = Num(Velocity.Size());
				}
				else if (Before && T > Q.LastT)
				{
					V = Num(FVector::Dist(SC->GetComponentLocation(), *Before) / (T - Q.LastT));
				}
			}
			else if (Prim && (F == TEXT("extent_x") || F == TEXT("extent_y") || F == TEXT("extent_z")))
			{
				// its world bounds' half-size (a skinned mesh's: around its bones, wherever its bodies went)
				const FVector E = Prim->Bounds.BoxExtent;
				V = Num(F == TEXT("extent_x") ? E.X : F == TEXT("extent_y") ? E.Y : E.Z);
			}
			else if (Prim && F == TEXT("simulating"))
			{
				V = Num(Simulating(Prim) ? 1.0 : 0.0);
			}
			else if (SC && F == TEXT("spin"))
			{
				V = SpinOf(SC);
			}
			else if (Prim && IsChangeField(F))
			{
				V = ChangeField(Change, F);
			}
			else if (Light && F == TEXT("intensity"))
			{
				V = Num(Light->Intensity);
			}
			else if (Light && F == TEXT("on"))
			{
				V = Num(LightOn(Light, World) ? 1.0 : 0.0);
			}
			else if (IsGlowField(F))
			{
				V = GlowField(Glow, F);
			}
			else if (F.StartsWith(TEXT("prop:")))
			{
				V = ReadProp(C, F.Mid(5));
			}
			if (Matched.Num() > MaxRows)
			{
				Full.FindOrAdd(F).Add(V);
			}
			Row->SetField(F, V);
		}
		if (i < MaxRows)
		{
			Row->SetStringField(TEXT("name"), C->GetName());
			Row->SetStringField(TEXT("class"), C->GetClass()->GetName());
			Row->SetStringField(TEXT("owner"), C->GetOwner() ? C->GetOwner()->GetName() : FString());
			if (bGlow && Glow.bRead)
			{
				Row->SetStringField(TEXT("glow_sources"), GlowSources(Glow));  // for logs, never a threshold
				if (Glow.Reads)
				{
					Row->SetStringField(TEXT("glow_read"), GlowReads(Glow));  // for logs, never a threshold
				}
			}
			Rows.Add(MakeShared<FJsonValueObject>(Row));
		}
	}
	if (bSpeed)
	{
		Q.LastPlaces = MoveTemp(Places);
		Q.LastT = T;
	}
	Out.SetArrayField(TEXT("rows"), Rows);
	SetTotal(Out, Total, Rows.Num(), Q.Fields, Full);
}

void FTaskProbeQueries::SamplePieces(FQuery& Q, UWorld* World, APlayerController* PC, FJsonObject& Out)
{
	const TSharedPtr<FJsonObject>* SelObj = nullptr;
	Q.Def->TryGetObjectField(TEXT("select"), SelObj);
	const FSel Sel = ParseSel(SelObj ? *SelObj : TSharedPtr<FJsonObject>());
	FString Mesh;
	if (SelObj && SelObj->IsValid())
	{
		(*SelObj)->TryGetStringField(TEXT("mesh"), Mesh);
	}
	if (!World)
	{
		Out.SetField(TEXT("value"), Null());
		return;
	}
	// owner: an actor selection the component's owner must be in
	TSet<const AActor*> Owners;
	const TSharedPtr<FJsonObject>* OwnerObj = nullptr;
	const bool bOwner = SelObj && SelObj->IsValid() && (*SelObj)->TryGetObjectField(TEXT("owner"), OwnerObj);
	if (bOwner)
	{
		TArray<AActor*> Found;
		int32 OwnerTotal = 0;
		FindActors(World, PC, ParseSel(*OwnerObj), 0, MAX_int32, Found, OwnerTotal);
		Owners.Append(Found);
	}
	FVector NearP = FVector::ZeroVector;
	const bool bNear = Sel.Near.IsSet();
	if (bNear && !ResolvePoint(Sel.Near.Point, World, PC, 1, NearP))
	{
		Out.SetField(TEXT("value"), Null());
		return;
	}
	int64 Count = 0, Visible = 0, Triangles = 0, VisibleTriangles = 0;
	int32 Components = 0;
	TSet<const AActor*> Actors;
	TMap<const UClass*, bool> ClassCache;  // most components share a few classes
	for (TObjectIterator<UMeshComponent> It; It; ++It)
	{
		UMeshComponent* C = *It;
		if (!IsValid(C) || C->HasAnyFlags(RF_ClassDefaultObject | RF_ArchetypeObject) || !C->IsRegistered() || C->GetWorld() != World ||
			C->IsEditorOnly())
		{
			continue;
		}
		const UClass* K = C->GetClass();
		const bool* Cached = ClassCache.Find(K);
		// a world-space widget is a mesh component, but no placed mesh piece
		const bool bClass = Cached ? *Cached : ClassCache.Add(K, !ClassMatches(K, TEXT("WidgetComponent")) && ClassMatches(K, Sel.Class));
		const AActor* Owner = C->GetOwner();
		if (!bClass || (!Sel.Name.IsEmpty() && !C->GetName().MatchesWildcard(Sel.Name)) || (bOwner && !Owners.Contains(Owner)))
		{
			continue;
		}
		const FString AssetName = MeshAssetName(C);
		if (!Mesh.IsEmpty() && (AssetName.IsEmpty() || !AssetName.MatchesWildcard(Mesh)))
		{
			continue;  // select.mesh: only pieces of a mesh asset by that name (a procedural mesh has none)
		}
		const bool bShown = C->IsVisible() && !C->bHiddenInGame && !(Owner && Owner->IsHidden());
		int64 N = 0, NV = 0, T = 0, TV = 0;
		auto Take = [&](const FVector& Where, bool bDrawn, int64 Tris)
		{
			if (bNear && !Sel.Near.Holds(NearP, Where))
			{
				return;
			}
			++N;
			NV += bDrawn ? 1 : 0;
			T += Tris;
			TV += bDrawn ? Tris : 0;
		};
		if (const UInstancedStaticMeshComponent* ISM = Cast<UInstancedStaticMeshComponent>(C))
		{
			if (!ISM->GetStaticMesh())
			{
				continue;
			}
			const int32 Instances = ISM->GetInstanceCount();
			const int64 Each = PieceTriangles(ISM);
			if (!bNear)
			{
				N = Instances;
				NV = bShown ? Instances : 0;
				T = Instances * Each;
				TV = bShown ? T : 0;
			}
			else
			{
				for (int32 i = 0; i < Instances; ++i)
				{
					FTransform Instance;
					if (ISM->GetInstanceTransform(i, Instance, true))
					{
						Take(Instance.GetLocation(), bShown, Each);
					}
				}
			}
		}
		else if (!ProcSections(C, [&](const FBox& Box, bool bSectionVisible, int64 Tris)
		{
			Take(Box.IsValid ? C->GetComponentTransform().TransformPosition(Box.GetCenter()) : C->GetComponentLocation(), bShown && bSectionVisible,
				Tris);
		}))
		{
			if (AssetName.IsEmpty() && (Cast<UStaticMeshComponent>(C) || Cast<USkinnedMeshComponent>(C)))
			{
				continue;  // an empty mesh draws nothing
			}
			Take(C->GetComponentLocation(), bShown, PieceTriangles(C));
		}
		if (N > 0)
		{
			Count += N;
			Visible += NV;
			Triangles += T;
			VisibleTriangles += TV;
			++Components;
			if (Owner)
			{
				Actors.Add(Owner);
			}
		}
	}
	const TSharedRef<FJsonObject> V = MakeShared<FJsonObject>();
	V->SetNumberField(TEXT("count"), (double)Count);
	V->SetNumberField(TEXT("visible"), (double)Visible);
	V->SetNumberField(TEXT("components"), Components);
	V->SetNumberField(TEXT("actors"), Actors.Num());
	V->SetNumberField(TEXT("triangles"), (double)Triangles);
	V->SetNumberField(TEXT("visible_triangles"), (double)VisibleTriangles);
	Out.SetObjectField(TEXT("value"), V);
}

void FTaskProbeQueries::OnViewportRendered(FViewport* Viewport)
{
	// right after the game viewport drew a frame, where the engine takes its own screenshots: the frame after
	// post-processing and tone mapping, with the HUD canvas, before the UMG and Slate UI is drawn over it
	const UGameViewportClient* GVC = GEngine ? GEngine->GameViewport.Get() : nullptr;
	if (!Viewport || !GVC || GVC->Viewport != Viewport)
	{
		return;
	}
	// screen before ui: a ui read of text in a rect draws the window again, UI and all
	if (bWantFrame)
	{
		ReadScreen(Viewport);
	}
	if (bWantUi)
	{
		FillUi();
	}
}

void FTaskProbeQueries::ReadScreen(FViewport* Viewport)
{
	const FIntPoint Size = Viewport->GetSizeXY();
	if (Size.X <= 0 || Size.Y <= 0)
	{
		return;
	}
	TArray<FColor> Pixels;
	if (!Viewport->ReadPixels(Pixels, FReadSurfaceDataFlags(), FIntRect(0, 0, Size.X, Size.Y)) || Pixels.Num() < Size.X * Size.Y)
	{
		return;
	}
	const int32 W = Size.X, H = Size.Y;
	const int32 Stride = Pixels.Num() / H;  // the read-back rows (the render target may be wider than the viewport)
	bWantFrame = false;
	for (FQuery& Q : Queries)
	{
		if (Q.Kind != TEXT("screen") || Q.Pending.Num() == 0)
		{
			continue;
		}
		const int32 X0 = FMath::Clamp(FMath::FloorToInt(FMath::Min(Q.Rect[0], Q.Rect[2]) * W), 0, W - 1);
		const int32 Y0 = FMath::Clamp(FMath::FloorToInt(FMath::Min(Q.Rect[1], Q.Rect[3]) * H), 0, H - 1);
		const int32 X1 = FMath::Clamp(FMath::CeilToInt(FMath::Max(Q.Rect[0], Q.Rect[2]) * W), X0 + 1, W);
		const int32 Y1 = FMath::Clamp(FMath::CeilToInt(FMath::Max(Q.Rect[1], Q.Rect[3]) * H), Y0 + 1, H);
		double Lum = 0.0, Luma = 0.0;
		for (int32 y = Y0; y < Y1; ++y)
		{
			const FColor* Row = Pixels.GetData() + (int64)y * Stride;
			for (int32 x = X0; x < X1; ++x)
			{
				const FColor& P = Row[x];
				Lum += 0.2126 * SrgbToLinear(P.R) + 0.7152 * SrgbToLinear(P.G) + 0.0722 * SrgbToLinear(P.B);
				Luma += (0.2126 * P.R + 0.7152 * P.G + 0.0722 * P.B) / 255.0;
			}
		}
		const double Count = (double)(X1 - X0) * (Y1 - Y0);
		const TSharedRef<FJsonObject> V = MakeShared<FJsonObject>();
		V->SetField(TEXT("luminance"), Num(Lum / Count));
		V->SetField(TEXT("luma"), Num(Luma / Count));
		V->SetNumberField(TEXT("pixels"), Count);
		V->SetField(TEXT("size"), Arr({(double)W, (double)H}));
		for (const TSharedPtr<FJsonObject>& S : Q.Pending)
		{
			S->SetObjectField(TEXT("value"), V);
		}
		Q.Pending.Reset();
	}
}

void FTaskProbeQueries::OnHudPostRender(AHUD* Hud, UCanvas* DebugCanvas)
{
	// when a HUD has drawn, its canvas holds every draw of the frame's HUDs (split screen: each HUD after the one before)
	UWorld* World = Hud ? Hud->GetWorld() : nullptr;
	UCanvas* HudCanvas = Hud ? FTaskProbeHudPeek::CanvasOf(*Hud) : nullptr;
	if (!bWantUi || !HudCanvas || !HudCanvas->Canvas || !World || !World->IsGameWorld())
	{
		return;
	}
	CanvasNow.Reset();
	UiCanvas(*HudCanvas->Canvas, CanvasNow);
	CanvasFrame = GFrameCounter;
}

void FTaskProbeQueries::FillUi()
{
	// everything on screen this frame: the visible Slate tree under the game viewport (UMG included) and what the HUD
	// canvas held when the HUD had drawn this frame
	bWantUi = false;
	TArray<FUiElement> Found;
	const UGameViewportClient* GVC = GEngine ? GEngine->GameViewport.Get() : nullptr;
	const TSharedPtr<SViewport> Root = GVC ? GVC->GetGameViewportWidget() : nullptr;
	if (Root.IsValid())
	{
		UiSlate(Root.ToSharedRef(), Found);
	}
	if (CanvasFrame == GFrameCounter)
	{
		Found.Append(CanvasNow);
	}
	CanvasNow.Reset();
	// what widgets painted themselves in the game window's last paint (Slate paints after the viewport draws, so the
	// paint before this frame's, laid out as the walk above reads it)
	if (PaintFrame > 0 && PaintFrame + 2 >= GFrameCounter)
	{
		Found.Append(PaintNow);
	}
	// the frame as drawn, captured once and only when a query asks for text in a rect (UiOcr)
	TArray<FColor> Frame;
	int32 FrameW = 0, FrameH = 0;
	bool bFrameTried = false, bFrame = false;
	for (FQuery& Q : Queries)
	{
		if (Q.Kind != TEXT("ui") || Q.Pending.Num() == 0)
		{
			continue;
		}
		FString Kind, TextRegex;
		double Rect[4] = {0.0, 0.0, 1.0, 1.0};
		bool bRect = false;
		const TSharedPtr<FJsonObject>* SelObj = nullptr;
		if (Q.Def->TryGetObjectField(TEXT("select"), SelObj) && SelObj->IsValid())
		{
			(*SelObj)->TryGetStringField(TEXT("kind"), Kind);
			(*SelObj)->TryGetStringField(TEXT("text"), TextRegex);
			const TArray<TSharedPtr<FJsonValue>>* R = nullptr;
			if ((*SelObj)->TryGetArrayField(TEXT("rect"), R) && R->Num() == 4)
			{
				bRect = true;
				for (int32 i = 0; i < 4; ++i)
				{
					double V = 0.0;
					if ((*R)[i].IsValid() && (*R)[i]->TryGetNumber(V))
					{
						Rect[i] = V;
					}
				}
			}
		}
		const TOptional<FRegexPattern> Pattern = TextRegex.IsEmpty() ? TOptional<FRegexPattern>() : TOptional<FRegexPattern>(FRegexPattern(TextRegex));
		// text read from the frame in the rect: this query's own rows, after every element read the other ways
		TArray<FUiElement> Read;
		if (Q.bOcr && bRect)
		{
			if (!bFrameTried)
			{
				bFrameTried = true;
				bFrame = UiFrame(Frame, FrameW, FrameH);
			}
			if (bFrame)
			{
				UiOcr(Frame, FrameW, FrameH, Rect, Found, Read);
			}
		}
		TArray<const FUiElement*> Candidates;
		for (const FUiElement& E : Found)
		{
			Candidates.Add(&E);
		}
		for (const FUiElement& E : Read)
		{
			Candidates.Add(&E);
		}
		TArray<const FUiElement*> Picked;
		for (const FUiElement* Each : Candidates)
		{
			const FUiElement& E = *Each;
			if ((!Kind.IsEmpty() && E.Kind != Kind) || (Pattern.IsSet() && E.Kind != TEXT("text")))
			{
				continue;
			}
			if (Pattern.IsSet())
			{
				FRegexMatcher Matcher(Pattern.GetValue(), E.Text);
				if (!Matcher.FindNext())
				{
					continue;
				}
			}
			if (bRect)
			{
				const double Cx = E.X + E.W / 2.0, Cy = E.Y + E.H / 2.0;
				if (!E.bHasRect || Cx < FMath::Min(Rect[0], Rect[2]) || Cx > FMath::Max(Rect[0], Rect[2]) || Cy < FMath::Min(Rect[1], Rect[3]) ||
					Cy > FMath::Max(Rect[1], Rect[3]))
				{
					continue;
				}
			}
			Picked.Add(&E);
		}
		TArray<TSharedPtr<FJsonValue>> Rows;
		TMap<FString, FFull> Full;  // every match's values, when more matched than the rows hold
		for (int32 i = 0; i < Picked.Num(); ++i)
		{
			const FUiElement& E = *Picked[i];
			const TSharedRef<FJsonObject> Row = MakeShared<FJsonObject>();
			for (const FString& F : Q.Fields)
			{
				const TSharedPtr<FJsonValue> V = UiField(E, F);
				if (Picked.Num() > MaxRows)
				{
					Full.FindOrAdd(F).Add(V);
				}
				Row->SetField(F, V);
			}
			if (i < MaxRows)
			{
				Row->SetStringField(TEXT("name"), E.Name);
				Row->SetStringField(TEXT("class"), E.Class);
				Row->SetStringField(TEXT("source"), E.Source);
				Row->SetStringField(TEXT("kind"), E.Kind);
				Rows.Add(MakeShared<FJsonValueObject>(Row));
			}
		}
		for (const TSharedPtr<FJsonObject>& S : Q.Pending)
		{
			S->SetArrayField(TEXT("rows"), Rows);
			SetTotal(*S, Picked.Num(), Rows.Num(), Q.Fields, Full);
		}
		Q.Pending.Reset();
	}
}

void FTaskProbeQueries::Listen(UWorld* World, double T)
{
	// audio's started fields: once a frame, before the world ticks, the audio thread looks at every active sound. A sound
	// stays active from its start until its source has played out, at least one audio update, so none slips between two
	// looks however short it is; one the engine never starts (out of voices, too far to hear and not virtualized) is
	// never active, and never heard. A start is stamped with this look's play time, a frame after the game asked for it
	// at most.
	FAudioDevice* Device = World ? World->GetAudioDeviceRaw() : nullptr;
	if (!SoundStarts.IsValid() || !Device)
	{
		return;
	}
	const TSharedPtr<FSoundStarts, ESPMode::ThreadSafe> Followed = SoundStarts;
	FAudioThread::RunCommandOnAudioThread([Device, Followed, T]()
	{
		FScopeLock Guard(&Followed->Lock);
		TMap<const FActiveSound*, FSoundStarts::FSeen> Seen;
		for (const FActiveSound* Active : Device->GetActiveSounds())
		{
			if (!Active)
			{
				continue;
			}
			const USoundBase* S = Active->GetSound();
			const float Playback = PlaybackOf(*Active);
			const uint64 Component = ComponentOf(*Active);
			const FSoundStarts::FSeen* Before = Followed->Live.Find(Active);
			FSoundStarts::FSeen Now;
			Now.Playback = Playback;
			Now.Sound = S;
			Now.Component = Component;
			// the same sound as at the last look: the same active sound, its playback not gone back
			const bool bSame = Before && Before->Sound == S && Before->Component == Component &&
				(Playback < 0.f || Playback + 0.001f >= Before->Playback);
			const bool bLoops = LoopsOf(S);
			if (bSame)
			{
				Now.Index = Before->Index;
			}
			else if (Followed->bLooked && ((Playback >= 0.f && Playback > FreshPlayback) ||
				(bLoops && Component != 0 && Followed->Loops.Contains(TPair<uint64, const USoundBase*>(Component, S)))))
			{
				// not a start: a sound already playing that the engine made active again (a looping sound virtualized
				// while out of hearing and realized on approach, its playback on, or its component's loop seen before)
				Now.Index = INDEX_NONE;
			}
			else if (Followed->Starts.Num() < MaxSoundStarts)
			{
				FSoundStart& Start = Followed->Starts.AddDefaulted_GetRef();
				Start.Sound = S ? S->GetName() : FString();
				Start.bNamed = S && !S->HasAnyFlags(RF_Transient) && S->GetPackage() != GetTransientPackage();
				Start.Classes = SoundClasses(*Active);
				Start.bPlaced = PlaceOf(*Active, Start.Location);
				Start.T = T;
				Now.Index = Followed->Starts.Num() - 1;
			}
			else
			{
				Followed->bCapped = true;
			}
			if (bLoops && Component != 0)
			{
				Followed->Loops.Add(TPair<uint64, const USoundBase*>(Component, S));
			}
			if (Now.Index != INDEX_NONE)
			{
				FSoundStart& Start = Followed->Starts[Now.Index];
				const double Volume = HeardVolume(*Active);
				Start.Peak = FMath::Max(Start.Peak, Volume);
				if (Start.AudibleT < 0.0 && Volume >= AudibleVolume)
				{
					Start.AudibleT = T;
				}
			}
			Seen.Add(Active, Now);
		}
		Followed->Live = MoveTemp(Seen);
		Followed->bLooked = true;
	});
}

void FTaskProbeQueries::SampleAudio(FQuery& Q, UWorld* World, APlayerController* PC, double T, FJsonObject& Out)
{
	// what the player hears: the audio device's active sounds, each at its volume at the listener (the player's camera,
	// or whatever the game listens from): its wave instances' volume (the sound's own, its class's and mixes', the
	// game's multipliers) times their distance and occlusion attenuation and dynamic volume, summed. The output's
	// primary volume (the play's -muteaudio, an unfocused window) is left out. And the sounds that started since the
	// play began (Listen), counted to this sample, with those since the last sample listed.
	// this sample's starts are those after the previous sample's, whatever this sample reads (a sample that reads
	// nothing loses its interval's starts, never moves them into the next)
	const double Since = Q.HeardT;
	Q.HeardT = T;
	FAudioDevice* Device = World ? World->GetAudioDeviceRaw() : nullptr;
	if (!Device)
	{
		Out.SetField(TEXT("value"), Null());  // no audio device (-nosound): nothing is heard, so nothing is measured
		return;
	}
	FString Sound, SoundClass;
	TSet<FObjectKey> Owners;
	bool bOwner = false;
	FNearSel Near;
	const TSharedPtr<FJsonObject>* SelObj = nullptr;
	if (Q.Def->TryGetObjectField(TEXT("select"), SelObj) && SelObj->IsValid())
	{
		(*SelObj)->TryGetStringField(TEXT("sound"), Sound);
		(*SelObj)->TryGetStringField(TEXT("sound_class"), SoundClass);
		const TSharedPtr<FJsonObject>* OwnerObj = nullptr;
		if ((*SelObj)->TryGetObjectField(TEXT("owner"), OwnerObj))
		{
			bOwner = true;
			TArray<AActor*> Found;
			int32 OwnerTotal = 0;
			FindActors(World, PC, ParseSel(*OwnerObj), 0, MAX_int32, Found, OwnerTotal);
			for (const AActor* A : Found)
			{
				Owners.Add(FObjectKey(A));
			}
		}
		Near = ParseNear(*SelObj);
	}
	// near: where the point is at this sample; a sound with no place (2D, unspatialized) is near nothing
	FVector NearP = FVector::ZeroVector;
	if (Near.IsSet() && !ResolvePoint(Near.Point, World, PC, 1, NearP))
	{
		Out.SetField(TEXT("value"), Null());
		return;
	}
	auto Selected = [&](const FString& Name, const TArray<FString>& Classes, const FObjectKey& Owner, bool bPlaced, const FVector& Location)
	{
		return !((!Sound.IsEmpty() && !Name.MatchesWildcard(Sound)) || (bOwner && !Owners.Contains(Owner)) ||
			(!SoundClass.IsEmpty() && !Classes.ContainsByPredicate([&](const FString& K) { return K.MatchesWildcard(SoundClass); })) ||
			(Near.IsSet() && !(bPlaced && Near.Holds(NearP, Location))));
	};
	struct FHeard
	{
		FString Sound;
		TArray<FString> Classes;  // its sound class and the parents of it
		FObjectKey Owner;
		bool bPlaced = false;
		FVector Location = FVector::ZeroVector;
		double Volume = 0.0;
	};
	const TSharedRef<TArray<FHeard>, ESPMode::ThreadSafe> Heard = MakeShared<TArray<FHeard>, ESPMode::ThreadSafe>();
	FAudioThread::RunCommandOnAudioThread([Device, Heard]()
	{
		for (const FActiveSound* Active : Device->GetActiveSounds())
		{
			if (!Active)
			{
				continue;
			}
			FHeard H;
			const USoundBase* S = Active->GetSound();
			H.Sound = S ? S->GetName() : FString();
			H.Classes = SoundClasses(*Active);
			H.Owner = Active->GetOwnerKey();
			H.bPlaced = PlaceOf(*Active, H.Location);
			H.Volume = HeardVolume(*Active);
			Heard->Add(MoveTemp(H));
		}
	});
	FAudioCommandFence Fence;
	Fence.BeginFence();
	Fence.Wait();
	int32 Count = 0, Audible = 0;
	double Volume = 0.0, Max = 0.0;
	FString Loudest;
	for (const FHeard& H : *Heard)
	{
		if (!Selected(H.Sound, H.Classes, H.Owner, H.bPlaced, H.Location))
		{
			continue;
		}
		++Count;
		Audible += H.Volume >= AudibleVolume ? 1 : 0;
		Volume += H.Volume;
		if (Loudest.IsEmpty() || H.Volume > Max)
		{
			Max = H.Volume;
			Loudest = H.Sound;
		}
	}
	const TSharedRef<FJsonObject> V = MakeShared<FJsonObject>();
	V->SetNumberField(TEXT("count"), Count);
	V->SetNumberField(TEXT("audible"), Audible);
	V->SetField(TEXT("volume"), Num(Volume));
	V->SetField(TEXT("max_volume"), Num(Max));
	V->SetField(TEXT("loudest"), Count ? Str(Loudest) : Null());
	if (SoundStarts.IsValid())
	{
		// the starts since the previous sample, each counted once, here, by this sample's select (the fence above has
		// run every look Listen asked for until now); started_audible counts a start where it first reached 0.001. A
		// started field is never read with an owner (checks.AudioMeasure: an owner gone by the sample would lose its
		// sound), so a start keeps no owner.
		int32 Started = 0, StartedAudible = 0, Listed = 0;
		TArray<TSharedPtr<FJsonValue>> Rows;
		FScopeLock Guard(&SoundStarts->Lock);
		for (const FSoundStart& St : SoundStarts->Starts)
		{
			const bool bNew = St.T > Since + 1e-6 && St.T <= T + 1e-6;
			const bool bHeard = St.AudibleT > Since + 1e-6 && St.AudibleT <= T + 1e-6;
			if ((!bNew && !bHeard) || !Selected(St.Sound, St.Classes, FObjectKey(), St.bPlaced, St.Location))
			{
				continue;
			}
			StartedAudible += bHeard ? 1 : 0;
			if (!bNew)
			{
				continue;
			}
			++Started;
			if (Listed++ < MaxStartRows)
			{
				const TSharedRef<FJsonObject> R = MakeShared<FJsonObject>();
				R->SetNumberField(TEXT("t"), St.T);
				R->SetStringField(TEXT("sound"), St.Sound);
				R->SetBoolField(TEXT("named"), St.bNamed);
				R->SetField(TEXT("class"), St.Classes.Num() ? Str(St.Classes[0]) : Null());
				R->SetField(TEXT("x"), St.bPlaced ? Num(St.Location.X) : Null());
				R->SetField(TEXT("y"), St.bPlaced ? Num(St.Location.Y) : Null());
				R->SetField(TEXT("z"), St.bPlaced ? Num(St.Location.Z) : Null());
				R->SetField(TEXT("peak"), Num(St.Peak));
				Rows.Add(MakeShared<FJsonValueObject>(R));
			}
		}
		V->SetNumberField(TEXT("started"), Started);
		V->SetNumberField(TEXT("started_audible"), StartedAudible);
		V->SetArrayField(TEXT("starts"), Rows);
		V->SetNumberField(TEXT("starts_total"), Started);
		if (SoundStarts->bCapped)
		{
			V->SetBoolField(TEXT("starts_capped"), true);
		}
	}
	Out.SetObjectField(TEXT("value"), V);
}

void FTaskProbeQueries::SampleGround(FQuery& Q, UWorld* World, APlayerController* PC, FJsonObject& Out)
{
	if (!World || Q.Grid <= 0)
	{
		Out.SetField(TEXT("value"), Null());
		return;
	}
	// the ground at a point: the first thing a trace straight down (on the visibility channel, against complex
	// collision) meets, pawns aside; with select, only an actor the select matches counts as ground (others are
	// traced through)
	const TSharedPtr<FJsonObject>* SelObj = nullptr;
	const bool bSelect = Q.Def->TryGetObjectField(TEXT("select"), SelObj) && SelObj->IsValid();
	TSet<const AActor*> Ground;
	if (bSelect)
	{
		TArray<AActor*> Found;
		int32 Total = 0;
		FindActors(World, PC, ParseSel(*SelObj), 0, MAX_int32, Found, Total);
		Ground.Append(Found);
	}
	FCollisionQueryParams Params(FName(TEXT("TaskProbeGround")), true);
	for (TActorIterator<APawn> It(World); It; ++It)
	{
		Params.AddIgnoredActor(*It);
	}
	auto Down = [&](double X, double Y, double& Z)
	{
		FCollisionQueryParams Through = Params;
		for (int32 Tries = 0; Tries < 32; ++Tries)
		{
			FHitResult Hit;
			if (!World->LineTraceSingleByChannel(Hit, FVector(X, Y, TraceLength), FVector(X, Y, -TraceLength), ECC_Visibility, Through))
			{
				return false;
			}
			const AActor* HitActor = Hit.GetActor();
			if (!bSelect || (HitActor && Ground.Contains(HitActor)))
			{
				Z = Hit.ImpactPoint.Z;
				return true;
			}
			if (!HitActor)
			{
				return false;
			}
			Through.AddIgnoredActor(HitActor);
		}
		return false;
	};
	const TSharedRef<FJsonObject> V = MakeShared<FJsonObject>();
	if (!Q.bGroundBox)
	{
		double Z = 0.0;
		const bool bHit = Down(Q.Ground[0], Q.Ground[1], Z);
		V->SetField(TEXT("height"), bHit ? Num(Z) : Null());
		V->SetNumberField(TEXT("hit"), bHit ? 1 : 0);
		Out.SetObjectField(TEXT("value"), V);
		return;
	}
	// the box on a grid x grid lattice, its corners and edges included
	int32 Hits = 0;
	double Min = 0.0, Max = 0.0, Sum = 0.0;
	for (int32 i = 0; i < Q.Grid; ++i)
	{
		for (int32 j = 0; j < Q.Grid; ++j)
		{
			const double X = FMath::Lerp(Q.Ground[0], Q.Ground[2], (double)i / (Q.Grid - 1));
			const double Y = FMath::Lerp(Q.Ground[1], Q.Ground[3], (double)j / (Q.Grid - 1));
			double Z = 0.0;
			if (!Down(X, Y, Z))
			{
				continue;
			}
			Min = Hits ? FMath::Min(Min, Z) : Z;
			Max = Hits ? FMath::Max(Max, Z) : Z;
			Sum += Z;
			++Hits;
		}
	}
	V->SetField(TEXT("min"), Hits ? Num(Min) : Null());
	V->SetField(TEXT("max"), Hits ? Num(Max) : Null());
	V->SetField(TEXT("mean"), Hits ? Num(Sum / Hits) : Null());
	V->SetField(TEXT("range"), Hits ? Num(Max - Min) : Null());
	V->SetNumberField(TEXT("hits"), Hits);
	V->SetNumberField(TEXT("points"), Q.Grid * Q.Grid);
	Out.SetObjectField(TEXT("value"), V);
}

void FTaskProbeQueries::SampleLight(FQuery& Q, UWorld* World, APlayerController* PC, FJsonObject& Out)
{
	const TSharedPtr<FJsonObject>* PointObj = nullptr;
	Q.Def->TryGetObjectField(TEXT("point"), PointObj);
	FVector P;
	if (!World || !ResolvePoint(PointObj ? *PointObj : TSharedPtr<FJsonObject>(), World, PC, 0, P))
	{
		Out.SetField(TEXT("value"), Null());
		return;
	}
	const APawn* Pawn = PlayerPawn(PC);
	auto Blocked = [&](const FVector& To, const AActor* LightOwner)
	{
		FCollisionQueryParams Params(FName(TEXT("TaskProbeLight")), false);
		if (Pawn)
		{
			Params.AddIgnoredActor(Pawn);  // the point is usually at the pawn: it doesn't shade itself
		}
		if (LightOwner)
		{
			Params.AddIgnoredActor(LightOwner);  // a lamp's own housing
		}
		FHitResult Hit;
		return World->LineTraceSingleByChannel(Hit, P, To, ECC_Visibility, Params);
	};
	double Local = 0.0, Directional = 0.0, Sky = 0.0;
	int32 Lit = 0;
	for (TObjectIterator<ULightComponentBase> It; It; ++It)
	{
		ULightComponentBase* Base = *It;
		if (!LightOn(Base, World))
		{
			continue;
		}
		if (const USkyLightComponent* SkyL = Cast<USkyLightComponent>(Base))
		{
			// the sky light by its intensity (and colour), times the share of the upper hemisphere open to the sky
			// (9 traces: straight up and 8 at 45 degrees)
			int32 Open = 0;
			const int32 Rays = 9;
			for (int32 r = 0; r < Rays; ++r)
			{
				FVector Dir = FVector::UpVector;
				if (r > 0)
				{
					const double A = (r - 1) * UE_DOUBLE_PI / 4.0;
					Dir = FVector(FMath::Cos(A) * 0.70710678118654752, FMath::Sin(A) * 0.70710678118654752, 0.70710678118654752);
				}
				if (!SkyL->CastShadows || !Blocked(P + Dir * TraceLength, SkyL->GetOwner()))
				{
					++Open;
				}
			}
			const double C = SkyL->Intensity * FLinearColor(SkyL->LightColor).GetLuminance() * Open / Rays;
			Sky += C;
			Lit += C > 0.0 ? 1 : 0;
			continue;
		}
		const ULightComponent* L = Cast<ULightComponent>(Base);
		if (!L)
		{
			continue;
		}
		const double Lum = L->GetColoredLightBrightness().GetLuminance();
		if (const UDirectionalLightComponent* D = Cast<UDirectionalLightComponent>(L))
		{
			// illuminance in lux, if a trace toward the light is clear
			if (D->CastShadows && Blocked(P - D->GetDirection() * TraceLength, D->GetOwner()))
			{
				continue;
			}
			Directional += Lum;
			Lit += Lum > 0.0 ? 1 : 0;
			continue;
		}
		const ULocalLightComponent* LL = Cast<ULocalLightComponent>(L);
		if (!LL)
		{
			continue;
		}
		const FVector LP = LL->GetComponentLocation();
		const FVector ToP = P - LP;
		const double Dist = ToP.Size();
		const double Radius = LL->AttenuationRadius;
		if (Radius <= 0.0 || Dist >= Radius)
		{
			continue;
		}
		const FVector Dir = Dist > UE_KINDA_SMALL_NUMBER ? ToP / Dist : LL->GetForwardVector();
		const UPointLightComponent* PL = Cast<UPointLightComponent>(LL);
		double Falloff = 0.0;
		if (!PL || PL->bUseInverseSquaredFalloff)
		{
			// ComputeLightBrightness is in candela x 1e4 (per cm2), so brightness / d(cm)^2 = candela / d(m)^2 = lux;
			// times the engine's attenuation-radius window, saturate(1 - (d/r)^4)^2
			const double Window = FMath::Square(FMath::Clamp(1.0 - FMath::Pow(Dist / Radius, 4.0), 0.0, 1.0));
			Falloff = Window / FMath::Max(Dist * Dist, 1.0);
		}
		else
		{
			// legacy (unitless) falloff: (1 - saturate(d^2/r^2))^exponent, reported in the light's own units
			Falloff = FMath::Pow(FMath::Clamp(1.0 - FMath::Square(Dist / Radius), 0.0, 1.0), (double)PL->LightFalloffExponent);
		}
		if (const USpotLightComponent* SL = Cast<USpotLightComponent>(LL))
		{
			// the engine's spot cone: saturate((cos(angle) - cos(outer)) / (cos(inner) - cos(outer)))^2
			const double Inner = FMath::DegreesToRadians(FMath::Clamp((double)SL->InnerConeAngle, 0.0, 89.0));
			const double Outer = FMath::DegreesToRadians(FMath::Clamp((double)SL->OuterConeAngle, FMath::RadiansToDegrees(Inner) + 0.001, 89.0 + 0.001));
			const double CosOuter = FMath::Cos(Outer);
			const double InvRange = 1.0 / FMath::Max(FMath::Cos(Inner) - CosOuter, 1e-4);
			const double CosAngle = FVector::DotProduct(Dir, SL->GetForwardVector());
			Falloff *= FMath::Square(FMath::Clamp((CosAngle - CosOuter) * InvRange, 0.0, 1.0));
		}
		else if (Cast<URectLightComponent>(LL))
		{
			// a rect light emits forward with a cosine distribution
			Falloff *= FMath::Max(0.0, FVector::DotProduct(Dir, LL->GetForwardVector()));
		}
		const double C = Lum * Falloff;
		if (C <= 0.0)
		{
			continue;
		}
		if (LL->CastShadows && Blocked(LP, LL->GetOwner()))
		{
			continue;
		}
		Local += C;
		++Lit;
	}
	const double Illuminance = Local + Directional + Sky;
	const TSharedRef<FJsonObject> V = MakeShared<FJsonObject>();
	V->SetField(TEXT("illuminance"), Num(Illuminance));
	const bool bExposure = ViewExtension.IsValid() && ViewExtension->bSeen && ViewExtension->Exposure > 0.f;
	V->SetField(TEXT("exposure"), bExposure ? Num(ViewExtension->Exposure) : Null());
	V->SetField(TEXT("brightness"), bExposure ? Num(Illuminance * ViewExtension->Exposure) : Null());
	V->SetField(TEXT("local"), Num(Local));
	V->SetField(TEXT("directional"), Num(Directional));
	V->SetField(TEXT("sky"), Num(Sky));
	V->SetNumberField(TEXT("lights"), Lit);
	V->SetField(TEXT("point"), Arr({P.X, P.Y, P.Z}));
	Out.SetObjectField(TEXT("value"), V);
}

void FTaskProbeQueries::SampleGrading(FQuery& Q, UWorld* World, APlayerController* PC, FJsonObject& Out)
{
	if (!World)
	{
		Out.SetField(TEXT("value"), Null());
		return;
	}
	FGrade G;
	FString Source;
	if (ViewExtension.IsValid() && ViewExtension->bSeen)
	{
		G = ViewExtension->Grade;  // what the renderer used for the player's view
		Source = TEXT("view");
	}
	else
	{
		// no view rendered yet: blend here, the unbound and enclosing volumes by priority and weight, then the camera's
		const FPostProcessSettings Defaults;
		G.From(Defaults);
		const APlayerCameraManager* View = PC ? PC->PlayerCameraManager.Get() : nullptr;
		const FVector Loc = View ? View->GetCameraLocation() : FVector::ZeroVector;
		for (IInterface_PostProcessVolume* Vol : World->PostProcessVolumes)
		{
			if (!Vol)
			{
				continue;
			}
			const FPostProcessVolumeProperties Props = Vol->GetProperties();
			if (!Props.bIsEnabled || !Props.Settings)
			{
				continue;
			}
			float W = FMath::Clamp(Props.BlendWeight, 0.f, 1.f);
			if (!Props.bIsUnbound)
			{
				float Dist = 0.f;
				if (!Vol->EncompassesPoint(Loc, Props.BlendRadius, &Dist) || Dist < 0.f)
				{
					continue;
				}
				if (Dist > 0.f && Props.BlendRadius >= 1.f)
				{
					W *= FMath::Clamp(1.f - Dist / Props.BlendRadius, 0.f, 1.f);
				}
			}
			G.Blend(*Props.Settings, W);
		}
		if (View)
		{
			const FMinimalViewInfo& POV = View->GetCameraCacheView();
			G.Blend(POV.PostProcessSettings, POV.PostProcessBlendWeight);
		}
		Source = TEXT("volumes");
	}
	const TSharedRef<FJsonObject> V = MakeShared<FJsonObject>();
	V->SetStringField(TEXT("source"), Source);
	V->SetField(TEXT("white_temp"), Num(G.WhiteTemp));
	V->SetField(TEXT("white_tint"), Num(G.WhiteTint));
	V->SetField(TEXT("saturation"), V4(G.Saturation));
	V->SetField(TEXT("contrast"), V4(G.Contrast));
	V->SetField(TEXT("gamma"), V4(G.Gamma));
	V->SetField(TEXT("gain"), V4(G.Gain));
	V->SetField(TEXT("offset"), V4(G.Offset));
	V->SetField(TEXT("auto_exposure_bias"), Num(G.ExposureBias));
	V->SetField(TEXT("auto_exposure_min"), Num(G.ExposureMin));
	V->SetField(TEXT("auto_exposure_max"), Num(G.ExposureMax));
	V->SetNumberField(TEXT("auto_exposure_method"), G.ExposureMethod);
	V->SetField(TEXT("lut"), G.Lut.IsValid() ? Str(G.Lut->GetPathName()) : Null());
	V->SetField(TEXT("lut_intensity"), Num(G.LutIntensity));

	// post:<FPostProcessSettings property>[.<Sub>]: any post-process value in effect at the camera
	TArray<FString> PostNames;
	for (const FString& F : Q.Fields)
	{
		if (F.StartsWith(TEXT("post:")) && F.Len() > 5)
		{
			PostNames.Add(F);
		}
	}
	if (PostNames.Num() > 0)
	{
		const FPostProcessSettings* Settings = nullptr;
		FPostProcessSettings Blended;
		if (Source == TEXT("view") && ViewExtension->Full.IsValid())
		{
			Settings = ViewExtension->Full.Get();
		}
		else
		{
			TArray<FString> Tops;
			for (const FString& F : PostNames)
			{
				FString Top = F.Mid(5);
				Top.Split(TEXT("."), &Top, nullptr);
				Tops.AddUnique(Top);
			}
			BlendPost(World, PC, Tops, Blended);
			Settings = &Blended;
		}
		for (const FString& F : PostNames)
		{
			TArray<FString> Toks;
			F.Mid(5).ParseIntoArray(Toks, TEXT("."), true);
			V->SetField(F, WalkProp(nullptr, const_cast<FPostProcessSettings*>(Settings), FPostProcessSettings::StaticStruct(), Toks, 0));
		}
	}

	// the key lights: the strongest directional light, the sky light, the height fog
	const UDirectionalLightComponent* Sun = nullptr;
	const USkyLightComponent* SkyL = nullptr;
	for (TObjectIterator<ULightComponentBase> It; It; ++It)
	{
		if (!LightOn(*It, World))
		{
			continue;
		}
		if (const UDirectionalLightComponent* D = Cast<UDirectionalLightComponent>(*It))
		{
			if (!Sun || D->Intensity > Sun->Intensity)
			{
				Sun = D;
			}
		}
		else if (const USkyLightComponent* S = Cast<USkyLightComponent>(*It))
		{
			if (!SkyL || S->Intensity > SkyL->Intensity)
			{
				SkyL = S;
			}
		}
	}
	if (Sun)
	{
		const TSharedRef<FJsonObject> O = MakeShared<FJsonObject>();
		O->SetStringField(TEXT("name"), OwnerName(Sun));
		const FLinearColor Color(Sun->LightColor);
		O->SetField(TEXT("color"), Rgb(Color));
		O->SetField(TEXT("temperature"), Num(Sun->Temperature));
		O->SetNumberField(TEXT("use_temperature"), Sun->bUseTemperature ? 1 : 0);
		O->SetField(TEXT("intensity"), Num(Sun->Intensity));
		// the colour the light is lit with: its colour times the engine's temperature colour when that is on
		O->SetField(TEXT("lit_color"), Rgb(Sun->bUseTemperature ? Color * Sun->GetColorTemperature() : Color));
		V->SetObjectField(TEXT("sun"), O);
	}
	else
	{
		V->SetField(TEXT("sun"), Null());
	}
	if (SkyL)
	{
		const TSharedRef<FJsonObject> O = MakeShared<FJsonObject>();
		O->SetStringField(TEXT("name"), OwnerName(SkyL));
		O->SetField(TEXT("color"), Rgb(FLinearColor(SkyL->LightColor)));
		O->SetField(TEXT("intensity"), Num(SkyL->Intensity));
		V->SetObjectField(TEXT("sky"), O);
	}
	else
	{
		V->SetField(TEXT("sky"), Null());
	}
	const UExponentialHeightFogComponent* Fog = nullptr;
	for (TObjectIterator<UExponentialHeightFogComponent> It; It; ++It)
	{
		const UExponentialHeightFogComponent* F = *It;
		if (F && F->GetWorld() == World && !F->HasAnyFlags(RF_ClassDefaultObject | RF_ArchetypeObject) && F->IsRegistered() &&
			F->ShouldComponentAddToScene() && (!Fog || F->FogDensity > Fog->FogDensity))
		{
			Fog = F;
		}
	}
	if (Fog)
	{
		const TSharedRef<FJsonObject> O = MakeShared<FJsonObject>();
		O->SetStringField(TEXT("name"), OwnerName(Fog));
		O->SetField(TEXT("density"), Num(Fog->FogDensity));
		O->SetField(TEXT("inscattering"), Rgb(Fog->FogInscatteringLuminance));
		V->SetObjectField(TEXT("fog"), O);
	}
	else
	{
		V->SetField(TEXT("fog"), Null());
	}
	Out.SetObjectField(TEXT("value"), V);
}

void FTaskProbeQueries::SampleCamera(UWorld* World, APlayerController* PC, FJsonObject& Out)
{
	const APlayerCameraManager* View = PC ? PC->PlayerCameraManager.Get() : nullptr;
	if (!World || !View)
	{
		Out.SetField(TEXT("value"), Null());
		return;
	}
	const FVector C = View->GetCameraLocation();
	const FRotator R = View->GetCameraRotation();
	const TSharedRef<FJsonObject> V = MakeShared<FJsonObject>();
	V->SetField(TEXT("pitch"), Num(Angle(R.Pitch)));
	V->SetField(TEXT("yaw"), Num(Angle(R.Yaw)));
	V->SetField(TEXT("fov"), Num(View->GetFOVAngle()));
	APawn* Pawn = PlayerPawn(PC);
	if (!Pawn)
	{
		for (const TCHAR* Key : {TEXT("distance"), TEXT("height"), TEXT("occluded"), TEXT("pawn_on_screen")})
		{
			V->SetField(Key, Null());
		}
		Out.SetObjectField(TEXT("value"), V);
		return;
	}
	// the pawn's centre: its colliding components' bounding box centre, else its location
	FVector Centre = Pawn->GetActorLocation();
	{
		FVector Origin, Extent;
		Pawn->GetActorBounds(true, Origin, Extent, false);
		if (!Extent.IsNearlyZero())
		{
			Centre = Origin;
		}
	}
	V->SetField(TEXT("distance"), Num(FVector::Dist(C, Pawn->GetActorLocation())));
	V->SetField(TEXT("height"), Num(C.Z - Pawn->GetActorLocation().Z));
	FCollisionQueryParams Params(FName(TEXT("TaskProbeCamera")), false);
	if (AActor* Target = View->GetViewTarget(); Target && Target != Pawn)
	{
		Params.AddIgnoredActor(Target);  // a camera actor the view runs through
	}
	FHitResult Hit;
	bool bOccluded = false;
	if (World->LineTraceSingleByChannel(Hit, C, Centre, ECC_Visibility, Params))
	{
		const AActor* HitActor = Hit.GetActor();
		bOccluded = !(HitActor && (HitActor == Pawn || HitActor->IsAttachedTo(Pawn)));
	}
	V->SetNumberField(TEXT("occluded"), bOccluded ? 1 : 0);
	FVector2D Screen;
	int32 SizeX = 0, SizeY = 0;
	PC->GetViewportSize(SizeX, SizeY);
	const bool bProjected = PC->ProjectWorldLocationToScreen(Centre, Screen, false);
	const bool bOnScreen = bProjected && SizeX > 0 && SizeY > 0 && Screen.X >= 0 && Screen.Y >= 0 && Screen.X <= SizeX && Screen.Y <= SizeY;
	V->SetNumberField(TEXT("pawn_on_screen"), bOnScreen ? 1 : 0);
	Out.SetObjectField(TEXT("value"), V);
}

// ---------------------------------------------------------------- spin: how fast a component turns

/** frozen: an actor holds still in a frame when it moved under this (cm) and none of its skinned meshes' bones moved
 *  this far (cm, in its component's space: the largest single bone's move, whatever the skeleton's size); a stop
 *  counts only between two frames of motion and only up to StillLongest (s): a hit stop, never an idle or a rest. */
static constexpr double StillPlace = 0.1;
static constexpr double StillPose = 0.1;
static constexpr double StillLongest = 0.5;

/** The bones of an actor's skinned meshes in their component's space, in order (frozen compares them frame to frame). */
static void PoseOf(const AActor* A, TArray<FVector>& Out)
{
	Out.Reset();
	TInlineComponentArray<USkinnedMeshComponent*> Meshes(A);
	for (const USkinnedMeshComponent* M : Meshes)
	{
		if (!M || !M->IsRegistered())
		{
			continue;
		}
		for (const FTransform& Bone : M->GetComponentSpaceTransforms())
		{
			Out.Add(Bone.GetLocation());
		}
	}
}

void FTaskProbeQueries::Frame(float DeltaTime, UWorld* World)
{
	if (World && bHasWorld)
	{
		// world: a hit pause slows or stops the world for a few frames, which a sample every 0.1 s can fall between (only
		// in a play that reads it: every other play runs as before)
		const AWorldSettings* Settings = World->GetWorldSettings(false, false);
		const double Dilation = Settings ? Settings->GetEffectiveTimeDilation() : 1.0;
		MinDilation = MinDilation < 0.0 ? Dilation : FMath::Min(MinDilation, Dilation);
		bPausedSince = bPausedSince || World->IsPaused();
	}
	for (auto It = Stills.CreateIterator(); It; ++It)
	{
		FStillTrack& T = It.Value();
		const AActor* A = T.Actor.Get();
		if (!A)
		{
			It.RemoveCurrent();
			continue;
		}
		// still: neither its place nor its pose changed since the last frame (a hit stop however made: the world or
		// the actor slowed, a montage paused, the game skipping its tick)
		const FVector Place = A->GetActorLocation();
		TArray<FVector> Bones;
		PoseOf(A, Bones);
		bool bStill = false;
		if (T.bSeen && Bones.Num() == T.Bones.Num())
		{
			double Moved = 0.0;
			for (int32 i = 0; i < Bones.Num(); ++i)
			{
				Moved = FMath::Max(Moved, FVector::Dist(Bones[i], T.Bones[i]));
			}
			bStill = FVector::Dist(Place, T.Place) < StillPlace && Moved < StillPose;
		}
		if (bStill)
		{
			T.Run += T.bMovedBefore ? DeltaTime : 0.0;  // a stop that follows motion
		}
		else if (T.bSeen)
		{
			// motion again: the stop just ended counts when it was short, a pause inside a movement
			if (T.Run > 0.0 && T.Run <= StillLongest)
			{
				T.Longest = FMath::Max(T.Longest, T.Run);
			}
			T.Run = 0.0;
			T.bMovedBefore = true;
		}
		T.Time += DeltaTime;
		T.Place = Place;
		T.Bones = MoveTemp(Bones);
		T.bSeen = true;
	}
	for (auto It = Spins.CreateIterator(); It; ++It)
	{
		FSpinTrack& T = It.Value();
		const USceneComponent* C = T.Component.Get();
		if (!C)
		{
			It.RemoveCurrent();
			continue;
		}
		const FQuat Now = C->GetComponentQuat();
		T.Angle += T.Last.AngularDistance(Now);
		T.Last = Now;
		T.Time += DeltaTime;
	}
}

TSharedPtr<FJsonValue> FTaskProbeQueries::SpinOf(const USceneComponent* C)
{
	// deg/s: how far it turned in the world, frame by frame, since the previous sample; the first sample it is seen in
	// has no value, unless it simulates physics: then its body's angular velocity
	const FObjectKey Key(C);
	SpinRead.Add(Key);
	if (const FSpinTrack* T = Spins.Find(Key); T && T->Time > 0.0)
	{
		return Num(FMath::RadiansToDegrees(T->Angle) / T->Time);
	}
	const UPrimitiveComponent* P = Cast<UPrimitiveComponent>(C);
	if (P && P->IsSimulatingPhysics())
	{
		return Num(P->GetPhysicsAngularVelocityInDegrees().Size());
	}
	return Null();
}

TSharedPtr<FJsonValue> FTaskProbeQueries::ActorStill(const AActor* A)
{
	// s: the longest short stop (moving, still, moving again) that ended since the previous sample; null the first
	// sample it is seen in
	const FObjectKey Key(A);
	StillRead.Add(Key);
	const FStillTrack* T = Stills.Find(Key);
	return T && T->Time > 0.0 ? Num(T->Longest) : Null();
}

void FTaskProbeQueries::SampleWorld(FJsonObject& Out)
{
	const TSharedRef<FJsonObject> V = MakeShared<FJsonObject>();
	if (MinDilation < 0.0)
	{
		V->SetField(TEXT("time_dilation"), Null());  // no frame since the previous sample
	}
	else
	{
		V->SetNumberField(TEXT("time_dilation"), MinDilation);
	}
	V->SetNumberField(TEXT("paused"), bPausedSince ? 1.0 : 0.0);
	Out.SetObjectField(TEXT("value"), V);
}

TSharedPtr<FJsonValue> FTaskProbeQueries::ActorSpin(const AActor* A)
{
	// the fastest of its mesh parts (as changed and extent_ take them); with none, its root component
	TArray<UMeshComponent*> Parts;
	ChangeParts(A, Parts);
	if (Parts.IsEmpty())
	{
		const USceneComponent* Root = A->GetRootComponent();
		return Root ? SpinOf(Root) : Null();
	}
	TSharedPtr<FJsonValue> Best = Null();
	for (const UMeshComponent* M : Parts)
	{
		const TSharedPtr<FJsonValue> V = SpinOf(M);
		if (V.IsValid() && V->Type == EJson::Number && (Best->Type != EJson::Number || V->AsNumber() > Best->AsNumber()))
		{
			Best = V;
		}
	}
	return Best;
}

// ---------------------------------------------------------------- ui: what widgets paint themselves

void FTaskProbeQueries::OnPaintBeginWindow(const FSlateWindowElementList& List)
{
	const UGameViewportClient* GVC = GEngine ? GEngine->GameViewport.Get() : nullptr;
	const TSharedPtr<SWindow> Window = GVC ? const_cast<UGameViewportClient*>(GVC)->GetWindow() : nullptr;
	if (!Window.IsValid() || List.GetPaintWindow() != Window.Get())
	{
		return;
	}
	PaintList = &List;
	PaintStack.Reset();
	PaintRecords.Reset();
	PaintViewportAt = INDEX_NONE;
}

void FTaskProbeQueries::OnPaintBeginWidget(const SWidget* Widget, const FPaintArgs& Args, const FGeometry& Geometry, const FSlateRect& Culling,
	const FSlateWindowElementList& List, int32 Layer)
{
	if (&List != PaintList)
	{
		return;
	}
	const UGameViewportClient* GVC = GEngine ? GEngine->GameViewport.Get() : nullptr;
	const TSharedPtr<SViewport> Viewport = GVC ? GVC->GetGameViewportWidget() : nullptr;
	if (PaintViewportAt == INDEX_NONE && Viewport.IsValid() && Widget == Viewport.Get())
	{
		// the game viewport's rect as painted (window space, as the draw elements are)
		PaintViewportAt = PaintStack.Num();
		PaintViewPos = FVector2D(Geometry.GetAbsolutePosition());
		PaintViewSize = FVector2D(Geometry.GetAbsoluteSize());
	}
	PaintStack.Add(Widget);
}

void FTaskProbeQueries::OnPaintEndWidget(const SWidget* Widget, const FSlateWindowElementList& List, int32 Layer)
{
	if (&List != PaintList || PaintStack.IsEmpty())
	{
		return;
	}
	PaintStack.Pop();
	if (PaintViewportAt != INDEX_NONE && PaintStack.Num() <= PaintViewportAt)
	{
		PaintViewportAt = INDEX_NONE;
	}
}

void FTaskProbeQueries::OnPaintElement(const FSlateDebuggingElementTypeAddedEventArgs& Args)
{
	// an element painted under the game viewport (not by the viewport itself) by a widget the Slate walk doesn't read
	if (&Args.ElementList != PaintList || PaintViewportAt == INDEX_NONE || PaintStack.Num() <= PaintViewportAt + 1 || PaintRecords.Num() >= 4096)
	{
		return;
	}
	const FName Type = PaintStack.Last()->GetType();
	if (WalkReads(Type))
	{
		return;
	}
	FPaintRecord R;
	R.Type = (uint8)Args.ElementType;
	R.Index = Args.ElementIndex;
	R.Widget = Type;
	PaintRecords.Add(R);
}

void FTaskProbeQueries::OnPaintEndWindow(const FSlateWindowElementList& List)
{
	if (&List != PaintList)
	{
		return;
	}
	PaintNow.Reset();
	for (const FPaintRecord& R : PaintRecords)
	{
		FUiElement E;
		if (PaintElement(List, R, PaintViewPos, PaintViewSize, E))
		{
			PaintNow.Add(MoveTemp(E));
		}
	}
	PaintFrame = GFrameCounter;
	PaintRecords.Reset();
	PaintStack.Reset();
	PaintList = nullptr;
}

// ---------------------------------------------------------------- drawn: what is drawn in a place

void FTaskProbeQueries::SampleDrawn(FQuery& Q, UWorld* World, APlayerController* PC, FJsonObject& Out)
{
	Out.SetField(TEXT("value"), Null());
	const TSharedPtr<FJsonObject>* NearObj = nullptr;
	const TSharedPtr<FJsonObject>* LineObj = nullptr;
	const bool bNear = Q.Def->TryGetObjectField(TEXT("near"), NearObj) && NearObj->IsValid();
	const bool bLine = !bNear && Q.Def->TryGetObjectField(TEXT("line"), LineObj) && LineObj->IsValid();
	if (!World || (!bNear && !bLine))
	{
		return;
	}
	if (!DrawnRender.IsValid())
	{
		DrawnRender = MakeUnique<FDrawnRender>();
	}
	const TSharedRef<FJsonObject> V = MakeShared<FJsonObject>();
	TArray<UPrimitiveComponent*> Show;
	if (bNear)
	{
		// a sphere around the point, cut to its height band; four views from the corners of a tetrahedron
		const FNearSel Near = ParseNearObject(*NearObj);
		FVector P;
		if (!ResolvePoint(Near.Point, World, PC, 1, P) || Near.Radius <= 0.0)
		{
			return;
		}
		const double R = Near.Radius;
		const double Base = Near.bZRelative ? P.Z : 0.0;
		FBox Place(P - FVector(R), P + FVector(R));
		if (Near.bZMin)
		{
			Place.Min.Z = FMath::Max(Place.Min.Z, Base + Near.ZMin);
		}
		if (Near.bZMax)
		{
			Place.Max.Z = FMath::Min(Place.Max.Z, Base + Near.ZMax);
		}
		if (Place.Min.Z <= Place.Max.Z)
		{
			DrawnPrimitives(World, Place, [&](const FBox& B)
			{
				return B.ComputeSquaredDistanceToPoint(P) <= R * R && B.Max.Z >= Place.Min.Z && B.Min.Z <= Place.Max.Z;
			}, Show);
		}
		TArray<FDrawnView> Views;
		for (const FVector& Corner : GlowViews)
		{
			const FVector Dir = Corner.GetSafeNormal();
			FDrawnView View;
			View.Location = P + Dir * (R + 50.0);
			View.Rotation = FRotationMatrix::MakeFromX(-Dir).Rotator();
			View.Width = R * 2.0 * 1.02;
			Views.Add(View);
		}
		const int32 N = DrawnNearSize;
		TArray<TArray<FLinearColor>> Lit, BaseColour;
		const bool bBase = Q.Fields.ContainsByPredicate([](const FString& F) { return F.StartsWith(TEXT("base_")); });
		if (!Show.IsEmpty() && !DrawnRender->Render(World, Show, Views, N, SCS_SceneColorSceneDepth, Lit))
		{
			return;  // nothing renders (-nullrhi)
		}
		if (bBase && !Show.IsEmpty() && !DrawnRender->Render(World, Show, Views, N, SCS_BaseColor, BaseColour))
		{
			return;
		}
		// each pixel: kept when what it shows is in the place (its depth puts it inside the sphere and the band), or a
		// translucent pixel with nothing opaque behind it whose ray crosses the sphere
		const int32 Count = Views.Num() * N * N;
		TArray<uint8> Kept;
		TArray<FLinearColor> Colour;
		Kept.SetNumZeroed(Count);
		Colour.SetNumZeroed(Count);
		int64 KeptN = 0, OpaqueN = 0;
		FVector BaseSum = FVector::ZeroVector;
		for (int32 v = 0; v < Views.Num() && !Show.IsEmpty(); ++v)
		{
			const FDrawnFrame Cam(Views[v], N);
			for (int32 y = 0; y < N; ++y)
			{
				for (int32 x = 0; x < N; ++x)
				{
					const int32 i = v * N * N + y * N + x;
					const FLinearColor& C = Lit[v][y * N + x];
					const double Depth = C.A;
					const FVector OnPlane = Cam.Plane(x, y);
					bool bKeep = false, bOpaque = false;
					if (FMath::IsFinite(Depth) && Depth < DrawnBackground)
					{
						const FVector At = OnPlane + Cam.Forward * Depth;
						bKeep = bOpaque = FVector::DistSquared(At, P) <= R * R && Near.InBand(P, At.Z);
					}
					else if (Luminance(C.R, C.G, C.B) > DrawnFaint)
					{
						const FVector Off = OnPlane - P;
						bKeep = (Off - Cam.Forward * FVector::DotProduct(Off, Cam.Forward)).SizeSquared() <= R * R;
					}
					if (!bKeep)
					{
						continue;
					}
					Kept[i] = 1;
					Colour[i] = FLinearColor(Compressed(C.R), Compressed(C.G), Compressed(C.B), 0.f);
					++KeptN;
					if (bOpaque && bBase)
					{
						const FLinearColor& B = BaseColour[v][y * N + x];
						BaseSum += FVector(B.R, B.G, B.B);
						++OpaqueN;
					}
				}
			}
		}
		V->SetNumberField(TEXT("drawn"), KeptN > 0 ? 1.0 : 0.0);
		V->SetNumberField(TEXT("pixels"), (double)KeptN);
		V->SetNumberField(TEXT("primitives"), Show.Num());
		// motion: of the pixels in the place now or at the previous sample, the share that changed
		if (Q.bDrawnBefore && Q.DrawnKept.Num() == Count)
		{
			int64 Union = 0, Changed = 0;
			for (int32 i = 0; i < Count; ++i)
			{
				if (!Kept[i] && !Q.DrawnKept[i])
				{
					continue;
				}
				++Union;
				const FLinearColor& A = Colour[i];
				const FLinearColor& B = Q.DrawnColour[i];
				if (Kept[i] != Q.DrawnKept[i] || FMath::Abs(A.R - B.R) > DrawnStep || FMath::Abs(A.G - B.G) > DrawnStep || FMath::Abs(A.B - B.B) > DrawnStep)
				{
					++Changed;
				}
			}
			V->SetNumberField(TEXT("motion"), Union ? (double)Changed / Union : 0.0);
		}
		else
		{
			V->SetField(TEXT("motion"), Null());
		}
		Q.DrawnKept = MoveTemp(Kept);
		Q.DrawnColour = MoveTemp(Colour);
		Q.bDrawnBefore = true;
		// base colour: the mean of the opaque pixels in the place; base_change its distance from the first sample's
		if (bBase && OpaqueN > 0)
		{
			const FVector Mean = BaseSum / (double)OpaqueN;
			V->SetNumberField(TEXT("base_r"), Mean.X);
			V->SetNumberField(TEXT("base_g"), Mean.Y);
			V->SetNumberField(TEXT("base_b"), Mean.Z);
			if (!Q.bDrawnFirstBase)
			{
				Q.bDrawnFirstBase = true;
				Q.DrawnFirstBase = Mean;
			}
			V->SetNumberField(TEXT("base_change"), FVector::Dist(Mean, Q.DrawnFirstBase));
		}
		else
		{
			for (const TCHAR* F : {TEXT("base_r"), TEXT("base_g"), TEXT("base_b"), TEXT("base_change")})
			{
				V->SetField(F, Null());
			}
		}
	}
	else
	{
		// a line from `from` to `to`: what is drawn within `radius` of it, seen from two sides square to it
		FVector A, B;
		double R = 0.0;
		const TSharedPtr<FJsonObject>* FromObj = nullptr;
		const TSharedPtr<FJsonObject>* ToObj = nullptr;
		(*LineObj)->TryGetNumberField(TEXT("radius"), R);
		if (!(*LineObj)->TryGetObjectField(TEXT("from"), FromObj) || !(*LineObj)->TryGetObjectField(TEXT("to"), ToObj) || R <= 0.0 ||
			!ResolvePoint(*FromObj, World, PC, 1, A) || !ResolvePoint(*ToObj, World, PC, 1, B))
		{
			return;
		}
		const double L = FVector::Dist(A, B);
		if (L < 1.0)
		{
			return;
		}
		const FVector D = (B - A) / L;
		const FBox Place = FBox(A.ComponentMin(B) - FVector(R), A.ComponentMax(B) + FVector(R));
		DrawnPrimitives(World, Place, [&](const FBox& Box)
		{
			const FBox Grown = Box.ExpandBy(R);
			return Grown.IsInside(A) || Grown.IsInside(B) || FMath::LineBoxIntersection(Grown, A, B, B - A);
		}, Show);
		const FVector Side = FMath::Abs(D.Z) < 0.9 ? FVector::CrossProduct(D, FVector::UpVector).GetSafeNormal() : FVector::CrossProduct(D, FVector::ForwardVector).GetSafeNormal();
		const FVector Other = FVector::CrossProduct(D, Side).GetSafeNormal();
		const FVector Mid = (A + B) / 2.0;
		TArray<FDrawnView> Views;
		for (const FVector& Look : {Side, Other})
		{
			FDrawnView View;
			View.Location = Mid - Look * (R + 50.0);
			View.Rotation = FRotationMatrix::MakeFromXZ(Look, Look == Side ? Other : Side).Rotator();
			View.Width = L + 2.0 * R + 20.0;
			Views.Add(View);
		}
		const int32 N = DrawnLineSize;
		TArray<TArray<FLinearColor>> Lit;
		if (!Show.IsEmpty() && !DrawnRender->Render(World, Show, Views, N, SCS_SceneColorSceneDepth, Lit))
		{
			return;
		}
		// steps along the line no finer than a pixel of the views, so a thin beam leaves no step between its pixels empty
		const int32 Steps = FMath::Clamp(FMath::FloorToInt(L / FMath::Max(L / DrawnLineBins, Views[0].Width / N)), 1, DrawnLineBins);
		TArray<uint8> Bins;
		Bins.SetNumZeroed(Steps);
		double Reach = -1.0;
		int64 KeptN = 0;
		for (int32 v = 0; v < Views.Num() && !Show.IsEmpty(); ++v)
		{
			const FDrawnFrame Cam(Views[v], N);
			for (int32 y = 0; y < N; ++y)
			{
				for (int32 x = 0; x < N; ++x)
				{
					const FLinearColor& C = Lit[v][y * N + x];
					const double Depth = C.A;
					const FVector OnPlane = Cam.Plane(x, y);
					double T = 0.0;
					bool bKeep = false;
					if (FMath::IsFinite(Depth) && Depth < DrawnBackground)
					{
						const FVector At = OnPlane + Cam.Forward * Depth;
						T = FVector::DotProduct(At - A, D);
						bKeep = FVector::DistSquared(At, A + D * FMath::Clamp(T, 0.0, L)) <= R * R;
					}
					else if (Luminance(C.R, C.G, C.B) > DrawnFaint)
					{
						T = FVector::DotProduct(OnPlane - A, D);
						const FVector Off = OnPlane - (A + D * T);
						bKeep = (Off - Cam.Forward * FVector::DotProduct(Off, Cam.Forward)).SizeSquared() <= R * R;
					}
					if (!bKeep || T < 0.0 || T > L)
					{
						continue;
					}
					++KeptN;
					Reach = FMath::Max(Reach, T);
					Bins[FMath::Clamp(FMath::FloorToInt(T / L * Steps), 0, Steps - 1)] = 1;
				}
			}
		}
		int32 Covered = 0;
		for (const uint8 Bin : Bins)
		{
			Covered += Bin;
		}
		V->SetNumberField(TEXT("drawn"), KeptN > 0 ? 1.0 : 0.0);
		V->SetField(TEXT("reach"), KeptN > 0 ? Num(Reach) : Null());
		V->SetNumberField(TEXT("length"), Covered * L / Steps);
		V->SetNumberField(TEXT("pixels"), (double)KeptN);
		V->SetNumberField(TEXT("primitives"), Show.Num());
	}
	Out.SetObjectField(TEXT("value"), V);
}
