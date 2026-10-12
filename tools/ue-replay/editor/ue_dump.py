"""Structure dump of an Unreal project, run inside the editor (headless):

  UnrealEditor-Cmd <uproject> -run=pythonscript -script="ue_dump.py --out <dir> [--roots /Game/A,/Game/B]
                   [--maps all|none|/Game/X/Map,...] [--assets 1|0] [--t3d 1|0] [--module <GameModule>]"

Writes <out>/assets.json (one entry per asset: package, class, per-class digest) and <out>/maps/<Map>.json (every
actor: class, label, name, folder, transform, attach parent, tags, components with their key settings, and every
editor property of the game's own classes), plus <out>/maps/<Map>.t3d (the level exported as T3D, the text the
editor's copy/paste uses) when --t3d 1. Floats are rounded to 1e-4. Used by ue_replay.py verify and derive.
"""
import argparse
import json
import os
import shlex
import sys
import time

import unreal

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
AR = unreal.AssetRegistryHelpers.get_asset_registry()
MEL = unreal.MaterialEditingLibrary


def args():
    raw = sys.argv[1:]
    if len(raw) == 1 and " " in raw[0]:
        raw = shlex.split(raw[0])
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--roots", default="/Game")
    ap.add_argument("--maps", default="all")
    ap.add_argument("--map-roots", default="")
    ap.add_argument("--assets", default="1")
    ap.add_argument("--t3d", default="1")
    ap.add_argument("--module", default="")
    return ap.parse_args(raw)


# ------------------------------------------------------------------------------------------- values
def ser(v, depth=0):
    if v is None or isinstance(v, (bool, int, str)):
        return v
    if isinstance(v, float):
        r = round(v, 4)
        return 0.0 if r == 0 else r
    if isinstance(v, (unreal.Name, unreal.Text)):
        return str(v)
    if isinstance(v, unreal.EnumBase):
        return v.name
    if isinstance(v, unreal.Object):
        return v.get_path_name()
    if isinstance(v, (unreal.Vector, unreal.Vector2D, unreal.Rotator, unreal.LinearColor, unreal.Color)):
        return [ser(x) for x in vec_tuple(v)]
    if depth > 4:
        return "<deep>"
    if isinstance(v, (list, tuple, set, unreal.Array, unreal.Set)):
        items = list(v)
        out = [ser(x, depth + 1) for x in items[:300]]
        if len(items) > 300:
            out.append("<%d more>" % (len(items) - 300))
        return out
    if isinstance(v, unreal.Map):
        return {str(ser(k, depth + 1)): ser(x, depth + 1) for k, x in v.items()}
    if isinstance(v, unreal.StructBase):
        try:
            return {"_struct": type(v).__name__, "text": v.export_text()}
        except Exception:
            return {"_struct": type(v).__name__, "repr": repr(v)[:300]}
    return repr(v)[:300]


def vec_tuple(v):
    if isinstance(v, unreal.Vector):
        return (v.x, v.y, v.z)
    if isinstance(v, unreal.Vector2D):
        return (v.x, v.y)
    if isinstance(v, unreal.Rotator):
        return (v.roll, v.pitch, v.yaw)
    if isinstance(v, unreal.LinearColor):
        return (v.r, v.g, v.b, v.a)
    return (v.r, v.g, v.b, v.a)


_prop_cache = {}


def prop_names(obj):
    """Editor-exposed property names of an object's class (Python getset descriptors on the wrapper classes)."""
    t = type(obj)
    if t not in _prop_cache:
        names = []
        for cls in t.__mro__:
            for k, d in cls.__dict__.items():
                if k.startswith("_") or type(d).__name__ != "getset_descriptor":
                    continue
                names.append(k)
        _prop_cache[t] = sorted(set(names))
    return _prop_cache[t]


def all_props(obj, skip=()):
    out = {}
    for k in prop_names(obj):
        if k in skip:
            continue
        try:
            out[k] = ser(obj.get_editor_property(k))
        except Exception:
            pass
    return out


def pick(obj, names):
    out = {}
    for k in names:
        try:
            out[k] = ser(obj.get_editor_property(k))
        except Exception:
            pass
    return out


# ------------------------------------------------------------------------------------------- assets
def digest(asset):
    d = {}
    try:
        if isinstance(asset, unreal.StaticMesh):
            b = asset.get_bounds()
            d["lods"] = asset.get_num_lods()
            d["triangles_lod0"] = asset.get_num_triangles(0)
            d["vertices_lod0"] = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_number_verts(asset, 0)
            d["bounds"] = [ser(b.origin), ser(b.box_extent)]
            d["materials"] = [[str(m.material_slot_name), ser(m.material_interface)] for m in asset.get_editor_property("static_materials")]
            d["sections_lod0"] = asset.get_num_sections(0)
            d["collision_complex_as_simple"] = ser(asset.get_editor_property("body_setup").get_editor_property("collision_trace_flag")) if asset.get_editor_property("body_setup") else None
            try:
                d["nanite"] = asset.get_editor_property("nanite_settings").get_editor_property("enabled")
            except Exception:
                pass
        elif isinstance(asset, unreal.SkeletalMesh):
            b = asset.get_bounds()
            d["skeleton"] = ser(asset.get_editor_property("skeleton"))
            d["bounds"] = [ser(b.origin), ser(b.box_extent)]
            d["materials"] = [[str(m.material_slot_name), ser(m.material_interface)] for m in asset.get_editor_property("materials")]
            d["lods"] = len(asset.get_editor_property("lod_info"))
        elif isinstance(asset, unreal.Texture2D):
            d["size"] = [asset.blueprint_get_size_x(), asset.blueprint_get_size_y()]
            d.update(pick(asset, ["compression_settings", "srgb", "lod_group", "mip_gen_settings", "address_x", "address_y", "filter"]))
        elif isinstance(asset, unreal.MaterialInstanceConstant):
            d["parent"] = ser(asset.get_editor_property("parent"))
            d["scalar"] = {str(n): ser(MEL.get_material_instance_scalar_parameter_value(asset, n)) for n in MEL.get_scalar_parameter_names(asset)}
            d["vector"] = {str(n): ser(MEL.get_material_instance_vector_parameter_value(asset, n)) for n in MEL.get_vector_parameter_names(asset)}
            d["texture"] = {str(n): ser(MEL.get_material_instance_texture_parameter_value(asset, n)) for n in MEL.get_texture_parameter_names(asset)}
            d["overrides"] = [ser(x) for x in asset.get_editor_property("scalar_parameter_values")][:100]
        elif isinstance(asset, unreal.Material):
            d["expressions"] = MEL.get_num_material_expressions(asset)
            d.update(pick(asset, ["blend_mode", "shading_model", "two_sided", "material_domain", "opacity_mask_clip_value",
                                  "used_with_skeletal_mesh", "used_with_niagara_sprites", "used_with_niagara_meshes", "blendable_location"]))
            d["scalar_params"] = sorted(str(n) for n in MEL.get_scalar_parameter_names(asset))
            d["vector_params"] = sorted(str(n) for n in MEL.get_vector_parameter_names(asset))
            d["texture_params"] = sorted(str(n) for n in MEL.get_texture_parameter_names(asset))
        elif isinstance(asset, unreal.SoundWave):
            d.update(pick(asset, ["duration", "num_channels", "sample_rate", "looping", "volume", "sound_class_object"]))
        elif isinstance(asset, unreal.AnimSequence):
            d["skeleton"] = ser(asset.get_editor_property("skeleton"))
            d["play_length"] = ser(asset.get_play_length())
            d["frames"] = unreal.AnimationLibrary.get_num_frames(asset)
            d.update(pick(asset, ["rate_scale", "enable_root_motion", "interpolation"]))
            try:
                d["notifies"] = len(unreal.AnimationLibrary.get_animation_notify_events(asset))
            except Exception:
                pass
        elif isinstance(asset, unreal.Blueprint):
            gc = asset.generated_class()
            d["parent"] = ser(asset.get_editor_property("parent_class"))
            if gc:
                cdo = unreal.get_default_object(gc)
                d["cdo"] = all_props(cdo, skip=("actor_guid",))
        elif isinstance(asset, unreal.World):
            pass
        elif isinstance(asset, (unreal.DataAsset, unreal.PrimaryDataAsset)) or type(asset).__module__ == "unreal" and asset.get_class().get_path_name().startswith("/Script/" + MODULE + "."):
            d["props"] = all_props(asset)
        elif isinstance(asset, unreal.NiagaraSystem):
            d["props"] = pick(asset, ["warmup_time", "fixed_bounds"])
        elif isinstance(asset, unreal.InputAction):
            d.update(pick(asset, ["value_type", "consume_input"]))
        elif isinstance(asset, unreal.InputMappingContext):
            d["mappings"] = [[ser(m.get_editor_property("action")), m.get_editor_property("key").export_text()] for m in asset.get_editor_property("mappings")]
        elif isinstance(asset, unreal.FontFace):
            d.update(pick(asset, ["hinting", "loading_policy", "source_filename"]))
    except Exception as e:  # keep going: the error is part of the record
        d["error"] = str(e)[:300]
    return d


def dump_assets(roots, out):
    rows = []
    t0 = time.time()
    for root in roots:
        for ad in AR.get_assets_by_path(root, recursive=True):
            pkg = str(ad.package_name)
            row = {"package": pkg, "name": str(ad.asset_name), "class": str(ad.asset_class_path.asset_name) if hasattr(ad, "asset_class_path") else str(ad.asset_class)}
            if row["class"] in ("World", "MapBuildDataRegistry"):
                rows.append(row)
                continue
            if row["class"] in NO_LOAD:
                # described from asset-registry tags: loading an animation can start a recompression that asserts on
                # clips whose length is not a whole number of frames (engine check in FCompressibleAnimData::FetchData)
                row["digest"] = {"tags": {t: str(ad.get_tag_value(t)) for t in REGISTRY_TAGS if ad.get_tag_value(t) is not None}}
                rows.append(row)
                continue
            a = ad.get_asset()
            if a is None:
                row["error"] = "failed to load"
            else:
                row["digest"] = digest(a)
            rows.append(row)
    rows.sort(key=lambda r: (r["package"], r["name"]))
    with open(os.path.join(out, "assets.json"), "w", encoding="utf-8") as f:
        json.dump({"roots": roots, "count": len(rows), "seconds": round(time.time() - t0, 1), "assets": rows}, f, ensure_ascii=False, indent=0)
    unreal.log("ue_dump: %d assets in %.1f s" % (len(rows), time.time() - t0))


# ------------------------------------------------------------------------------------------- maps
COMPONENT_KEYS = {
    unreal.StaticMeshComponent: ["static_mesh", "override_materials", "cast_shadow", "mobility", "visible", "hidden_in_game",
                                 "collision_enabled", "translucency_sort_priority", "render_custom_depth"],
    unreal.SkeletalMeshComponent: ["skeletal_mesh_asset", "override_materials", "animation_mode", "anim_class", "cast_shadow", "visible"],
    unreal.LightComponentBase: ["intensity", "light_color", "cast_shadows", "mobility", "visible", "affects_world"],
    unreal.PointLightComponent: ["attenuation_radius", "source_radius", "intensity_units"],
    unreal.DirectionalLightComponent: ["atmosphere_sun_light"],
    unreal.SkyLightComponent: ["real_time_capture", "source_type", "lower_hemisphere_is_black"],
    unreal.ExponentialHeightFogComponent: ["fog_density", "fog_height_falloff", "fog_inscattering_luminance", "enable_volumetric_fog",
                                           "volumetric_fog_scattering_distribution", "volumetric_fog_albedo", "volumetric_fog_extinction_scale",
                                           "start_distance", "fog_max_opacity"],
    unreal.NiagaraComponent: ["asset", "auto_activate"],
    unreal.CameraComponent: ["field_of_view", "aspect_ratio", "projection_mode"],
    unreal.TextRenderComponent: ["text", "world_size"],
    unreal.BrushComponent: [],
}
PPV_KEYS = ["auto_exposure_method", "auto_exposure_bias", "bloom_intensity", "vignette_intensity", "motion_blur_amount",
            "auto_exposure_apply_physical_camera_exposure", "color_saturation", "color_contrast", "color_gamma", "film_slope",
            "scene_color_tint", "ambient_occlusion_intensity"]


def component_info(c):
    info = {"class": c.get_class().get_path_name(), "name": c.get_name()}
    if isinstance(c, unreal.SceneComponent):
        t = c.get_editor_property("relative_location"), c.get_editor_property("relative_rotation"), c.get_editor_property("relative_scale3d")
        info["rel"] = [ser(t[0]), ser(t[1]), ser(t[2])]
        p = c.get_attach_parent()
        if p:
            info["parent"] = p.get_name()
    for cls, keys in COMPONENT_KEYS.items():
        if isinstance(c, cls):
            info.update(pick(c, keys))
    if isinstance(c, unreal.PrimitiveComponent):
        try:
            info["collision_profile"] = str(c.get_collision_profile_name())
        except Exception:
            pass
    if isinstance(c, unreal.StaticMeshComponent):
        try:
            info["materials"] = [ser(m) for m in c.get_materials()]
        except Exception:
            pass
    return info


def actor_info(a, module):
    info = {
        "class": a.get_class().get_path_name(),
        "label": a.get_actor_label(),
        "name": a.get_name(),
        "folder": str(a.get_folder_path()),
        "location": ser(a.get_actor_location()),
        "rotation": ser(a.get_actor_rotation()),
        "scale": ser(a.get_actor_scale3d()),
        "tags": [str(t) for t in a.tags],
    }
    for k in ("hidden", "is_editor_only_actor", "can_be_damaged"):
        try:
            info[k] = ser(a.get_editor_property(k))
        except Exception:
            pass
    try:
        par = a.get_attach_parent_actor()
        if par:
            info["attach_parent"] = par.get_actor_label()
    except Exception:
        pass
    comps = a.get_components_by_class(unreal.ActorComponent)
    info["components"] = sorted((component_info(c) for c in comps), key=lambda x: (x["class"], x["name"]))
    cls = info["class"]
    own = (module and cls.startswith("/Script/%s." % module)) or not cls.startswith("/Script/")
    if own:
        info["props"] = all_props(a, skip=("actor_guid", "content_bundle_guid", "actor_instance_guid"))
    if isinstance(a, unreal.PostProcessVolume):
        s = a.get_editor_property("settings")
        info["ppv"] = {"unbound": a.get_editor_property("unbound"), "priority": ser(a.get_editor_property("priority")),
                       "blend_weight": ser(a.get_editor_property("blend_weight"))}
        for k in PPV_KEYS:
            try:
                if s.get_editor_property("override_" + k):
                    info["ppv"][k] = ser(s.get_editor_property(k))
            except Exception:
                pass
        try:
            info["ppv"]["blendables"] = [[ser(b.get_editor_property("weight")), ser(b.get_editor_property("object"))]
                                         for b in s.get_editor_property("weighted_blendables").get_editor_property("array")]
        except Exception:
            pass
    return info


def export_t3d(world, path):
    task = unreal.AssetExportTask()
    task.set_editor_property("object", world)
    task.set_editor_property("filename", path)
    task.set_editor_property("automated", True)
    task.set_editor_property("prompt", False)
    task.set_editor_property("replace_identical", True)
    task.set_editor_property("selected", False)
    try:
        task.set_editor_property("exporter", unreal.LevelExporterT3D())
    except Exception:
        pass
    ok = unreal.Exporter.run_asset_export_task(task)
    return bool(ok) and os.path.exists(path)


def dump_maps(roots, which, out, t3d, module):
    md = os.path.join(out, "maps")
    os.makedirs(md, exist_ok=True)
    maps = []
    if which == "all":
        for root in roots:
            for ad in AR.get_assets_by_path(root, recursive=True):
                if str(ad.asset_class_path.asset_name) == "World":
                    maps.append(str(ad.package_name))
    elif which != "none":
        maps = which.split(",")
    summary = []
    for m in sorted(set(maps)):
        t0 = time.time()
        ok = LES.load_level(m)
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        if not ok or world is None:
            summary.append({"map": m, "error": "load_level failed"})
            continue
        actors = EAS.get_all_level_actors()
        rows = [actor_info(a, module) for a in actors]
        order = [a.get_name() for a in actors]  # level order = spawn order for script-built maps
        rows.sort(key=lambda r: (r["label"], r["class"], r["name"]))
        ws = world.get_world_settings()
        rec = {"map": m, "actors": rows, "level_order": order, "count": len(rows),
               "world_settings": pick(ws, ["default_game_mode", "kill_z", "enable_world_bounds_checks", "world_gravity_z"])}
        base = m.rsplit("/", 1)[1]
        rel = m.replace("/Game/", "").replace("/", "__")
        with open(os.path.join(md, rel + ".json"), "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=0)
        t3d_ok = export_t3d(world, os.path.join(md, rel + ".t3d").replace("\\", "/")) if t3d else None
        summary.append({"map": m, "actors": len(rows), "t3d": t3d_ok, "seconds": round(time.time() - t0, 1), "file": rel})
        unreal.log("ue_dump: map %s %d actors t3d=%s" % (base, len(rows), t3d_ok))
    with open(os.path.join(out, "maps.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)


MODULE = ""
NO_LOAD = ("AnimSequence", "AnimMontage", "AnimComposite")
REGISTRY_TAGS = ["Skeleton", "SequenceLength", "NumberOfFrames", "Number of Frames", "NumberOfKeys", "Number of Keys",
                 "TargetFrameRate", "ImportFileFramerate", "ImportResampleFramerate", "RateScale", "AdditiveAnimType",
                 "RetargetSource", "Notifies", "Curves", "Compressed Size (KB)", "Raw Size (KB)", "PreviewSkeletalMesh"]


def main():
    global MODULE
    a = args()
    MODULE = a.module
    os.makedirs(a.out, exist_ok=True)
    roots = a.roots.split(",")
    t0 = time.time()
    if a.assets == "1":
        dump_assets(roots, a.out)
    dump_maps(a.map_roots.split(",") if a.map_roots else roots, a.maps, a.out, a.t3d == "1", a.module)
    with open(os.path.join(a.out, "done.json"), "w", encoding="utf-8") as f:
        json.dump({"seconds": round(time.time() - t0, 1), "engine": unreal.SystemLibrary.get_engine_version(),
                   "project": unreal.Paths.get_project_file_path()}, f)


main()
