// The task checker's (game-factory tools/task_check): the measures a probe play takes (-TaskProbeQueries=<json file>, format game-probe-queries/1), sampled with
// the track (every -TaskProbeEvery seconds, default 0.5) and written to probe.json "measures" as {"<id>": [{"t": t, "rows": [...]} | {"t": t,
// "value": ...}, ...]}. The contract is game-factory's docs/task-probes.md
// (the measures) and docs/task-check.md (how the checker plays and reduces them).
// Query kinds: actors, widgets, light, grading, spawns, camera, components, pieces, screen, audio, ground. Anything unknown (a class, a property, a
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
//   under 10 cm/s), bb:<Key> (an AI controller's, or a pawn's AI controller's, blackboard value), simulating (1 when any
//   of its primitive components simulates physics: its own body or a skeletal mesh's body), spread (how far apart its
//   geometry's parts are: the diagonal of the box around the centres of the mesh components extent_ counts, a skeletal
//   mesh with several physics bodies by each body's place; 0 with one part, null with none).
// - widgets: "rows": [{"name", "class", <field>: value}] over the UMG trees in the viewport. select.class alone matches
//   the widget's own class; with select.name it also matches an enclosing user widget's class. visible = visible,
//   render opacity > 0, and every parent (through enclosing user widgets) the same. x, y, w, h: the cached geometry in
//   viewport fractions; brush: the path of an Image's brush resource. With select.slate (a Slate type name, wildcard)
//   and optional select.text (a regex on STextBlock text) the Slate tree under the game viewport is walked instead
//   (rows named by the widget's tag, else its type; fields visible, text, x/y/w/h, has_brush/brush for SImage).
//   select.visible: true keeps only the widgets the visible field reads 1 for (a collapsed or hidden one, or one under
//   such a parent, is not selected), UMG or Slate.
// - light: "value": {"illuminance" (lux), "exposure" (scale, null until the renderer has one), "brightness"
//   (illuminance * exposure, or null), "local", "directional", "sky" (the parts), "lights" (how many contributed),
//   "point": [x, y, z]} or null when the point doesn't resolve. Exposure is the player's view's
//   FSceneView::GetLastEyeAdaptationExposure (its view state's read-back eye adaptation), seen from a scene view
//   extension. The sky light adds intensity * colour luminance * the open share of 9 upward traces. A light counts when
//   the renderer draws it: registered, affecting the world, visible, not hidden in game, its owner not hidden, of an
//   intensity above 0 (grading's sun and sky the same).
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
//   select.name, select.owner = an actor selection, select.near); fields count, active, visible, x y z, prop:<path>,
//   speed (cm/s: its physics body's while it simulates, else its own velocity, else how far it moved since the query's
//   previous sample; null the first time it is seen), extent_x|y|z (a primitive's world bounds half-size), simulating
//   (a primitive's physics, as actors'), intensity (a light's), on (a light lights the scene, as light counts it).
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
// - audio: "value": {"count", "audible", "volume", "max_volume", "loudest"} | null: the audio device's active sounds
//   (null without an audio device: a play under -nosound) that select matches (select.sound: a wildcard on the sound
//   asset's name, select.sound_class: on its sound class's or a parent class's name, select.owner: an actor selection
//   its owner is in), each at its volume at the listener: its wave instances' volume (its own, its class's and mixes',
//   multipliers) times their distance and occlusion attenuation and dynamic volume, summed, the output's primary
//   volume left out. count: how many; audible: how many at 0.001 (-60 dB) or more; volume: their sum; max_volume and
//   loudest (its sound's name): the loudest one.
// - ground: "value": {"height", "hit"} for query.xy = [x, y], or {"min", "max", "mean", "range", "hits", "points"}
//   for query.box = [x0, y0, x1, y1] on a query.grid x grid lattice (2-32, default 8; corners and edges included):
//   the z (cm) where a trace straight down from 2 km up meets the ground first (the visibility channel, complex
//   collision, every pawn ignored; with query.select, only an actor that actor selection matches counts, the rest are
//   traced through); null heights (and min/max/mean/range) where nothing was hit.

#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Engine/World.h"
#include "UObject/ObjectKey.h"

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
/** Where teleport_to puts the pawn: Distance cm from the nearest actor Select matches (nearest to the pawn), on the
 *  pawn's side of it (level, plus Offset), and the yaw that faces Face (a point, as a query's) or else that actor. */
bool TeleportSpot(UWorld* World, APlayerController* PC, const TSharedPtr<FJsonObject>& Select, double Distance, const FVector& Offset,
	const TSharedPtr<FJsonObject>& Face, FVector& OutLocation, double& OutYaw, FString& OutName);
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
		double Ground[4] = {0.0, 0.0, 0.0, 0.0};  // ground: [x0, y0, x1, y1] (cm; a point: x0 = x1, y0 = y1)
		bool bGroundBox = false;  // ground: a box sampled on a grid, else one point
		int32 Grid = 8;  // ground: grid x grid points over the box (0: the query gave no place)
		TMap<FObjectKey, FVector> LastPlaces;  // components: each one's place at the previous sample (for speed)
		double LastT = 0.0;
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
	void SampleComponents(FQuery& Q, UWorld* World, APlayerController* PC, double T, FJsonObject& Out);
	void SamplePieces(FQuery& Q, UWorld* World, APlayerController* PC, FJsonObject& Out);
	void SampleAudio(FQuery& Q, UWorld* World, APlayerController* PC, FJsonObject& Out);
	void SampleGround(FQuery& Q, UWorld* World, APlayerController* PC, FJsonObject& Out);
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
