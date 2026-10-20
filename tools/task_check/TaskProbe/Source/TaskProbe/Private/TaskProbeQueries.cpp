#include "TaskProbeQueries.h"

#include "AIController.h"
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
#include "Components/LightComponent.h"
#include "Components/LocalLightComponent.h"
#include "Components/MeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Components/ProgressBar.h"
#include "Components/RectLightComponent.h"
#include "Components/RichTextBlock.h"
#include "Components/SkinnedMeshComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/SpotLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextBlock.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/HitResult.h"
#include "Engine/Scene.h"
#include "Engine/Texture.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Interfaces/Interface_PostProcessVolume.h"
#include "Internationalization/Regex.h"
#include "Materials/MaterialInterface.h"
#include "Misc/FileHelper.h"
#include "SceneInterface.h"
#include "SceneView.h"
#include "SceneViewExtension.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UObjectIterator.h"
#include "UObject/UnrealType.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/SViewport.h"
#include "Widgets/Text/STextBlock.h"

namespace TaskProbe
{
static constexpr int32 MaxRows = 200;     // rows per sample of one query
static constexpr int32 MaxQueries = 256;  // queries per play
static constexpr double TraceLength = 200000.0;  // cm, toward a directional light or the sky

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

static bool LightOn(const ULightComponentBase* L, const UWorld* World)
{
	return L && L->GetWorld() == World && !L->HasAnyFlags(RF_ClassDefaultObject | RF_ArchetypeObject) && L->IsRegistered() &&
		L->bAffectsWorld && L->ShouldComponentAddToScene() && L->Intensity > 0.f;
}

static FString OwnerName(const UActorComponent* C)
{
	const AActor* Owner = C ? C->GetOwner() : nullptr;
	return Owner ? Owner->GetName() : (C ? C->GetName() : FString());
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
	static const TSet<FString> Kinds = {TEXT("actors"), TEXT("widgets"), TEXT("light"), TEXT("grading"), TEXT("spawns"), TEXT("camera"), TEXT("components")};
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
			SampleComponents(Q, World, PC, *S);
		}
		else if (Q.Kind == TEXT("camera"))
		{
			SampleCamera(World, PC, *S);
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
	FindActors(World, PC, ParseSel(SelObj ? *SelObj : TSharedPtr<FJsonObject>()), 0, MaxRows, Found, Total);
	TArray<TSharedPtr<FJsonValue>> Rows;
	for (AActor* A : Found)
	{
		const TSharedRef<FJsonObject> Row = MakeShared<FJsonObject>();
		Row->SetStringField(TEXT("name"), A->GetName());
		Row->SetStringField(TEXT("class"), A->GetClass()->GetName());
		for (const FString& F : Q.Fields)
		{
			Row->SetField(F, ActorField(A, F));
		}
		Rows.Add(MakeShared<FJsonValueObject>(Row));
	}
	Out.SetArrayField(TEXT("rows"), Rows);
	if (Total > Rows.Num())
	{
		Out.SetNumberField(TEXT("total"), Total);  // more matched than the rows cap
	}
}

void FTaskProbeQueries::SampleWidgets(FQuery& Q, UWorld* World, FJsonObject& Out)
{
	FString Class, Name, Slate, TextRegex;
	const TSharedPtr<FJsonObject>* SelObj = nullptr;
	if (Q.Def->TryGetObjectField(TEXT("select"), SelObj) && SelObj->IsValid())
	{
		(*SelObj)->TryGetStringField(TEXT("class"), Class);
		(*SelObj)->TryGetStringField(TEXT("name"), Name);
		(*SelObj)->TryGetStringField(TEXT("slate"), Slate);
		(*SelObj)->TryGetStringField(TEXT("text"), TextRegex);
	}
	TArray<TSharedPtr<FJsonValue>> Rows;
	int32 Total = 0;
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
				++Total;
				if (Found.Num() < MaxRows)
				{
					Found.Add(W);
				}
			});
		}
		for (const TSharedRef<SWidget>& W : Found)
		{
			const TSharedRef<FJsonObject> Row = MakeShared<FJsonObject>();
			const FName Tag = W->GetTag();
			Row->SetStringField(TEXT("name"), Tag.IsNone() ? W->GetTypeAsString() : Tag.ToString());
			Row->SetStringField(TEXT("class"), W->GetTypeAsString());
			for (const FString& F : Q.Fields)
			{
				Row->SetField(F, SlateField(W, F));
			}
			Rows.Add(MakeShared<FJsonValueObject>(Row));
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
			if (!W || (!Class.IsEmpty() && !WidgetClassMatches(W, Class, bWithOwners)) || (!Name.IsEmpty() && !W->GetName().MatchesWildcard(Name)))
			{
				return;
			}
			++Total;
			if (Found.Num() < MaxRows)
			{
				Found.AddUnique(W);
			}
		};
		for (UUserWidget* Top : Tops)
		{
			ForEachWidgetDeep(Top, Visit);
		}
		for (UWidget* W : Found)
		{
			const TSharedRef<FJsonObject> Row = MakeShared<FJsonObject>();
			Row->SetStringField(TEXT("name"), W->GetName());
			Row->SetStringField(TEXT("class"), W->GetClass()->GetName());
			for (const FString& F : Q.Fields)
			{
				Row->SetField(F, WidgetField(W, F));
			}
			Rows.Add(MakeShared<FJsonValueObject>(Row));
		}
	}
	Out.SetArrayField(TEXT("rows"), Rows);
	if (Total > Rows.Num())
	{
		Out.SetNumberField(TEXT("total"), Total);
	}
}

void FTaskProbeQueries::SampleComponents(FQuery& Q, UWorld* World, APlayerController* PC, FJsonObject& Out)
{
	TArray<TSharedPtr<FJsonValue>> Rows;
	int32 Total = 0;
	const TSharedPtr<FJsonObject>* SelObj = nullptr;
	Q.Def->TryGetObjectField(TEXT("select"), SelObj);
	const FSel Sel = ParseSel(SelObj ? *SelObj : TSharedPtr<FJsonObject>());
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
			++Total;
			if (Rows.Num() >= MaxRows)
			{
				continue;
			}
			const TSharedRef<FJsonObject> Row = MakeShared<FJsonObject>();
			Row->SetStringField(TEXT("name"), C->GetName());
			Row->SetStringField(TEXT("class"), K->GetName());
			Row->SetStringField(TEXT("owner"), C->GetOwner() ? C->GetOwner()->GetName() : FString());
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
				else if (F.StartsWith(TEXT("prop:")))
				{
					V = ReadProp(C, F.Mid(5));
				}
				Row->SetField(F, V);
			}
			Rows.Add(MakeShared<FJsonValueObject>(Row));
		}
	}
	Out.SetArrayField(TEXT("rows"), Rows);
	if (Total > Rows.Num())
	{
		Out.SetNumberField(TEXT("total"), Total);
	}
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
