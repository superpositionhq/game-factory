using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Object = UnityEngine.Object;

namespace Superposition.LiaoZhaiReplay
{
    /// <summary>Result of one step: how it was executed and what reading it back showed.</summary>
    public sealed class StepResult
    {
        public string Mode;                 // api | import | file_fallback
        public string FallbackReason;
        public readonly List<string> Actions = new List<string>();
        public readonly List<string> Errors = new List<string>();
        public int ReadbackOk, ReadbackFailed;
        public readonly List<object> ReadbackFailures = new List<object>();

        public bool Ok => Errors.Count == 0 && ReadbackFailed == 0;

        public void Fail(string what, object wanted, object got)
        {
            ReadbackFailed++;
            if (ReadbackFailures.Count < 20)
                ReadbackFailures.Add(new OrderedDict { ["path"] = what, ["wanted"] = wanted, ["got"] = got });
        }
    }

    /// <summary>
    /// Editor-API implementations of the liaozhai.unity-workflow/v1 ops. Objects are found by their local file id
    /// (the `file_id` the converter took from the YAML), property paths are the converter's flattened YAML paths.
    /// </summary>
    public static class StepOps
    {
        // ---------- which steps can be expressed through editor APIs ----------

        /// <summary>Null if the step can run through editor APIs, else why not (it is then applied from the commit).</summary>
        public static string WhyNotApi(OrderedDict step)
        {
            var op = (string)step.Get("op");
            var p = (OrderedDict)step.Get("params");
            switch (op)
            {
                case "object.set":
                    if (p.Get("truncated") is bool t && t)
                        return "object.set truncated in workflow.jsonl (more than 400 changed paths)";
                    return null;
                case "object.remove":
                case "asset.move":
                case "asset.delete":
                case "importer.set":
                    return null;
                case "object.add":
                    return "object.add: the new object must carry the commit's local file id, which editor APIs cannot assign";
                case "prefab.override":
                    if (p.Get("truncated") is bool t2 && t2)
                        return "prefab.override truncated in workflow.jsonl";
                    if (p.Has("other"))
                        return "prefab.override changes fields besides m_Modifications";
                    foreach (OrderedDict o in (List<object>)p.Get("overrides_set"))
                        if (((string)o.Get("property")).Contains("[*]"))
                            return "prefab.override with a collapsed array override (" + o.Get("property") +
                                   ", " + o.Get("changed_elements") + " elements; e.g. Odin SerializedBytes)";
                    foreach (OrderedDict o in (List<object>)p.Get("overrides_removed"))
                        if (((string)o.Get("property")).Contains("[*]"))
                            return "prefab.override removes a collapsed array override";
                    return null;
                case "asset.create":
                case "asset.import":
                case "asset.replace":
                case "table.create":
                case "table.edit":
                case "code.change":
                case "file.edit":
                    return null;    // handled as imports of the committed file (see Run)
            }
            return "unknown op " + op;
        }

        // ---------- objects by local file id ----------

        public static long LocalId(Object o)
        {
            if (o == null) return 0;
            if (AssetDatabase.TryGetGUIDAndLocalFileIdentifier(o, out string _, out long id) && id != 0)
                return id;
            return (long)GlobalObjectId.GetGlobalObjectIdSlow(o).targetObjectId;
        }

        static readonly Dictionary<string, Dictionary<long, Object>> cache = new Dictionary<string, Dictionary<long, Object>>();

        public static void ClearCache() => cache.Clear();

        public static Dictionary<long, Object> Objects(string path)
        {
            if (cache.TryGetValue(path, out var d) && d.Values.All(o => o != null))
                return d;
            d = new Dictionary<long, Object>();
            if (path.EndsWith(".unity", StringComparison.OrdinalIgnoreCase))
            {
                var scene = EditorSceneManager.GetSceneByPath(path);
                if (!scene.isLoaded)
                    scene = EditorSceneManager.OpenScene(path, OpenSceneMode.Single);
                foreach (var root in scene.GetRootGameObjects())
                    foreach (var t in root.GetComponentsInChildren<Transform>(true))
                    {
                        d[LocalId(t.gameObject)] = t.gameObject;
                        foreach (var c in t.GetComponents<Component>())
                            if (c != null) d[LocalId(c)] = c;
                    }
            }
            else
            {
                foreach (var o in AssetDatabase.LoadAllAssetsAtPath(path))
                    if (o != null && AssetDatabase.TryGetGUIDAndLocalFileIdentifier(o, out string _, out long id))
                        d[id] = o;
            }
            cache[path] = d;
            return d;
        }

        static Object Find(string path, object fileId)
        {
            long id = Convert.ToInt64(fileId, CultureInfo.InvariantCulture);
            return Objects(path).TryGetValue(id, out var o) ? o : null;
        }

        /// <summary>Resolves a YAML reference {fileID, guid, type} seen from asset <paramref name="from"/>.</summary>
        public static bool ResolveRef(OrderedDict r, string from, out Object result)
        {
            result = null;
            long fid = Convert.ToInt64(r.Get("fileID") ?? 0L, CultureInfo.InvariantCulture);
            if (fid == 0)
                return true;
            var guid = r.Get("guid") as string;
            string path = string.IsNullOrEmpty(guid) ? from : AssetDatabase.GUIDToAssetPath(guid);
            if (string.IsNullOrEmpty(path))
                return false;
            if (Objects(path).TryGetValue(fid, out result))
                return true;
            // Built-in resources and package scripts: fall back to the main asset when the id is a main-object id.
            result = AssetDatabase.LoadMainAssetAtPath(path);
            return result != null && LocalId(result) == fid;
        }

        // ---------- object.set ----------

        public static void ObjectSet(OrderedDict step, StepResult res)
        {
            var target = (string)step.Get("target");
            var p = (OrderedDict)step.Get("params");
            var obj = Find(target, ((OrderedDict)p.Get("object")).Get("file_id"));
            if (obj == null)
            {
                res.Errors.Add("object " + ((OrderedDict)p.Get("object")).Get("file_id") + " not found in " + target);
                return;
            }
            var values = NameKeyed((OrderedDict)p.Get("values"));
            if (obj.GetType().FullName == AddressablesGroupType)
                values = AddressablesEntries(obj, values, Inserts(p, "m_SerializeEntries"), res);
            var so = new SerializedObject(obj);
            var applied = new List<KeyValuePair<string, object>>();
            var removals = new List<string>();
            foreach (var path in Order(values))
            {
                var v = values.Get(path);
                if (v == null && IsContainerOfOthers(path, values))
                    continue;
                if (v == null && IsElementPath(path) && ElementRemoved(path, values))
                {
                    removals.Add(ElementPrefix(path));
                    continue;
                }
                if (Set(so, path, v, target, res))
                    applied.Add(new KeyValuePair<string, object>(path, v));
            }
            foreach (var elem in removals.Distinct().OrderByDescending(e => e, StringComparer.Ordinal))
                RemoveElement(so, elem, res);
            if (p.Get("list_inserts") is OrderedDict inserts)
                foreach (var list in inserts.OrderedKeys)
                    if (!(list == "m_SerializeEntries" && obj.GetType().FullName == AddressablesGroupType))
                        PlaceInserted(so, list, (List<object>)inserts.Get(list), res);
            so.ApplyModifiedPropertiesWithoutUndo();
            EditorUtility.SetDirty(obj);
            res.Actions.Add($"SerializedObject({obj.GetType().Name} {LocalId(obj)}): set {applied.Count} properties" +
                            (removals.Count > 0 ? $", removed {removals.Distinct().Count()} list elements" : ""));
            so = new SerializedObject(obj);
            foreach (var kv in applied)
                ReadBack(so, kv.Key, kv.Value, target, res);
        }

        /// <summary>Paths in an order that sizes lists before their elements are set (index paths ascending).</summary>
        static IEnumerable<string> Order(OrderedDict values) => values.OrderedKeys;

        static readonly System.Text.RegularExpressions.Regex SavedProp = new System.Text.RegularExpressions.Regex(
            @"^(m_SavedProperties\.m_(?:Floats|Colors|TexEnvs|Ints))\[\d+\]\.([^.\[]+)(.*)$");

        /// <summary>
        /// Material saved properties are YAML lists of one-key maps (`- _Name: value`), so the converter's paths
        /// are `m_Floats[42]._Name`; an inserted property shifts every later index. Serialized, each element is a
        /// pair (first = name, second = value), so the paths are rewritten to `m_Floats[first=_Name].second`.
        /// A name that moved to another index appears once as null and once with its value; the value wins.
        /// </summary>
        static OrderedDict NameKeyed(OrderedDict values)
        {
            if (!values.OrderedKeys.Any(k => SavedProp.IsMatch(k))) return values;
            var o = new OrderedDict();
            foreach (var k in values.OrderedKeys)
            {
                var m = SavedProp.Match(k);
                var key = m.Success ? $"{m.Groups[1].Value}[first={m.Groups[2].Value}].second{m.Groups[3].Value}" : k;
                if (o.Has(key) && values.Get(k) == null) continue;
                o[key] = values.Get(k);
            }
            return o;
        }

        // ---------- Addressables groups ----------

        const string AddressablesGroupType = "UnityEditor.AddressableAssets.Settings.AddressableAssetGroup";
        static readonly System.Text.RegularExpressions.Regex EntryPath = new System.Text.RegularExpressions.Regex(
            @"^m_SerializeEntries\[m_GUID=([0-9a-f]{32})\](?:\.(.+))?$");

        /// <summary>
        /// Entries of an Addressables group are added, moved and removed through AddressableAssetSettings
        /// (CreateOrMoveEntry / RemoveAssetEntry), as the editor's Addressables window and "Mark as Addressable" do.
        /// The group rebuilds m_SerializeEntries from its entry map on save, so setting the list directly cannot
        /// reproduce its order. Returns the values that are not entry paths, for the generic setter.
        /// Called by reflection so the package does not depend on com.unity.addressables.
        /// </summary>
        /// <summary>Insertion index by key ("[m_GUID=…]" → n) for one list of the step's list_inserts.</summary>
        static Dictionary<string, long> Inserts(OrderedDict p, string list)
        {
            var d = new Dictionary<string, long>();
            if (p.Get("list_inserts") is OrderedDict ins && ins.Get(list) is List<object> items)
                foreach (List<object> pair in items)
                    d[(string)pair[1]] = Convert.ToInt64(pair[0], CultureInfo.InvariantCulture);
            return d;
        }

        /// <summary>
        /// Moves each element the commit added to an identity-keyed list to the index the converter recorded
        /// (list_inserts), lowest index first, so the list ends in the commit's order.
        /// </summary>
        static void PlaceInserted(SerializedObject so, string listPath, List<object> added, StepResult res)
        {
            var list = Walk(so, listPath, false, out var err);
            if (list == null || !list.isArray) { res.Errors.Add("list_inserts " + listPath + ": " + err); return; }
            int moved = 0;
            foreach (List<object> pair in added.OrderBy(x => Convert.ToInt64(((List<object>)x)[0])))
            {
                int want = (int)Convert.ToInt64(pair[0], CultureInfo.InvariantCulture);
                var sel = ((string)pair[1]).Trim('[', ']');
                int eq = sel.IndexOf('=');
                if (eq < 0) continue;
                for (int i = 0; i < list.arraySize; i++)
                    if (KeyMatches(list.GetArrayElementAtIndex(i), sel.Substring(0, eq), sel.Substring(eq + 1)))
                    {
                        if (i != want && want < list.arraySize) { list.MoveArrayElement(i, want); moved++; }
                        break;
                    }
            }
            if (moved > 0) res.Actions.Add($"{listPath}: {moved} added elements moved to their committed index");
        }

        static OrderedDict AddressablesEntries(UnityEngine.Object group, OrderedDict values, Dictionary<string, long> order,
                                               StepResult res)
        {
            var rest = new OrderedDict();
            var byGuid = new Dictionary<string, OrderedDict>();
            foreach (var k in values.OrderedKeys)
            {
                var m = EntryPath.Match(k);
                if (!m.Success) { rest[k] = values.Get(k); continue; }
                if (!byGuid.TryGetValue(m.Groups[1].Value, out var d)) byGuid[m.Groups[1].Value] = d = new OrderedDict();
                d[m.Groups[2].Success ? m.Groups[2].Value : ""] = values.Get(k);
            }
            if (byGuid.Count == 0) return values;
            var gt = group.GetType();
            var settings = gt.GetProperty("Settings").GetValue(group);
            var st = settings.GetType();
            var getEntry = gt.GetMethod("GetAssetEntry", new[] { typeof(string) });
            var create = st.GetMethods().First(m => m.Name == "CreateOrMoveEntry" && m.GetParameters().Length == 4);
            var remove = st.GetMethods().First(m => m.Name == "RemoveAssetEntry" && m.GetParameters().Length == 2
                                                     && m.GetParameters()[0].ParameterType == typeof(string));
            int added = 0, removed = 0, updated = 0;
            // Entries are created in the order the commit added them (list_inserts), so the group, which keeps
            // its entries in creation order, serializes them as the commit does.
            foreach (var kv in byGuid.OrderBy(kv => order.TryGetValue("[m_GUID=" + kv.Key + "]", out var n) ? n : -1))
            {
                var guid = kv.Key;
                var fields = kv.Value;
                if (fields.Values.Cast<object>().All(v => v == null))
                {
                    if (getEntry.Invoke(group, new object[] { guid }) != null)
                    {
                        remove.Invoke(settings, new object[] { guid, true });
                        removed++;
                    }
                    if (getEntry.Invoke(group, new object[] { guid }) == null) res.ReadbackOk++;
                    else res.Fail("entry " + guid, "absent", "present");
                    continue;
                }
                var entry = getEntry.Invoke(group, new object[] { guid });
                if (entry == null)
                {
                    if (string.IsNullOrEmpty(AssetDatabase.GUIDToAssetPath(guid)))
                    {
                        res.Errors.Add("Addressables entry " + guid + ": no asset with this GUID in the project");
                        continue;
                    }
                    entry = create.Invoke(settings, new object[] { guid, group, false, true });
                    added++;
                }
                else updated++;
                var et = entry.GetType();
                if (fields.Get("m_Address") is string address)
                {
                    et.GetProperty("address").SetValue(entry, address);
                    if ((string)et.GetProperty("address").GetValue(entry) == address) res.ReadbackOk++;
                    else res.Fail("entry " + guid + " address", address, et.GetProperty("address").GetValue(entry));
                }
                if (fields.Has("m_ReadOnly") && fields.Get("m_ReadOnly") != null)
                    et.GetProperty("ReadOnly").SetValue(entry, Convert.ToInt64(fields.Get("m_ReadOnly")) != 0);
                if (fields.Get("m_SerializedLabels") is List<object> labels)
                {
                    var setLabel = et.GetMethods().First(m => m.Name == "SetLabel" && m.GetParameters().Length == 4);
                    foreach (var l in labels)
                        setLabel.Invoke(entry, new object[] { Convert.ToString(l), true, true, true });
                }
            }
            EditorUtility.SetDirty(group);
            EditorUtility.SetDirty((UnityEngine.Object)settings);
            res.Actions.Add($"AddressableAssetSettings: {added} entries created/moved, {removed} removed, {updated} updated");
            return rest;
        }

        static bool IsContainerOfOthers(string path, OrderedDict values) =>
            values.OrderedKeys.Any(k => k.Length > path.Length && k.StartsWith(path, StringComparison.Ordinal)
                                        && (k[path.Length] == '.' || k[path.Length] == '[') && values.Get(k) != null);

        static bool IsElementPath(string path) => path.Contains("[");

        static string ElementPrefix(string path) => path.Substring(0, path.LastIndexOf(']') + 1);

        /// <summary>Every listed path under the element is null: the element is gone in the commit.</summary>
        static bool ElementRemoved(string path, OrderedDict values)
        {
            var prefix = ElementPrefix(path);
            return values.OrderedKeys.Where(k => k == prefix || k.StartsWith(prefix + ".", StringComparison.Ordinal)
                                                             || k.StartsWith(prefix + "[", StringComparison.Ordinal))
                         .All(k => values.Get(k) == null);
        }

        struct Seg
        {
            public string Field;    // field name, or null for a selector
            public int Index;       // [n]
            public string Key, KeyValue;   // [key=value]
        }

        static List<Seg> Parse(string path)
        {
            var segs = new List<Seg>();
            int i = 0;
            while (i < path.Length)
            {
                if (path[i] == '.') { i++; continue; }
                if (path[i] == '[')
                {
                    int j = path.IndexOf(']', i);
                    var inner = path.Substring(i + 1, j - i - 1);
                    int eq = inner.IndexOf('=');
                    segs.Add(eq < 0 ? new Seg { Index = int.Parse(inner, CultureInfo.InvariantCulture) }
                                    : new Seg { Index = -1, Key = inner.Substring(0, eq), KeyValue = inner.Substring(eq + 1) });
                    i = j + 1;
                    continue;
                }
                int k = i;
                while (k < path.Length && path[k] != '.' && path[k] != '[') k++;
                segs.Add(new Seg { Field = path.Substring(i, k - i), Index = -1 });
                i = k;
            }
            return segs;
        }

        /// <summary>Walks to the property for a flattened path; grows lists and appends keyed elements if asked.</summary>
        static SerializedProperty Walk(SerializedObject so, string path, bool create, out string error)
        {
            error = null;
            SerializedProperty cur = null;
            foreach (var s in Parse(path))
            {
                if (s.Field != null)
                {
                    cur = cur == null ? so.FindProperty(s.Field) : cur.FindPropertyRelative(s.Field);
                    if (cur == null) { error = "no property " + s.Field; return null; }
                    continue;
                }
                if (cur == null || !cur.isArray || cur.propertyType == SerializedPropertyType.String)
                {
                    error = "not a list before selector";
                    return null;
                }
                if (s.Key == null)
                {
                    if (s.Index >= cur.arraySize)
                    {
                        if (!create) { error = $"index {s.Index} >= size {cur.arraySize}"; return null; }
                        int old = cur.arraySize;
                        cur.arraySize = s.Index + 1;
                        for (int n = old; n < cur.arraySize; n++)
                            ClearLists(cur.GetArrayElementAtIndex(n));
                    }
                    cur = cur.GetArrayElementAtIndex(s.Index);
                    continue;
                }
                int found = -1;
                for (int i = 0; i < cur.arraySize && found < 0; i++)
                    if (KeyMatches(cur.GetArrayElementAtIndex(i), s.Key, s.KeyValue))
                        found = i;
                if (found < 0)
                {
                    if (!create) { error = $"no element {s.Key}={s.KeyValue}"; return null; }
                    found = cur.arraySize;
                    cur.arraySize = found + 1;
                    var el = cur.GetArrayElementAtIndex(found);
                    ClearLists(el);
                    if (el.propertyType != SerializedPropertyType.ObjectReference)
                    {
                        var keyProp = el.FindPropertyRelative(s.Key);
                        if (keyProp != null && keyProp.propertyType == SerializedPropertyType.String)
                            keyProp.stringValue = s.KeyValue;
                    }
                }
                cur = cur.GetArrayElementAtIndex(found);
            }
            return cur;
        }

        /// <summary>
        /// Growing a list copies the previous last element into the new slot, nested lists included. The step lists
        /// every leaf of a new element, but not the absence of items it does not have, so nested lists start empty.
        /// </summary>
        static void ClearLists(SerializedProperty el)
        {
            if (el.isArray && el.propertyType != SerializedPropertyType.String)
            {
                el.arraySize = 0;
                return;
            }
            var it = el.Copy();
            var end = el.GetEndProperty();
            bool enter = true;
            while (it.Next(enter) && !SerializedProperty.EqualContents(it, end))
            {
                enter = true;
                if (it.isArray && it.propertyType != SerializedPropertyType.String)
                {
                    it.arraySize = 0;
                    enter = false;
                }
            }
        }

        static bool KeyMatches(SerializedProperty el, string key, string value)
        {
            // Lists of references ({fileID, guid, type}) are keyed by the referenced asset's GUID.
            if (el.propertyType == SerializedPropertyType.ObjectReference)
            {
                var o = el.objectReferenceValue;
                if (o == null) return false;
                if (key == "guid")
                    return AssetDatabase.TryGetGUIDAndLocalFileIdentifier(o, out string g, out long _) && g == value;
                if (key == "fileID")
                    return LocalId(o).ToString(CultureInfo.InvariantCulture) == value;
                return false;
            }
            var k = el.FindPropertyRelative(key);
            if (k == null) return false;
            if (k.propertyType == SerializedPropertyType.ObjectReference)
                return LocalId(k.objectReferenceValue).ToString(CultureInfo.InvariantCulture) == value;
            if (k.propertyType == SerializedPropertyType.String)
                return k.stringValue == value;
            if (k.propertyType == SerializedPropertyType.Integer)
                return k.longValue.ToString(CultureInfo.InvariantCulture) == value;
            return false;
        }

        static void RemoveElement(SerializedObject so, string elementPath, StepResult res)
        {
            int cut = elementPath.LastIndexOf('[');
            var list = Walk(so, elementPath.Substring(0, cut), false, out var err);
            if (list == null) { res.Errors.Add("remove " + elementPath + ": " + err); return; }
            var sel = elementPath.Substring(cut + 1, elementPath.Length - cut - 2);
            int eq = sel.IndexOf('=');
            if (eq < 0)
            {
                // Index-keyed lists lose their tail: the commit's list is shorter.
                list.arraySize = Math.Min(list.arraySize, int.Parse(sel, CultureInfo.InvariantCulture));
                return;
            }
            for (int i = 0; i < list.arraySize; i++)
                if (KeyMatches(list.GetArrayElementAtIndex(i), sel.Substring(0, eq), sel.Substring(eq + 1)))
                {
                    list.DeleteArrayElementAtIndex(i);
                    return;
                }
            // Already gone (e.g. the component's object.remove ran first and Unity dropped its m_Component entry).
            res.Actions.Add("remove " + elementPath + ": already absent");
        }

        static bool Set(SerializedObject so, string path, object v, string asset, StepResult res)
        {
            var prop = Walk(so, path, true, out var err);
            if (prop == null)
            {
                res.Errors.Add(path + ": " + err);
                return false;
            }
            try
            {
                if (Assign(prop, v, asset, out var why))
                    return true;
                res.Errors.Add(path + ": " + why);
            }
            catch (Exception e)
            {
                res.Errors.Add(path + ": " + e.GetType().Name + " " + e.Message);
            }
            return false;
        }

        static bool Assign(SerializedProperty p, object v, string asset, out string why)
        {
            why = null;
            switch (p.propertyType)
            {
                case SerializedPropertyType.Integer:
                case SerializedPropertyType.LayerMask:
                case SerializedPropertyType.Character:
                case SerializedPropertyType.ArraySize:
                    if (v is double dv && dv > long.MaxValue) { p.ulongValue = (ulong)dv; return true; }
                    if (p.type == "ulong" || p.type == "UInt64")
                        p.ulongValue = Convert.ToUInt64(v ?? 0L, CultureInfo.InvariantCulture);
                    else
                        p.longValue = Convert.ToInt64(v ?? 0L, CultureInfo.InvariantCulture);
                    return true;
                case SerializedPropertyType.Enum:
                    p.intValue = Convert.ToInt32(v ?? 0L, CultureInfo.InvariantCulture);
                    return true;
                case SerializedPropertyType.Boolean:
                    p.boolValue = v is bool b ? b : Convert.ToInt64(v ?? 0L, CultureInfo.InvariantCulture) != 0;
                    return true;
                case SerializedPropertyType.Float:
                    p.doubleValue = Convert.ToDouble(v ?? 0.0, CultureInfo.InvariantCulture);
                    return true;
                case SerializedPropertyType.String:
                    p.stringValue = v == null ? "" : Convert.ToString(v, CultureInfo.InvariantCulture);
                    return true;
                case SerializedPropertyType.ObjectReference:
                case SerializedPropertyType.ExposedReference:
                    if (v == null) { p.objectReferenceValue = null; return true; }
                    if (!(v is OrderedDict r)) { why = "expected a reference"; return false; }
                    if (!ResolveRef(r, asset, out var o)) { why = "unresolved reference " + MiniJson.Write(r); return false; }
                    p.objectReferenceValue = o;
                    return true;
            }
            if (p.isArray && v is List<object> list)
            {
                p.arraySize = list.Count;
                for (int i = 0; i < list.Count; i++)
                    if (!Assign(p.GetArrayElementAtIndex(i), list[i], asset, out why))
                        return false;
                return true;
            }
            if (p.isArray && v is string hex && p.arrayElementType == "UInt8" && hex.Length % 2 == 0)
            {
                p.arraySize = hex.Length / 2;
                for (int i = 0; i < p.arraySize; i++)
                    p.GetArrayElementAtIndex(i).intValue = Convert.ToInt32(hex.Substring(2 * i, 2), 16);
                return true;
            }
            if (v is OrderedDict d && d.Count == 0)
                return true;
            why = "unsupported property type " + p.propertyType + " (" + p.type + ")";
            return false;
        }

        static void ReadBack(SerializedObject so, string path, object wanted, string asset, StepResult res)
        {
            var p = Walk(so, path, false, out var err);
            if (p == null) { res.Fail(path, wanted, "missing: " + err); return; }
            object got = Value(p);
            if (Same(p, wanted, got, asset)) res.ReadbackOk++;
            else res.Fail(path, wanted, got);
        }

        static object Value(SerializedProperty p)
        {
            switch (p.propertyType)
            {
                case SerializedPropertyType.Integer:
                case SerializedPropertyType.LayerMask:
                case SerializedPropertyType.Character:
                case SerializedPropertyType.ArraySize:
                    return p.type == "ulong" || p.type == "UInt64" ? (object)p.ulongValue : p.longValue;
                case SerializedPropertyType.Enum: return (long)p.intValue;
                case SerializedPropertyType.Boolean: return p.boolValue;
                case SerializedPropertyType.Float: return p.doubleValue;
                case SerializedPropertyType.String: return p.stringValue;
                case SerializedPropertyType.ObjectReference:
                case SerializedPropertyType.ExposedReference:
                    var o = p.objectReferenceValue;
                    if (o == null) return new OrderedDict { ["fileID"] = 0L };
                    AssetDatabase.TryGetGUIDAndLocalFileIdentifier(o, out string g, out long id);
                    return new OrderedDict { ["fileID"] = id, ["guid"] = g };
            }
            if (p.isArray)
            {
                var l = new List<object>();
                for (int i = 0; i < p.arraySize; i++) l.Add(Value(p.GetArrayElementAtIndex(i)));
                return l;
            }
            return p.type;
        }

        static bool Same(SerializedProperty p, object wanted, object got, string asset)
        {
            if (wanted is OrderedDict r && r.Has("fileID") && got is OrderedDict g)
            {
                if (Convert.ToInt64(r.Get("fileID"), CultureInfo.InvariantCulture) == 0)
                    return Convert.ToInt64(g.Get("fileID"), CultureInfo.InvariantCulture) == 0;
                return ResolveRef(r, asset, out var o) && o == p.objectReferenceValue;
            }
            if (wanted is OrderedDict e && e.Count == 0) return true;
            if (wanted == null) return got == null || (got is string s && s.Length == 0) || (got is List<object> l && l.Count == 0);
            if (got is double gd)
                return Math.Abs(gd - Convert.ToDouble(wanted, CultureInfo.InvariantCulture)) <= 1e-6 * Math.Max(1, Math.Abs(gd));
            if (got is bool gb)
                return gb == (wanted is bool wb ? wb : Convert.ToInt64(wanted, CultureInfo.InvariantCulture) != 0);
            if (got is long || got is ulong)
                return Convert.ToDecimal(got, CultureInfo.InvariantCulture) == Convert.ToDecimal(wanted, CultureInfo.InvariantCulture);
            if (got is List<object> gl && wanted is List<object> wl)
                return gl.Count == wl.Count && Enumerable.Range(0, gl.Count).All(i =>
                    Convert.ToString(gl[i], CultureInfo.InvariantCulture) == Convert.ToString(wl[i], CultureInfo.InvariantCulture));
            return Convert.ToString(got, CultureInfo.InvariantCulture) == Convert.ToString(wanted, CultureInfo.InvariantCulture);
        }

        // ---------- object.remove ----------

        public static void ObjectRemove(OrderedDict step, StepResult res)
        {
            var target = (string)step.Get("target");
            var desc = (OrderedDict)((OrderedDict)step.Get("params")).Get("object");
            if (desc.Get("stripped") is bool stripped && stripped)
            {
                // A stripped object is the stub of a nested prefab instance's object, kept only while something in
                // this file references it. Unity drops it on save once the reference is gone; destroying it would
                // instead record a removed-component override. The boundary hash checks that it disappeared.
                res.Actions.Add($"stripped {desc.Get("class")} {desc.Get("file_id")}: no edit, follows the references to it");
                return;
            }
            var obj = Find(target, desc.Get("file_id"));
            if (obj == null)
            {
                res.Errors.Add("object " + desc.Get("file_id") + " not found in " + target);
                return;
            }
            var root = AssetDatabase.LoadMainAssetAtPath(target);
            var name = obj.GetType().Name;
            Object.DestroyImmediate(obj, true);
            if (root != null) EditorUtility.SetDirty(root);
            ClearCache();
            res.Actions.Add($"DestroyImmediate({name} {desc.Get("file_id")})");
            if (Find(target, desc.Get("file_id")) == null) res.ReadbackOk++;
            else res.Fail("object " + desc.Get("file_id"), "absent", "present");
        }

        // ---------- prefab.override ----------

        public static void PrefabOverride(OrderedDict step, StepResult res)
        {
            var target = (string)step.Get("target");
            var p = (OrderedDict)step.Get("params");
            long instanceId = Convert.ToInt64(((OrderedDict)p.Get("object")).Get("file_id"), CultureInfo.InvariantCulture);
            GameObject root = null;
            foreach (var o in Objects(target).Values)
            {
                if (!(o is GameObject go) || !PrefabUtility.IsPartOfPrefabInstance(go)) continue;
                var handle = PrefabUtility.GetPrefabInstanceHandle(go);
                if (handle != null && LocalId(handle) == instanceId)
                {
                    root = PrefabUtility.GetNearestPrefabInstanceRoot(go);
                    break;
                }
            }
            if (root == null)
            {
                res.Errors.Add("prefab instance " + instanceId + " not found in " + target);
                return;
            }
            var src = (OrderedDict)p.Get("source_prefab");
            var srcPath = src.Get("path") as string ?? AssetDatabase.GUIDToAssetPath((string)src.Get("guid"));
            var mods = (PrefabUtility.GetPropertyModifications(root) ?? new PropertyModification[0]).ToList();
            int changed = 0;
            foreach (OrderedDict o in (List<object>)p.Get("overrides_set"))
            {
                var tgt = FindInPrefabTree(srcPath, o.Get("target_file_id"));
                if (tgt == null) { res.Errors.Add("override target " + o.Get("target_file_id") + " not in " + srcPath); continue; }
                var prop = (string)o.Get("property");
                var m = mods.FirstOrDefault(x => x.target == tgt && x.propertyPath == prop);
                if (m == null) mods.Add(m = new PropertyModification { target = tgt, propertyPath = prop });
                m.value = ModValue(o.Get("value"));
                Object refObj = null;
                if (o.Get("objectReference") is OrderedDict r && !ResolveRef(r, target, out refObj))
                    res.Errors.Add("unresolved override reference " + MiniJson.Write(r));
                m.objectReference = refObj;
                changed++;
            }
            foreach (OrderedDict o in (List<object>)p.Get("overrides_removed"))
            {
                var tgt = FindInPrefabTree(srcPath, o.Get("target_file_id"));
                changed += mods.RemoveAll(x => x.target == tgt && x.propertyPath == (string)o.Get("property"));
            }
            PrefabUtility.SetPropertyModifications(root, mods.ToArray());
            EditorUtility.SetDirty(root);
            res.Actions.Add($"PrefabUtility.SetPropertyModifications({root.name}): {changed} overrides changed");
            var after = PrefabUtility.GetPropertyModifications(root) ?? new PropertyModification[0];
            foreach (OrderedDict o in (List<object>)p.Get("overrides_set"))
            {
                var tgt = FindInPrefabTree(srcPath, o.Get("target_file_id"));
                var m = after.FirstOrDefault(x => x.target == tgt && x.propertyPath == (string)o.Get("property"));
                if (m != null && (m.value ?? "") == ModValue(o.Get("value"))) res.ReadbackOk++;
                else res.Fail((string)o.Get("property"), ModValue(o.Get("value")), m?.value);
            }
        }

        /// <summary>An override target lives in the source prefab or in a prefab nested inside it.</summary>
        static Object FindInPrefabTree(string srcPath, object fileId)
        {
            var o = Find(srcPath, fileId);
            if (o != null) return o;
            foreach (var dep in AssetDatabase.GetDependencies(srcPath, true))
                if (dep != srcPath && dep.EndsWith(".prefab", StringComparison.OrdinalIgnoreCase)
                    && (o = Find(dep, fileId)) != null)
                    return o;
            return null;
        }

        static string ModValue(object v)
        {
            if (v == null) return "";
            if (v is double d) return d.ToString("R", CultureInfo.InvariantCulture);
            if (v is bool b) return b ? "1" : "0";
            return Convert.ToString(v, CultureInfo.InvariantCulture);
        }

        // ---------- importer.set ----------

        public static void ImporterSet(OrderedDict step, StepResult res)
        {
            var target = (string)step.Get("target");
            var values = (OrderedDict)((OrderedDict)step.Get("params")).Get("values");
            var imp = AssetImporter.GetAtPath(target);
            if (imp == null)
            {
                res.Errors.Add(File.Exists(ReplayCommon.Abs(target)) ? "no importer for " + target
                               : "asset not in the project (gitignored or never committed): " + target);
                return;
            }
            var so = new SerializedObject(imp);
            var applied = new List<KeyValuePair<string, object>>();
            foreach (var key in values.OrderedKeys)
            {
                // Converter paths start with the importer class name (TextureImporter.mipmaps…); properties do not.
                var path = key.Contains(".") ? key.Substring(key.IndexOf('.') + 1) : key;
                var map = new Dictionary<string, string> { ["assetBundleName"] = "m_AssetBundleName",
                    ["assetBundleVariant"] = "m_AssetBundleVariant", ["userData"] = "m_UserData" };
                if (map.TryGetValue(path, out var mapped)) path = mapped;
                if (Set(so, path, values.Get(key), target, res))
                    applied.Add(new KeyValuePair<string, object>(path, values.Get(key)));
            }
            so.ApplyModifiedPropertiesWithoutUndo();
            imp.SaveAndReimport();
            res.Actions.Add($"AssetImporter({imp.GetType().Name}).SaveAndReimport: {applied.Count} settings");
            so = new SerializedObject(AssetImporter.GetAtPath(target));
            foreach (var kv in applied) ReadBack(so, kv.Key, kv.Value, target, res);
        }

        // ---------- assets ----------

        public static void AssetMove(OrderedDict step, StepResult res)
        {
            var to = (string)step.Get("target");
            var from = (string)((OrderedDict)step.Get("params")).Get("from");
            EnsureFolder(Path.GetDirectoryName(to).Replace('\\', '/'), res);
            var guid = AssetDatabase.AssetPathToGUID(from);
            var err = AssetDatabase.MoveAsset(from, to);
            ClearCache();
            if (!string.IsNullOrEmpty(err)) { res.Errors.Add("MoveAsset: " + err); return; }
            res.Actions.Add($"AssetDatabase.MoveAsset({from} → {to})");
            if (AssetDatabase.AssetPathToGUID(to) == guid && !string.IsNullOrEmpty(guid)) res.ReadbackOk++;
            else res.Fail("guid at " + to, guid, AssetDatabase.AssetPathToGUID(to));
        }

        public static void AssetDelete(OrderedDict step, StepResult res)
        {
            var target = (string)step.Get("target");
            if (!AssetDatabase.DeleteAsset(target)) res.Errors.Add("DeleteAsset failed");
            res.Actions.Add($"AssetDatabase.DeleteAsset({target})");
            ClearCache();
            if (!File.Exists(ReplayCommon.Abs(target))) res.ReadbackOk++;
            else res.Fail(target, "absent", "present");
        }

        /// <summary>Folders the commit adds come with their .meta (written first), so only refresh is needed here.</summary>
        static void EnsureFolder(string folder, StepResult res)
        {
            if (AssetDatabase.IsValidFolder(folder)) return;
            if (Directory.Exists(ReplayCommon.Abs(folder)))
            {
                AssetDatabase.ImportAsset(folder);
                return;
            }
            res.Errors.Add("destination folder missing (its .meta is not in the commit): " + folder);
        }

        /// <summary>Copies the committed file (and its .meta when the commit has it) and imports it.</summary>
        public static void ImportFile(string path, string blob, string metaBlob, StepResult res)
        {
            var abs = ReplayCommon.Abs(path);
            Directory.CreateDirectory(Path.GetDirectoryName(abs));
            if (metaBlob != null) File.Copy(metaBlob, abs + ".meta", true);
            File.Copy(blob, abs, true);
            AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceUpdate | ImportAssetOptions.ForceSynchronousImport);
            ClearCache();
            res.Actions.Add($"AssetDatabase.ImportAsset({Path.GetFileName(path)})" + (metaBlob != null ? " with .meta" : ""));
            var main = AssetDatabase.LoadMainAssetAtPath(path);
            if (main != null) res.ReadbackOk++;
            else res.Fail(path, "loadable asset", "null");
        }
    }
}
