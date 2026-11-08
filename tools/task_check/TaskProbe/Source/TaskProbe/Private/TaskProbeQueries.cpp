#include "TaskProbeQueries.h"

#include "ActiveSound.h"
#include "AIController.h"
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
#include "Blueprint/UserWidget.h"
#include "Blueprint/WidgetTree.h"
#include "Camera/PlayerCameraManager.h"
#include "CollisionQueryParams.h"
#include "Components/ActorComponent.h"
#include "Components/Button.h"
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
#include "Components/SkeletalMeshComponent.h"
#include "Components/SkinnedMeshComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/SpotLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextBlock.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/HitResult.h"
#include "Engine/Scene.h"
#include "Engine/SkinnedAsset.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Interfaces/Interface_PostProcessVolume.h"
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
#include "Misc/FileHelper.h"
#include "PhysicsEngine/BodyInstance.h"
#include "Rendering/SkeletalMeshLODRenderData.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "SceneInterface.h"
#include "SceneView.h"
#include "SceneViewExtension.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundClass.h"
#include "UObject/ObjectKey.h"
#include "UObject/UObjectIterator.h"
#include "UObject/UnrealType.h"
#include "UnrealClient.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/SViewport.h"
#include "Widgets/Text/STextBlock.h"

namespace TaskProbe
{
static constexpr int32 MaxRows = 200;     // rows per sample of one query
static constexpr int32 MaxQueries = 256;  // queries per play
static constexpr double TraceLength = 200000.0;  // cm, toward a directional light or the sky
static constexpr double AudibleVolume = 0.001;  // audio: a sound at least this loud at the listener (-60 dB) is audible

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

struct FSel
{
	FString Class, Tag, Name;
	bool bPlayer = false;
	TSharedPtr<FJsonObject> NearPoint;
	double Radius = 0.0;
};

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
	O->TryGetBoolField(TEXT("player"), S.bPlayer);
	const TSharedPtr<FJsonObject>* Near = nullptr;
	if (O->TryGetObjectField(TEXT("near"), Near) && Near->IsValid())
	{
		const TSharedPtr<FJsonObject>* Point = nullptr;
		if ((*Near)->TryGetObjectField(TEXT("point"), Point))
		{
			S.NearPoint = *Point;
		}
		else
		{
			S.NearPoint = MakeShared<FJsonObject>();  // a near without a point matches nothing
		}
		(*Near)->TryGetNumberField(TEXT("radius"), S.Radius);
	}
	return S;
}

static APawn* PlayerPawn(APlayerController* PC) { return PC ? PC->GetPawn() : nullptr; }

static bool ResolvePoint(const TSharedPtr<FJsonObject>& P, UWorld* World, APlayerController* PC, int32 Depth, FVector& Out);

/** The actors a selection matches (Out holds at most Limit; Total counts them all). */
static void FindActors(UWorld* World, APlayerController* PC, const FSel& S, int32 Depth, int32 Limit, TArray<AActor*>& Out, int32& Total)
{
	Total = 0;
	if (!World)
	{
		return;
	}
	FVector NearP = FVector::ZeroVector;
	const bool bNear = S.NearPoint.IsValid();
	if (bNear && !ResolvePoint(S.NearPoint, World, PC, Depth + 1, NearP))
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
		if (bNear && FVector::Dist(A->GetActorLocation(), NearP) > S.Radius)
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
	return Null();
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

bool TeleportSpot(UWorld* World, APlayerController* PC, const TSharedPtr<FJsonObject>& Select, double Distance, const FVector& Offset,
	const TSharedPtr<FJsonObject>& Face, FVector& OutLocation, double& OutYaw, FString& OutName)
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
static constexpr uint8 GlowLight = 1, GlowEmissive = 2, GlowUnlit = 4;  // glow_sources

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

/** An input the reading can't evaluate (a texture, vertex colour, time, a custom node): at most white. */
static FRange Unknown() { return FRange::Of(0.0, 1.0, 4); }

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
};

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
		return Unknown();
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
		return X->Declaration ? EvalOr(G, X->Declaration->Input, Call, 0.0) : Unknown();
	}
	if (const UMaterialExpressionMaterialFunctionCall* X = Cast<UMaterialExpressionMaterialFunctionCall>(E))
	{
		const UMaterialExpressionFunctionOutput* Out = X->FunctionOutputs.IsValidIndex(OutputIndex) ? X->FunctionOutputs[OutputIndex].ExpressionOutput.Get() : nullptr;
		const FGraphCall Inner{X, Call};
		return Out ? EvalOr(G, Out->A, &Inner, 0.0) : Unknown();
	}
	if (const UMaterialExpressionFunctionInput* X = Cast<UMaterialExpressionFunctionInput>(E))
	{
		return FunctionInputValue(G, X, Call);
	}
	if (const UMaterialExpressionFunctionOutput* X = Cast<UMaterialExpressionFunctionOutput>(E))
	{
		return EvalOr(G, X->A, Call, 0.0);
	}
	return Unknown();
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
		return Unknown();
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
		return Unknown();
	}
	if (const UMaterialExpressionMakeMaterialAttributes* X = Cast<UMaterialExpressionMakeMaterialAttributes>(E))
	{
		return EvalOr(G, X->EmissiveColor, Call, 0.0);
	}
	if (const UMaterialExpressionBlendMaterialAttributes* X = Cast<UMaterialExpressionBlendMaterialAttributes>(E))
	{
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
		return X->Declaration ? EmissiveOf(G, X->Declaration->Input, Call) : Unknown();
	}
	if (const UMaterialExpressionMaterialFunctionCall* X = Cast<UMaterialExpressionMaterialFunctionCall>(E))
	{
		const UMaterialExpressionFunctionOutput* Out = X->FunctionOutputs.IsValidIndex(In.OutputIndex) ? X->FunctionOutputs[In.OutputIndex].ExpressionOutput.Get() : nullptr;
		const FGraphCall Inner{X, Call};
		return Out ? EmissiveOf(G, Out->A, &Inner) : Unknown();
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
	return Unknown();  // SetMaterialAttributes and other attribute nodes
}
#endif  // WITH_EDITORONLY_DATA

/** A material's emissive from its graph (editor-only data, there in an uncooked -game play): the base material's
 *  emissive input evaluated with the instance's parameter values now. False without the graph (a cooked build). */
static bool GraphEmissive(const UMaterialInterface* MI, const UPrimitiveComponent* Prim, const UWorld* World, double& Out)
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

/** A material's emissive luminance now: from its graph, else by its parameters' names; false when neither can say. */
static bool MaterialEmissive(const UMaterialInterface* MI, const UPrimitiveComponent* Prim, const UWorld* World, double& Out)
{
	return GraphEmissive(MI, Prim, World, Out) || NamedEmissive(MI, Out);
}

/** lit and glow of one actor or component, summed over its sources (lights and meshes). */
struct FGlowReading
{
	bool bRead = false;  // it was read (else lit and glow are null)
	bool bLit = false;
	double Glow = 0.0;
	uint8 Kinds = 0;  // GlowLight | GlowEmissive | GlowUnlit: the sources that are lit
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

/** A mesh component as a source: its brightest material's emissive luminance (every material it draws with: its own,
 *  overrides and dynamic instances with their parameters now, its overlay). Lit when it is drawn (visible, not hidden
 *  in game, its owner not hidden) and that is above EmissiveFloor; glow that luminance times a quarter of the surface
 *  of its local bounds (m2, scaled), the candelas a lamp that size would give every way. False when no material could
 *  be read. */
static bool AddMesh(FGlowReading& R, const UMeshComponent* M, const UWorld* World)
{
	TArray<UMaterialInterface*> Used;
	M->GetUsedMaterials(Used);
	bool bRead = Used.IsEmpty();
	double Best = 0.0;
	bool bUnlit = false;
	for (const UMaterialInterface* MI : Used)
	{
		double L = 0.0;
		if (!MI)
		{
			bRead = true;
		}
		else if (MaterialEmissive(MI, M, World, L))
		{
			bRead = true;
			if (L > Best)
			{
				Best = L;
				bUnlit = MI->GetShadingModels().HasOnlyShadingModel(MSM_Unlit);
			}
		}
	}
	if (!bRead)
	{
		return false;
	}
	R.bRead = true;
	const AActor* Owner = M->GetOwner();
	const bool bDrawn = M->IsRegistered() && M->IsVisible() && !M->bHiddenInGame && !(Owner && Owner->IsHidden());
	if (!bDrawn || Best <= EmissiveFloor)
	{
		return true;
	}
	const FVector Size = M->CalcBounds(FTransform::Identity).BoxExtent * 2.0 * M->GetComponentTransform().GetScale3D().GetAbs();
	const double Area = 2.0 * (Size.X * Size.Y + Size.Y * Size.Z + Size.Z * Size.X) / 10000.0;
	R.bLit = true;
	R.Glow += Best * Area / 4.0;
	R.Kinds |= bUnlit ? GlowUnlit : GlowEmissive;
	return true;
}

/** An actor's sources: its own registered light components and the mesh components changed compares (ChangeParts). */
static FGlowReading ActorGlow(const AActor* A, const UWorld* World)
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
		bUnread |= !AddMesh(R, M, World);
	}
	R.bRead = R.bLit || !bUnread;
	return R;
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
	return FString::Join(Kinds, TEXT(","));
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
		TEXT("pieces"), TEXT("screen"), TEXT("audio"), TEXT("ground")};
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
		if (Q.Fields.Num() == 0 && (Q.Kind == TEXT("actors") || Q.Kind == TEXT("widgets") || Q.Kind == TEXT("components")))
		{
			Q.Fields.Add(TEXT("count"));
		}
		if (Q.Kind == TEXT("spawns"))
		{
			Q.Def->TryGetStringField(TEXT("class"), Q.SpawnClass);
			bHasSpawns = true;
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
			SampleAudio(Q, World, PC, *S);
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
		const FGlowReading Glow = bGlow ? ActorGlow(A, World) : FGlowReading();
		for (const FString& F : Q.Fields)
		{
			const TSharedPtr<FJsonValue> V = IsChangeField(F) ? ChangeField(Change, F) : IsGlowField(F) ? GlowField(Glow, F) : ActorField(A, F);
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
	// mesh: a wildcard on a mesh component's mesh asset; visible: only components drawn (as the visible field reads them)
	FString MeshSel;
	bool bDrawnOnly = false;
	if (SelObj && SelObj->IsValid())
	{
		(*SelObj)->TryGetStringField(TEXT("mesh"), MeshSel);
		(*SelObj)->TryGetBoolField(TEXT("visible"), bDrawnOnly);
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
	if (bOk && Sel.NearPoint.IsValid() && !ResolvePoint(Sel.NearPoint, World, PC, 1, NearP))
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
			if (Sel.NearPoint.IsValid() && (!SC || FVector::Dist(SC->GetComponentLocation(), NearP) > Sel.Radius))
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
			AddMesh(Glow, Mesh, World);
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
	const bool bNear = Sel.NearPoint.IsValid();
	if (bNear && !ResolvePoint(Sel.NearPoint, World, PC, 1, NearP))
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
			if (bNear && FVector::Dist(Where, NearP) > Sel.Radius)
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
	if (!bWantFrame || !Viewport || !GVC || GVC->Viewport != Viewport)
	{
		return;
	}
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

void FTaskProbeQueries::SampleAudio(FQuery& Q, UWorld* World, APlayerController* PC, FJsonObject& Out)
{
	// what the player hears: the audio device's active sounds, each at its volume at the listener (the player's camera,
	// or whatever the game listens from): its wave instances' volume (the sound's own, its class's and mixes', the
	// game's multipliers) times their distance and occlusion attenuation and dynamic volume, summed. The output's
	// primary volume (the play's -muteaudio, an unfocused window) is left out.
	FAudioDevice* Device = World ? World->GetAudioDeviceRaw() : nullptr;
	if (!Device)
	{
		Out.SetField(TEXT("value"), Null());  // no audio device (-nosound): nothing is heard, so nothing is measured
		return;
	}
	FString Sound, SoundClass;
	TSet<FObjectKey> Owners;
	bool bOwner = false;
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
	}
	struct FHeard
	{
		FString Sound;
		TArray<FString> Classes;  // its sound class and the parents of it
		FObjectKey Owner;
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
			for (const USoundClass* K = Active->GetSoundClass(); K && H.Classes.Num() < 16; K = K->ParentClass)
			{
				H.Classes.Add(K->GetName());
			}
			H.Owner = Active->GetOwnerKey();
			for (const TPair<UPTRINT, FWaveInstance*>& W : Active->GetWaveInstances())
			{
				if (W.Value)
				{
					H.Volume += W.Value->GetVolumeWithDistanceAndOcclusionAttenuation() * W.Value->GetDynamicVolume();
				}
			}
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
		if ((!Sound.IsEmpty() && !H.Sound.MatchesWildcard(Sound)) || (bOwner && !Owners.Contains(H.Owner)) ||
			(!SoundClass.IsEmpty() && !H.Classes.ContainsByPredicate([&](const FString& K) { return K.MatchesWildcard(SoundClass); })))
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
