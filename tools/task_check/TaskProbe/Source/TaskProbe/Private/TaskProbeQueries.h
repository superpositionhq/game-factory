// The task checker's (game-factory tools/task_check): the measures a probe play takes (-TaskProbeQueries=<json file>, format game-probe-queries/1), sampled with
// the track (every -TaskProbeEvery seconds, default 0.5) and written to probe.json "measures" as {"<id>": [{"t": t, "rows": [...]} | {"t": t,
// "value": ...}, ...]}. The contract is game-factory's docs/task-probes.md
// (the measures) and docs/task-check.md (how the checker plays and reduces them).
// Query kinds: actors, widgets, light, grading, spawns, camera, components, pieces, screen, audio, ground, ui, drawn, world, render, pad,
// nav. Anything unknown (a class, a
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
//   of its mesh parts' (or, with none, its root's) angular speed in the world (components' spin). frozen (s): the
//   longest stop that ended since the previous sample: frames in which it moved under 0.1 cm and no bone of its
//   skinned meshes (in component space) moved 0.1 cm, between two frames of motion, 0.5 s at most (a hit stop however
//   made; an idle, a rest or a static actor reads 0), null the first sample it is seen in; montage (1 while
//   an anim montage plays on one of its skeletal meshes); damage_taken (what its TakeDamage returned for the play's
//   staged damage, summed; null before any); focus_player (1 when its AI controller's focus is the player pawn; null
//   without an AI controller). A select's "where": [{"prop", "op", "value"}] keeps only actors whose reflected property
//   (read as prop: reads it) compares so, and "player": false every actor but the player pawn.
// - world: "value": {"time_dilation" (the lowest effective global time dilation over the frames since the previous
//   sample, null before any frame), "paused" (1 when the game was paused in any of them)}.
// - render: "value": {"draw_calls", "triangles" (the RHI's counts of a frame, as `stat RHI` shows them: the highest over
//   the frames since the previous sample, the UI's draws and the plugin's own captures among them; null before any
//   frame), "texture_mb" (the RHI's texture memory in use at the sample, streaming and not, in MiB)}.
// - pad: "value": {"rumble" (the strongest of the four force feedback motors the player
//   controller drove in any frame since the previous sample, 0-1: the values the engine computes each tick from the
//   game's force feedback effects, dynamic ones and located ones, scaled by its ForceFeedbackScale, and sent to the
//   player's controller; 0 while the game has force feedback turned off; null before any frame), "effects" (the most
//   force feedback effects playing at once in those frames: ClientPlayForceFeedback's)}. Computed whether a pad is
//   plugged in or not, as the engine does.
// - nav: "value": {"found" (1 when the navigation finds a whole path from query.from to query.to, 0 when it
//   finds none or only part of one), "partial" (1 for a part of one), "length" (cm along the path found, null with
//   none), "detour" (that length over the straight distance on the ground, null with none)} | null when the world has
//   no navigation data to ask. query.from and query.to are points as a select's near takes them; query.agent (an actor
//   selection, the nearest match to the player) is the one whose way of moving the path is for (its navigation agent:
//   size, the areas it may cross), default the navigation's default agent.
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
//   seen in unless it simulates physics: then its body's angular velocity), world_yaw and world_pitch (a scene
//   component's own rotation in the world, degrees in (-180, 180], as actors' world_yaw:<Component> without a name).
//   select.effect: true keeps only live effects
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
// - audio: "value": {"count", "audible", "volume", "max_volume", "loudest", "paused"} | null: the audio device's active sounds
//   (null without an audio device: a play under -nosound) that select matches (select.sound: a wildcard on the sound
//   asset's name, select.sound_class: on its sound class's or a parent class's name, select.owner: an actor selection
//   its owner is in), each at its volume at the listener: its wave instances' volume (its own, its class's and mixes',
//   multipliers) times their distance and occlusion attenuation and dynamic volume, summed, the output's primary
//   volume left out. count: how many; audible: how many at 0.001 (-60 dB) or more; volume: their sum; max_volume and
//   loudest (its sound's name): the loudest one; paused: how many are paused, by the game (a sound paused on its
//   own, UAudioComponent::SetPaused) or by the game's pause (a sound that isn't a UI sound while the world is
//   paused), and a paused sound plays nothing, so it is at volume 0 (counted, never audible). select.near (a select's near) keeps sounds with a place (played at a
//   location, spatialized) near the point as it is at the sample. And the sounds that started (Listen: the active
//   sounds looked at once a frame, so every start is seen, however short the sound): started (how many started since
//   the play began, to this sample), started_audible (how many of them have reached 0.001 at the listener),
//   "starts": [{"t", "sound", "named", "class", "x", "y", "z", "peak"}] for at most 64 that started since the
//   previous sample (t: the play time it was first seen; named: a saved asset, not a sound made at run time; x y z
//   null for a sound with no place; peak: its loudest at the listener so far), "starts_total" how many did, and
//   "starts_capped": true once more than 8192 started in the play (the later ones aren't counted).
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
struct FSoundStarts;
class FMix;

/** A point of the game viewport, in viewport fractions 0-1, in Slate's absolute (desktop) space. */
bool ViewportPoint(double Fx, double Fy, FVector2D& OutAbsolute);
/** The first enabled, visible UMG button in the viewport whose name (wildcard) or class matches. */
UButton* FindButton(UWorld* World, const FString& Want);
/** A click's Slate fallback (no UMG button matches): the first enabled, visible Slate button under the game viewport (a
 *  widget whose type ends in "Button": SButton, SComboButton, a game's own S...Button) that Want names by its text (a
 *  text block inside it, or all of them in order), its tag or its type (with or without its S), each compared as
 *  LabelKey makes them, so "New_expedition" names the button whose text reads "New expedition". Null when none.
 *  OutCentre: its centre in Slate's absolute space; OutLabel: what matched, for the log. */
TSharedPtr<SWidget> FindSlateButton(const FString& Want, FVector2D& OutCentre, FString& OutLabel);
/** Whether a button Want names (a UMG button by name or class, a Slate button as FindSlateButton names it) is shown
 *  but disabled: a click on it does nothing, as a player's would (game grader 1.14.0). OutLabel: which, for the log. */
bool DisabledButtonShown(UWorld* World, const FString& Want, FString& OutLabel);
/** Whether a press at a widget's centre reaches it (game grader 1.16.0): 0 when Slate's
 *  hit test there finds the widget or one inside it, 1 when it finds another widget over it (OutOver: what, for the
 *  log), -1 when it can't be told (not drawn, of no size, its centre outside the game viewport or outside a scroll area
 *  above it, no window there). */
int32 CoverAt(const TSharedPtr<SWidget>& Target, FString& OutOver);
/** A widget whose centre lies outside the view of the scroll boxes above it (SScrollBox, as UMG's UScrollBox draws one)
 *  scrolled into each one's view, innermost first, at once (no animation): what a player does before clicking it
 *  (game grader 1.16.0). Whether any was scrolled; OutAreas: which, for the log. The layout follows on the next frame. */
bool ScrollIntoView(const TSharedPtr<SWidget>& Target, FString& OutAreas);
/** The centre, in Slate's absolute space, of the first visible, laid-out UMG widget in the viewport whose name
 *  (wildcard) or class matches, whatever its kind (a button, a stick, a panel); else of the Slate button
 *  FindSlateButton finds. Where a touch on that widget lands. */
bool WidgetCentre(UWorld* World, const FString& Want, FVector2D& OutCentre, FString& OutLabel);
/** A name or a caption as a click compares them: lower case, each run of anything but letters and digits one "_",
 *  none at either end ("New expedition", "new_expedition" and "NEW  EXPEDITION!" alike). */
FString LabelKey(const FString& Text);
/** Where teleport_to puts the pawn: Distance cm from the nearest actor Select matches (nearest to the pawn), on the
 *  pawn's side of it (level, plus Offset), and the yaw that faces Face (a point, as a query's) or else that actor. */
bool TeleportSpot(UWorld* World, APlayerController* PC, const TSharedPtr<FJsonObject>& Select, double Distance, const FVector& Offset,
	const TSharedPtr<FJsonObject>& Face, FVector& OutLocation, double& OutYaw, FString& OutName);

/** The stages of a contact (docs/task-probes.md, section 1.3). The actor Select matches nearest to the
 *  player pawn, never the pawn itself unless the select is {"player": true}; null when none. OutAll: every match. */
AActor* NearestMatch(UWorld* World, APlayerController* PC, const TSharedPtr<FJsonObject>& Select, TArray<AActor*>* OutAll = nullptr);
/** pin's `at`: a point as a query's (xyz, pawn, camera, actor), resolved now; false when it doesn't resolve. */
bool PointOf(UWorld* World, APlayerController* PC, const TSharedPtr<FJsonObject>& Point, FVector& OutPoint);
/** set: writes a reflected property (prop: path, no index) of an actor or one of its components from a JSON number,
 *  boolean or string (an enum by its name, a name, a string, a text); false with why when it can't. */
bool WriteProp(UObject* Root, const FString& Path, const TSharedPtr<FJsonValue>& Value, FString& OutWhy);
/** damage: what an actor's TakeDamage returned for a staged hit, added to its damage_taken. */
void NoteDamage(const AActor* A, double Taken);

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

/** A click's text as shown (game grader 1.18.0): the centre, in viewport fractions, of the one text on screen that
 *  reads `Want` as a click compares names (LabelKey), whatever drew it (a UMG or Slate text, the HUD's canvas, a
 *  widget's own paint); or of a run of texts side by side on one line that reads it joined. OutMatches: how many
 *  places read it (two places further apart than a text's own size are two); true only for exactly one. */
bool FindShownText(const TArray<FUiElement>& Shown, const FString& Want, double& OutX, double& OutY, FString& OutLabel,
	int32& OutMatches);

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

/** An actor frozen follows frame by frame: its place and its skinned meshes' bones (component space) at the last frame,
 *  how long (s) it has held still so far, and the longest it held still since the last sample. */
struct FStillTrack
{
	TWeakObjectPtr<const AActor> Actor;
	FVector Place = FVector::ZeroVector;
	TArray<FVector> Bones;
	bool bSeen = false;
	bool bMovedBefore = false;  // it moved in a frame before the stop under way
	double Run = 0.0;
	double Longest = 0.0;
	double Time = 0.0;  // seconds followed since the last sample
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
	/** A heard query's clips of the mix (TaskProbeHeard.h) written to Dir: the files' names (none without one). */
	TArray<FString> WriteHeardClips(const FString& Dir);
	const TArray<FString>& Errors() const { return ErrorList; }
	/** A heard query is asked: the play is paced to real time, as the mix it hears renders (TaskProbeHeard.h). */
	bool HearsMix() const { return Mix.IsValid(); }
	/** A screen or ui sample waits for the next frame the game viewport draws. */
	bool WaitsForFrame() const { return bWantFrame || bWantUi; }
	/** Every frame of the play (the clock running or held): spin's components turn by so much since the last frame,
	 *  frozen's actors hold still or not, the world's time dilation and pause are noted. */
	void Frame(float DeltaTime, UWorld* World);
	/** Every frame of the play, before the world ticks (only with an audio query): the sounds that started since the
	 *  last frame, at play time T (audio's started fields). */
	void Listen(UWorld* World, double T);
	/** One reading, now, of a shot's `when` (game grader 1.16.0): query `Def` (an actors or widgets query as the
	 *  queries file names one) sampled once, its rows' `Field` reduced by `Of` (count: how many match; any, all, count,
	 *  sum, min, max, mean, first of the rows' values; text by `Match`). False when it reads no value. */
	bool ReadNow(const TSharedPtr<FJsonObject>& Def, const FString& Field, const FString& Of, const FString& Match,
		UWorld* World, APlayerController* PC, double& OutValue);
	/** Reads what is on screen from the next frame on, as a ui query does (the HUD canvas, the paint), for a click's
	 *  text (game grader 1.18.0). */
	void HookUi();
	/** Every text on screen in the next frame the viewport draws (TakeText). */
	void WantText() { bWantUi = true; bWantText = true; bTextReady = false; }
	/** What WantText asked for, once that frame has been drawn: false until then. */
	bool TakeText(TArray<TaskProbe::FUiElement>& Out)
	{
		if (!bTextReady)
		{
			return false;
		}
		Out = MoveTemp(TextNow);
		TextNow.Reset();
		bTextReady = false;
		return true;
	}

private:
	bool bWantText = false;  // a click's text: the next FillUi keeps every element it found (TextNow)
	bool bTextReady = false;
	TArray<TaskProbe::FUiElement> TextNow;
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
		double HeardT = -1.0;  // audio: the previous sample's time (its starts are those after it)
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
	void SampleAudio(FQuery& Q, UWorld* World, APlayerController* PC, double T, FJsonObject& Out);
	void SampleGround(FQuery& Q, UWorld* World, APlayerController* PC, FJsonObject& Out);
	void SampleCamera(UWorld* World, APlayerController* PC, FJsonObject& Out);
	void SampleDrawn(FQuery& Q, UWorld* World, APlayerController* PC, FJsonObject& Out);
	TSharedPtr<FJsonValue> SpinOf(const USceneComponent* C);
	TSharedPtr<FJsonValue> ActorSpin(const AActor* A);
	TSharedPtr<FJsonValue> ActorStill(const AActor* A);
	void SampleWorld(FJsonObject& Out);
	void SampleRender(FJsonObject& Out);
	void SamplePad(FJsonObject& Out);
	void SampleNav(FQuery& Q, UWorld* World, APlayerController* PC, FJsonObject& Out);
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
	TSharedPtr<TaskProbe::FSoundStarts, ESPMode::ThreadSafe> SoundStarts;  // audio: every sound started (only with an audio query)
	TSharedPtr<TaskProbe::FMix, ESPMode::ThreadSafe> Mix;  // heard: the mix as the player hears it (only with a heard query)
	FString MixId;  // heard: its query's id (one heard query a play)
	TUniquePtr<TaskProbe::FGlowRender> GlowRender;  // lit, glow: meshes whose emissive is read as rendered
	TUniquePtr<TaskProbe::FDrawnRender> DrawnRender;  // drawn: what is drawn in a place, rendered
	TMap<FObjectKey, TaskProbe::FSpinTrack> Spins;  // spin: the components read last sample, their turning since
	TSet<FObjectKey> SpinRead;  // spin: the components read this sample
	TMap<FObjectKey, TaskProbe::FStillTrack> Stills;  // frozen: the actors read last sample, their stillness since
	TSet<FObjectKey> StillRead;  // frozen: the actors read this sample
	double MinDilation = -1.0;  // world: the lowest global time dilation since the previous sample (-1: no frame yet)
	bool bPausedSince = false;  // world: the game was paused in a frame since the previous sample
	bool bHasWorld = false;  // a world query is asked for: only then is the world read every frame
	int32 MaxDrawCalls = -1, MaxPrimitives = -1;  // render: the RHI's highest frame counts since the previous sample (-1: no frame yet)
	bool bHasRender = false;  // a render query is asked for: only then are the RHI's counts read every frame
	double MaxRumble = -1.0;  // pad: the strongest motor value the player controller drove since the previous sample (-1: no frame yet)
	int32 MaxRumbleEffects = 0;  // pad: the most force feedback effects playing at once since the previous sample
	bool bHasPad = false;  // a pad query is asked for: only then is the force feedback read every frame
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
