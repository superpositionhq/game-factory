// The task checker's (game-factory tools/task_check): the measures a probe play takes (-TaskProbeQueries=<json file>, format game-probe-queries/1), sampled with
// the track (every -TaskProbeEvery seconds, default 0.5) and written to probe.json "measures" as {"<id>": [{"t": t, "rows": [...]} | {"t": t,
// "value": ...}, ...]}. The contract is game-factory's docs/task-probes.md
// (the measures) and docs/task-check.md (how the checker plays and reduces them).
// Query kinds: actors, widgets, light, grading, spawns, camera, components, pieces, screen. Anything unknown (a class, a property, a
// widget, a kind) gives empty rows or null values and never stops the play.
//
// Rows are capped at 200 per sample, never the counts: "total" is how many matched, and when more matched than the
// rows hold, "full": {"<field>": {"n", "nonzero", "sum", "min", "max"}} sums up every match's numeric value of each field
// (n: how many have a number), so a count, a sum, a min or a max over a selection reads every match.
//
// What each sample holds:
// - actors: "rows": [{"name", "class", <field>: value, ...}] for at most 200 matching actors ("total" and "full" when more
//   matched). Fields: count (1), x y z, yaw pitch roll (degrees in (-180, 180]), scale (mean of |scale x|, |y|, |z|), extent_x|y|z (components'
//   bounding box half-size), hidden, collision, speed, prop:<path> (null when the path doesn't resolve; arrays without
//   an index give their length; Materials[i] on a primitive component is its effective material i),
//   bone:<Component>.<BoneOrSocket>.x|y|z (world location; null when the bone or socket doesn't exist),
//   rel_yaw:<Component> (component yaw minus actor yaw), world_yaw|world_pitch|world_roll:<Component> (the component's
//   own rotation in the world, degrees in (-180, 180]), forward:<Component>.x|y|z (its forward unit vector in the world:
//   for a light, the way its light travels), facing_vs_velocity (degrees between forward and velocity, null
//   under 10 cm/s), bb:<Key> (an AI controller's, or a pawn's AI controller's, blackboard value).
// - widgets: "rows": [{"name", "class", <field>: value}] over the UMG trees in the viewport. select.class alone matches
//   the widget's own class; with select.name it also matches an enclosing user widget's class. visible = visible,
//   render opacity > 0, and every parent (through enclosing user widgets) the same. x, y, w, h: the cached geometry in
//   viewport fractions; brush: the path of an Image's brush resource. With select.slate (a Slate type name, wildcard)
//   and optional select.text (a regex on STextBlock text) the Slate tree under the game viewport is walked instead
//   (rows named by the widget's tag, else its type; fields visible, text, x/y/w/h, has_brush/brush for SImage).
// - light: "value": {"illuminance" (lux), "exposure" (scale, null until the renderer has one), "brightness"
//   (illuminance * exposure, or null), "local", "directional", "sky" (the parts), "lights" (how many contributed),
//   "point": [x, y, z]} or null when the point doesn't resolve. Exposure is the player's view's
//   FSceneView::GetLastEyeAdaptationExposure (its view state's read-back eye adaptation), seen from a scene view
//   extension. The sky light adds intensity * colour luminance * the open share of 9 upward traces.
// - grading: "value": {"source" ("view": the renderer's final settings for the player's view; "volumes": blended here
//   before the first frame), "white_temp", "white_tint", "saturation", "contrast", "gamma", "gain", "offset" ([x, y,
//   z, w] global), "auto_exposure_bias", "auto_exposure_min", "auto_exposure_max", "auto_exposure_method" (enum
//   index), "lut" (path or null), "lut_intensity", "sun": {"name", "color" (linear rgb), "temperature",
//   "use_temperature", "intensity", "lit_color" (colour times the engine's temperature colour when used)} | null,
//   "sky": {"name", "color", "intensity"} | null, "fog": {"name", "density", "inscattering" (linear rgb)} | null, "post:<Property>[.<Sub>]": every post: name in
//   the query's fields, read by reflection from the same settings (or blended here from the volumes' bOverride_ flags
//   and weights before the first frame)}.
// - spawns: "value": {"spawned", "destroyed"} counted since the play started (any actor of the class, also level ones
//   destroyed).
// - camera: "value": {"distance", "height" (camera relative to the pawn's location, cm), "pitch", "yaw", "fov",
//   "occluded", "pawn_on_screen"} (the pawn fields null without a pawn), the pawn's centre being its colliding
//   components' bounds centre.
// - components: "rows": [{"name", "class", "owner", <field>}] for registered components of select.class (optionally
//   select.name, select.owner = an actor selection, select.near); fields count, active, visible, x y z, prop:<path>.
// - pieces: "value": {"count", "visible", "components", "actors", "triangles", "visible_triangles"}: the placed mesh
//   pieces of the registered mesh components select.class matches (default every mesh component; also select.name,
//   select.mesh = a wildcard on the mesh asset's name, select.owner, select.near), counted over all of them whatever
//   their form: a static or skeletal mesh component with a mesh is 1, an instanced (ISM, HISM, foliage) component one
//   per instance, a procedural mesh component one per section with triangles. near tests each piece's own place (an
//   instance's, a section's bounds centre). visible: the pieces drawn in game (component visible, not hidden in game,
//   owner not hidden, section visible); components, actors: how many components and owner actors the pieces come
//   from; triangles, visible_triangles: the triangles those pieces (those drawn) hold: a static mesh's LOD0 (a Nanite
//   mesh's own triangles), times the instances of an instanced one, a skeletal mesh's LOD0, a procedural mesh
//   section's index count / 3; any other mesh component 0. Widget components, editor-only components and empty meshes
//   count nothing.
// - screen: "value": {"luminance", "luma", "pixels", "size": [w, h]} | null: the frame the player's viewport drew right
//   after the sample (after post-processing and tone mapping, the HUD canvas included, the UMG and Slate UI not), over
//   query.rect = [x0, y0, x1, y1] (viewport fractions, default the whole frame): luminance = mean linear Rec. 709
//   luminance of the displayed pixels (sRGB decoded, 0-1), luma = mean Rec. 709 luma of the encoded values (0-1).
//   null when no frame was drawn (the play ended first, or nothing renders).

#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Engine/World.h"

class AActor;
class APawn;
class APlayerController;
class FTaskProbeViewExtension;
class FViewport;
class UButton;

namespace TaskProbe
{
/** A point of the game viewport, in viewport fractions 0-1, in Slate's absolute (desktop) space. */
bool ViewportPoint(double Fx, double Fy, FVector2D& OutAbsolute);
/** The first enabled, visible UMG button in the viewport whose name (wildcard) or class matches. */
UButton* FindButton(UWorld* World, const FString& Want);
}

class FTaskProbeQueries
{
public:
	FTaskProbeQueries();
	~FTaskProbeQueries();

	/** Reads the queries file; problems go to Errors(). */
	void Load(const FString& Path);
	/** Takes one sample of every query at play time T (seconds). */
	void Sample(UWorld* World, APlayerController* PC, double T);
	/** {"<id>": [samples...]} for probe.json. */
	TSharedRef<FJsonObject> MeasuresJson() const;
	const TArray<FString>& Errors() const { return ErrorList; }
	/** A screen sample waits for the next frame the game viewport draws. */
	bool WaitsForFrame() const { return bWantFrame; }

private:
	struct FQuery
	{
		FString Id;
		FString Kind;
		TSharedPtr<FJsonObject> Def;
		TArray<FString> Fields;
		FString SpawnClass;
		int32 Spawned = 0;
		int32 Destroyed = 0;
		double Rect[4] = {0.0, 0.0, 1.0, 1.0};  // screen: [x0, y0, x1, y1] in viewport fractions
		TArray<TSharedPtr<FJsonObject>> Pending;  // screen: samples waiting for the next drawn frame
		TArray<TSharedPtr<FJsonValue>> Samples;
	};

	void Hook(UWorld* World);
	void Unhook();
	void OnWorldInit(UWorld* World, const UWorld::InitializationValues IVS);
	void OnSpawned(AActor* Actor);
	void OnDestroyed(AActor* Actor);
	void OnViewportRendered(FViewport* Viewport);

	void SampleActors(FQuery& Q, UWorld* World, APlayerController* PC, FJsonObject& Out);
	void SampleWidgets(FQuery& Q, UWorld* World, FJsonObject& Out);
	void SampleLight(FQuery& Q, UWorld* World, APlayerController* PC, FJsonObject& Out);
	void SampleGrading(FQuery& Q, UWorld* World, APlayerController* PC, FJsonObject& Out);
	void SampleComponents(FQuery& Q, UWorld* World, APlayerController* PC, FJsonObject& Out);
	void SamplePieces(FQuery& Q, UWorld* World, APlayerController* PC, FJsonObject& Out);
	void SampleCamera(UWorld* World, APlayerController* PC, FJsonObject& Out);

	TArray<FQuery> Queries;
	TArray<FString> ErrorList;
	bool bHasSpawns = false;
	TWeakObjectPtr<UWorld> HookedWorld;
	FDelegateHandle SpawnHandle;
	FDelegateHandle DestroyHandle;
	FDelegateHandle WorldInitHandle;
	FDelegateHandle ViewportHandle;  // only with a screen query
	bool bWantFrame = false;  // a screen sample waits for the next drawn frame
	TSharedPtr<FTaskProbeViewExtension, ESPMode::ThreadSafe> ViewExtension;
};
