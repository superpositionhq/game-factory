// The task checker's (game-factory tools/task_check): the measures a probe play takes (-TaskProbeQueries=<json file>, format game-probe-queries/1), sampled with
// the track (every -TaskProbeEvery seconds, default 0.5) and written to probe.json "measures" as {"<id>": [{"t": t, "rows": [...]} | {"t": t,
// "value": ...}, ...]}. The contract is game-factory's docs/task-probes.md
// (the measures) and docs/task-check.md (how the checker plays and reduces them).
// Query kinds: actors, widgets, light, grading, spawns, camera, components, pieces, screen, audio, ground, ui, drawn. Anything unknown (a class, a
// property, a widget, a kind) gives empty rows or null values and never stops the play.
//
// A select's near ({"point", "radius"}) may also give a height band, "z_min" and/or "z_max" (cm; world heights, or offsets
// from the point's own z with "z_relative": true): a thing matches only when its place is within the radius and the band.
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
//   mesh with several physics bodies by each body's place; 0 with one part, null with none), changed (1 when the actor
//   differs from the first sample it was seen in: one of its mesh components was hidden or shown, removed or added
//   drawn, its world bounds moved more than 1 cm, or a skinned mesh's pose moved: its bones more than 5 cm in all, in
//   its own space, or its local bounds more than 1 cm), bounds_change (cm: the furthest any face of a mesh component's
//   world bounds moved since then, the largest over its components), pose_change (cm: how far its skinned meshes'
//   bones moved since then in their own space, summed; null without a skinned mesh), lit (1 when any of its light
//   sources is lit: a light component that lights the scene, or a drawn mesh component whose emissive luminance is
//   above 0.01), glow (those sources' amounts summed: a light's intensity in candelas times its colour's luminance and
//   its light function's, a mesh's emissive luminance times a quarter of its local bounds' surface in m2). A mesh's
//   emissive is its brightest material's, from the material graphs evaluated with the parameter values now, when every
//   graph evaluates whole; else (a custom node, a texture, any input the graph can only bound, a cooked material) the
//   mesh rendered alone without light from four views (a scene capture showing only it, orthographic, HDR scene colour):
//   lit by its brightest pixel, its luminance over its local bounds box the mean of the four views' summed luminance x
//   pixel area over the box's seen area; the graph's bound when nothing renders (-nullrhi). With either field, the
//   row's "glow_sources" names the kinds lit ("light", "emissive", "unlit") and "glow_read" how its meshes were read
//   ("graph", "render", "bound"). A particle system component (Niagara, Cascade) is a source too: dark unless active and
//   drawn, then rendered alone as such a mesh is (lit by its brightest pixel, glow by the same formula over its local
//   bounds; "effect" in glow_sources), or without a renderer its materials' emissive bound. spin (deg/s): the fastest
//   of its mesh parts' (or, with none, its root's) angular speed in the world (components' spin).
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
//   select.name, select.owner = an actor selection, select.near, select.mesh = a wildcard on a mesh component's mesh
//   asset's name, select.visible = only components drawn, as the visible field reads them); fields count, active, visible, x y z, prop:<path>,
//   speed (cm/s: its physics body's while it simulates, else its own velocity, else how far it moved since the query's
//   previous sample; null the first time it is seen), extent_x|y|z (a primitive's world bounds half-size), simulating
//   (a primitive's physics, as actors'), intensity (a light's), on (a light lights the scene, as light counts it),
//   changed, bounds_change, pose_change (a primitive against the first sample it was seen in, as actors' for one part;
//   pose_change null unless skinned), lit and glow (a light component's, a mesh component's or a particle system's, as
//   actors' for one source; null for any other component; "glow_sources" with them), spin (deg/s: how far the component
//   turned in the world, accumulated every frame since the previous sample, over that time; null the first sample it is
//   seen in unless it simulates physics: then its body's angular velocity). select.effect: true keeps only live effects
//   (an active particle system component, Niagara or Cascade; a drawn decal component), select.class then optional.
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
// - ui: "rows": [{"name", "class", "source", "kind", <field>: value}] for the UI elements on screen in the frame drawn
//   right after the sample, whatever drew them: the Slate tree under the game viewport (UMG widgets are Slate widgets
//   underneath; "source" "umg" when the widget carries UMG's reflection metadata, else "slate"), walked through
//   visible widgets only (a collapsed or hidden widget, or one at render opacity 0, and everything under it is not on
//   screen), and the HUD canvas (AHUD's canvas as it stands when the HUD has drawn, "source" "canvas": every quad and
//   line the frame's DrawText, DrawRect, DrawTexture, DrawTile, DrawLine, K2_DrawBox and canvas items batched, text
//   read back from the glyphs the font cache placed, and digits drawn as seven-segment strokes read back from the
//   lines). kind: "text" (a TextBlock, rich text or editable text with text, a canvas string, digits drawn with
//   strokes), "box" (a drawn border, button, progress bar, colour block, a brush without a resource, a canvas rect),
//   "image" (a brush or canvas quad with a texture or material), "line" (a canvas line; an outline, four lines one
//   after another closing a rectangle, once as its rectangle; strokes read as digits stay lines too). Fields: count
//   (1), text (null but for text), x, y, w, h (viewport fractions). select.kind, select.text (a regex on the text) and select.rect ([x0, y0, x1, y1]: the element's centre
//   inside) choose; "source" and "kind" ride along for the logs. No rows when no frame was drawn. A select of text in
//   a rect (select.rect with select.kind "text", or with select.text) also reads the frame as drawn, UI included,
//   inside the rect (UiOcr): each line of digits, capitals and a few signs it can read for sure, where no element
//   above already reads text, is a text element of "source" "ocr" (name and class "ScreenText"). Other queries take
//   no capture and never see these rows. What a widget paints itself (its own OnPaint, a UMG NativePaint, an engine
//   widget the walk doesn't read) comes from the game window's Slate draw elements (FSlateDebugging's paint events, in
//   any build but Shipping and Test): each element painted under the game viewport while such a widget was the one
//   painting, "source" "paint" (name and class its widget type): a string as text, a box or border as box (image when
//   its brush has a picture texture), a gradient as box, a line or spline as line; elements of the last paint before
//   the frame.
// - drawn: "value": {"drawn", "motion", "base_r", "base_g", "base_b", "base_change", "pixels", "primitives"} for
//   query.near (a point, radius and band), or {"drawn", "reach", "length", "pixels", "primitives"} for query.line
//   ({"from": <Point>, "to": <Point>, "radius": cm}) | null (no renderer, a point that doesn't resolve): every primitive
//   drawn in game whose world bounds reach the place (but one enclosing the whole place and 20 times its size: a sky
//   dome, a room seen from inside) rendered alone (a scene capture showing only them, orthographic: four views from the
//   corners of a tetrahedron, 64 x 64, around a point; two views square to a line, 128 x 128), lit by direct lights and
//   the sky light, without shadows, global illumination, reflections, fog or anything that accumulates over frames, at
//   exposure 1; a pixel is in the place when its depth puts it there, or it is translucent with nothing opaque behind it
//   and its ray crosses the place. drawn: 1 when any pixel is; motion: of the pixels in the place now or at the previous
//   sample, the share that changed (in or out, or its colour c / (1 + c) by more than 1/255 in a channel), null the first
//   sample; base_r/g/b: the rendered base colour (GBuffer, linear) of the opaque pixels in the place, averaged, null with
//   none; base_change: its distance from the first sample's; reach: cm from "from" to the furthest pixel in the place
//   along the line (null with none); length: cm of the line with something drawn by it, in up to 128 steps none finer than a pixel.

#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Engine/World.h"
#include "UObject/ObjectKey.h"

class AActor;
class APawn;
class APlayerController;
class AHUD;
class FTaskProbeViewExtension;
class FViewport;
class UCanvas;
class UButton;
class USceneComponent;
class SWidget;
class FSlateWindowElementList;
class FPaintArgs;
class FSlateRect;
struct FGeometry;
struct FSlateDebuggingElementTypeAddedEventArgs;

namespace TaskProbe
{
class FGlowRender;
class FDrawnRender;

/** A point of the game viewport, in viewport fractions 0-1, in Slate's absolute (desktop) space. */
bool ViewportPoint(double Fx, double Fy, FVector2D& OutAbsolute);
/** The first enabled, visible UMG button in the viewport whose name (wildcard) or class matches. */
UButton* FindButton(UWorld* World, const FString& Want);
/** Where teleport_to puts the pawn: Distance cm from the nearest actor Select matches (nearest to the pawn), on the
 *  pawn's side of it (level, plus Offset), and the yaw that faces Face (a point, as a query's) or else that actor. */
bool TeleportSpot(UWorld* World, APlayerController* PC, const TSharedPtr<FJsonObject>& Select, double Distance, const FVector& Offset,
	const TSharedPtr<FJsonObject>& Face, FVector& OutLocation, double& OutYaw, FString& OutName);

/** One element of the UI on screen (ui): its source (umg, slate, canvas), kind (text, box, image), name and class (for
 *  the logs), text, and its rectangle in viewport fractions. */
struct FUiElement
{
	FString Source;
	FString Kind;
	FString Name;
	FString Class;
	FString Text;
	bool bHasRect = false;
	double X = 0.0, Y = 0.0, W = 0.0, H = 0.0;
};

/** An element a widget painted itself (ui, source "paint"): its draw element's type and index in the game window's
 *  element list, and the type of the widget that was painting it. */
struct FPaintRecord
{
	uint8 Type = 0;
	int32 Index = 0;
	FName Widget;
};

/** A component whose rotation spin follows: where it was turned at the last frame, and how far it turned (radians)
 *  over how long (s) since the last sample. */
struct FSpinTrack
{
	TWeakObjectPtr<const USceneComponent> Component;
	FQuat Last = FQuat::Identity;
	double Angle = 0.0;
	double Time = 0.0;
};

/** A drawn part (a primitive component) as changed compares it: drawn or not, its world bounds and, of a skinned
 *  mesh, its local bounds and its bones' places in its own space. */
struct FPartState
{
	bool bDrawn = false;
	bool bSkinned = false;
	FBox World = FBox(ForceInit);
	FBox Local = FBox(ForceInit);
	TArray<FVector> Bones;
};
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
	/** A screen or ui sample waits for the next frame the game viewport draws. */
	bool WaitsForFrame() const { return bWantFrame || bWantUi; }
	/** Every frame of the play (the clock running or held): spin's components turn by so much since the last frame. */
	void Frame(float DeltaTime);

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
		TMap<FObjectKey, TaskProbe::FPartState> Firsts;  // changed: each part as the first sample it was seen in had it
		TMap<FObjectKey, TArray<FObjectKey>> FirstParts;  // changed (actors): each actor's parts at its first sample
		double LastT = 0.0;
		TArray<TSharedPtr<FJsonObject>> Pending;  // screen, ui: samples waiting for the next drawn frame
		bool bOcr = false;  // ui: a select of text in a rect, read from the frame as drawn too (UiOcr)
		TArray<FLinearColor> DrawnColour;  // drawn: the previous sample's views, pixel by pixel (motion)
		TArray<uint8> DrawnKept;  // drawn: which of those pixels were in the place
		bool bDrawnBefore = false;  // drawn: a previous sample was rendered
		bool bDrawnFirstBase = false;  // drawn: the first sample's mean base colour is known (base_change)
		FVector DrawnFirstBase = FVector::ZeroVector;
		TArray<TSharedPtr<FJsonValue>> Samples;
	};

	void Hook(UWorld* World);
	void Unhook();
	void OnWorldInit(UWorld* World, const UWorld::InitializationValues IVS);
	void OnSpawned(AActor* Actor);
	void OnDestroyed(AActor* Actor);
	void OnViewportRendered(FViewport* Viewport);
	void ReadScreen(FViewport* Viewport);
	void OnHudPostRender(AHUD* Hud, UCanvas* DebugCanvas);
	void FillUi();

	void SampleActors(FQuery& Q, UWorld* World, APlayerController* PC, FJsonObject& Out);
	void SampleWidgets(FQuery& Q, UWorld* World, FJsonObject& Out);
	void SampleLight(FQuery& Q, UWorld* World, APlayerController* PC, FJsonObject& Out);
	void SampleGrading(FQuery& Q, UWorld* World, APlayerController* PC, FJsonObject& Out);
	void SampleComponents(FQuery& Q, UWorld* World, APlayerController* PC, double T, FJsonObject& Out);
	void SamplePieces(FQuery& Q, UWorld* World, APlayerController* PC, FJsonObject& Out);
	void SampleAudio(FQuery& Q, UWorld* World, APlayerController* PC, FJsonObject& Out);
	void SampleGround(FQuery& Q, UWorld* World, APlayerController* PC, FJsonObject& Out);
	void SampleCamera(UWorld* World, APlayerController* PC, FJsonObject& Out);
	void SampleDrawn(FQuery& Q, UWorld* World, APlayerController* PC, FJsonObject& Out);
	TSharedPtr<FJsonValue> SpinOf(const USceneComponent* C);
	TSharedPtr<FJsonValue> ActorSpin(const AActor* A);
	void OnPaintBeginWindow(const FSlateWindowElementList& List);
	void OnPaintEndWindow(const FSlateWindowElementList& List);
	void OnPaintBeginWidget(const SWidget* Widget, const FPaintArgs& Args, const FGeometry& Geometry, const FSlateRect& Culling, const FSlateWindowElementList& List, int32 Layer);
	void OnPaintEndWidget(const SWidget* Widget, const FSlateWindowElementList& List, int32 Layer);
	void OnPaintElement(const FSlateDebuggingElementTypeAddedEventArgs& Args);

	TArray<FQuery> Queries;
	TArray<FString> ErrorList;
	bool bHasSpawns = false;
	TWeakObjectPtr<UWorld> HookedWorld;
	FDelegateHandle SpawnHandle;
	FDelegateHandle DestroyHandle;
	FDelegateHandle WorldInitHandle;
	FDelegateHandle ViewportHandle;  // only with a screen query
	bool bWantFrame = false;  // a screen sample waits for the next drawn frame
	FDelegateHandle HudHandle;  // only with a ui query
	bool bWantUi = false;  // a ui sample waits for the next drawn frame
	TArray<TaskProbe::FUiElement> CanvasNow;  // ui: what the HUD canvas held when the HUD had drawn
	uint64 CanvasFrame = 0;  // ui: the frame (GFrameCounter) CanvasNow is of
	TSharedPtr<FTaskProbeViewExtension, ESPMode::ThreadSafe> ViewExtension;
	TUniquePtr<TaskProbe::FGlowRender> GlowRender;  // lit, glow: meshes whose emissive is read as rendered
	TUniquePtr<TaskProbe::FDrawnRender> DrawnRender;  // drawn: what is drawn in a place, rendered
	TMap<FObjectKey, TaskProbe::FSpinTrack> Spins;  // spin: the components read last sample, their turning since
	TSet<FObjectKey> SpinRead;  // spin: the components read this sample
	// ui: the elements widgets paint themselves, from the game window's Slate draw elements (only with a ui query)
	FDelegateHandle PaintHandles[5];
	const FSlateWindowElementList* PaintList = nullptr;  // the game window's element list while it is painted
	TArray<const SWidget*> PaintStack;  // the widgets painting, outermost first
	int32 PaintViewportAt = INDEX_NONE;  // where the game viewport widget is in PaintStack
	FVector2D PaintViewPos = FVector2D::ZeroVector, PaintViewSize = FVector2D::ZeroVector;  // its paint rect (window space)
	TArray<TaskProbe::FPaintRecord> PaintRecords;  // what was painted under it this paint
	TArray<TaskProbe::FUiElement> PaintNow;  // the last paint's elements, as ui elements
	uint64 PaintFrame = 0;  // the frame (GFrameCounter) PaintNow is of
};
