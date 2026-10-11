using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Debug = UnityEngine.Debug;

namespace Superposition.LiaoZhaiReplay
{
    /// <summary>
    /// Stage 3, step-level replay: executes workflow.jsonl through editor APIs, commit by commit, and verifies every
    /// file the commit touches by SHA-256 at the commit boundary.
    ///
    /// Per commit and file, the steps run as
    ///   api           SerializedObject / PrefabUtility / AssetDatabase.MoveAsset / AssetImporter, each change read back;
    ///   import        the committed source file is copied in and AssetDatabase.ImportAsset'ed (models, textures,
    ///                 new assets, tables): what an artist dropping the file into the project does;
    ///   file_fallback the step cannot be expressed (new objects need the commit's file ids, collapsed Odin byte
    ///                 overrides, truncated steps); the file is written from the commit at the boundary.
    /// At the boundary a file whose hash does not match is kept under work/mismatch/ for analysis and then restored
    /// from the commit, so every commit starts from ground truth.
    ///
    ///   Unity.exe [-batchmode] -projectPath &lt;start&gt; -executeMethod Superposition.LiaoZhaiReplay.StepReplay.Run
    ///     -replayPlan plan.json -replayWorkflow workflow.jsonl -replayLog step-log.jsonl
    ///     [-replayUntil c005] [-replayVisible] [-replayStepDelay 0.5] [-replayHandshake dir]
    /// </summary>
    public static class StepReplay
    {
        static IEnumerator<float> routine;
        static double resumeAt;
        public static ReplayStatus Status = new ReplayStatus();

        public sealed class ReplayStatus
        {
            public string Commit = "", CommitMessage = "", StepId = "", Op = "", Target = "", Mode = "", Detail = "";
            public int StepIndex, StepCount, CommitIndex, CommitCount;
            public int Exact, Mismatch, Fallback;
            public readonly List<string> Recent = new List<string>();
        }

        public static void Run()
        {
            bool visible = !Application.isBatchMode;
            try
            {
                routine = Execute(ReplayCommon.Arg("-replayPlan"), ReplayCommon.Arg("-replayWorkflow"),
                                  ReplayCommon.Arg("-replayLog"), ReplayCommon.Arg("-replayUntil"), visible,
                                  float.Parse(ReplayCommon.Arg("-replayStepDelay", "0.5"),
                                              System.Globalization.CultureInfo.InvariantCulture),
                                  ReplayCommon.Arg("-replayHandshake"));
            }
            catch (Exception e)
            {
                Debug.LogException(e);
                EditorApplication.Exit(1);
                return;
            }
            if (!visible)
            {
                int code = Drain();
                EditorApplication.Exit(code);
                return;
            }
            // No project scene stays open: the replay writes scene files, and the editor would stop on a modal
            // "modified externally" dialog for an open one.
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            ReplayWindow.Open();
            EditorApplication.update += Tick;
        }

        static int exitCode = 1;

        static int Drain()
        {
            try
            {
                while (routine.MoveNext()) { }
                return exitCode;
            }
            catch (Exception e)
            {
                Debug.LogException(e);
                return 1;
            }
        }

        static void Tick()
        {
            if (EditorApplication.timeSinceStartup < resumeAt) return;
            bool more;
            try
            {
                more = routine.MoveNext();
            }
            catch (Exception e)
            {
                Debug.LogException(e);
                more = false;
                exitCode = 1;
            }
            if (!more)
            {
                EditorApplication.update -= Tick;
                EditorApplication.Exit(exitCode);
                return;
            }
            resumeAt = EditorApplication.timeSinceStartup + routine.Current;
            ReplayWindow.RepaintAll();
        }

        static double Unix() => DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() / 1000.0;

        static IEnumerator<float> Execute(string planPath, string workflowPath, string logPath, string until,
                                          bool visible, float delay, string handshake)
        {
            var plan = JsonUtility.FromJson<FileReplay.Plan>(File.ReadAllText(planPath));
            var steps = File.ReadAllLines(workflowPath, Encoding.UTF8).Where(l => l.Trim().Length > 0)
                            .Select(l => (OrderedDict)MiniJson.Parse(l)).ToList();
            var byCommit = steps.GroupBy(s => (string)s.Get("commit")).ToDictionary(g => g.Key, g => g.ToList());
            var workDir = Path.GetDirectoryName(Path.GetFullPath(logPath));
            var mismatchDir = Path.Combine(workDir, "mismatch");
            Status.StepCount = steps.Count;
            Status.CommitCount = plan.commits.Length;

            if (handshake != null)
            {
                // The recorder waits for "ready", starts capturing, then writes "go".
                Directory.CreateDirectory(handshake);
                File.WriteAllText(Path.Combine(handshake, "ready"), Unix().ToString("F3"));
                var t0 = Unix();
                while (!File.Exists(Path.Combine(handshake, "go")) && Unix() - t0 < 120)
                    yield return 0.25f;
            }

            var total = Stopwatch.StartNew();
            int failures = 0;
            using (var log = new JsonlWriter(logPath))
            {
                log.WriteRaw(MiniJson.Write(new OrderedDict
                {
                    ["type"] = "start", ["feature"] = plan.feature, ["start_commit"] = plan.start_commit,
                    ["end_commit"] = plan.end_commit, ["steps"] = steps.Count, ["commits"] = plan.commits.Length,
                    ["visible"] = visible, ["unity"] = Application.unityVersion, ["t"] = Unix()
                }));
                foreach (var commit in plan.commits)
                {
                    Status.CommitIndex++;
                    var commitSteps = byCommit.TryGetValue(commit.id, out var cs) ? cs : new List<OrderedDict>();
                    Status.Commit = commit.id;
                    Status.CommitMessage = commitSteps.Count > 0 ? (string)commitSteps[0].Get("reason") : "";
                    var sw = Stopwatch.StartNew();
                    var writes = commit.files.Where(f => f.action == "write").ToDictionary(f => f.path);
                    var deletes = commit.files.Where(f => f.action == "delete").Select(f => f.path).ToList();

                    // A file whose steps cannot all go through editor APIs is applied from the commit as a whole.
                    var fallback = new Dictionary<string, string>();
                    foreach (var g in commitSteps.GroupBy(s => (string)s.Get("target")))
                    {
                        var why = g.Select(StepOps.WhyNotApi).FirstOrDefault(w => w != null);
                        // A rename whose old path is not in the project: the old file came from a commit outside
                        // the package (e.g. a branch merged after the start commit), so there is nothing to move.
                        why ??= g.Where(st => (string)st.Get("op") == "asset.move")
                                 .Select(st => (string)((OrderedDict)st.Get("params")).Get("from"))
                                 .Where(from => !File.Exists(ReplayCommon.Abs(from)))
                                 .Select(from => "asset.move source not in the project (added outside the package): " + from)
                                 .FirstOrDefault();
                        if (why != null) fallback[g.Key] = why;
                    }
                    var metaDone = new HashSet<string>();
                    var supportLog = Support(commit, commitSteps, writes, fallback, metaDone);
                    log.WriteRaw(MiniJson.Write(new OrderedDict
                    {
                        ["type"] = "support", ["commit"] = commit.id, ["files"] = supportLog, ["t"] = Unix()
                    }));

                    // Imports first, then API edits, each in workflow order: the order inside a commit is not
                    // observed, and API edits may reference assets the same commit creates.
                    foreach (var step in commitSteps.OrderBy(st => IsImport((string)st.Get("op")) ? 0 : 1)
                                                    .ThenBy(st => Convert.ToInt64(st.Get("seq"))))
                    {
                        Status.StepIndex++;
                        Status.StepId = (string)step.Get("id");
                        Status.Op = (string)step.Get("op");
                        Status.Target = (string)step.Get("target");
                        var t0 = Unix();
                        var res = new StepResult();
                        using (var cap = new LogCapture())
                        {
                            try
                            {
                                RunStep(step, commit, writes, fallback, metaDone, res);
                            }
                            catch (Exception e)
                            {
                                res.Errors.Add(e.GetType().Name + ": " + e.Message);
                            }
                            res.Errors.AddRange(cap.Errors.Take(10));
                        }
                        Status.Mode = res.Mode;
                        Status.Detail = res.Actions.LastOrDefault() ?? res.FallbackReason ?? "";
                        Status.Recent.Insert(0, $"{Status.StepId} {res.Mode,-13} {Status.Op} {Path.GetFileName(Status.Target)}");
                        if (Status.Recent.Count > 12) Status.Recent.RemoveAt(12);
                        if (visible && res.Mode != "file_fallback") Show(step);
                        var rec = new OrderedDict
                        {
                            ["type"] = "step", ["id"] = step.Get("id"), ["seq"] = step.Get("seq"),
                            ["commit"] = commit.id, ["op"] = step.Get("op"), ["target"] = step.Get("target"),
                            ["mode"] = res.Mode, ["fallback_reason"] = res.FallbackReason, ["ok"] = res.Ok,
                            ["actions"] = res.Actions, ["errors"] = res.Errors.Take(20).ToList(),
                            ["readback_ok"] = res.ReadbackOk, ["readback_failed"] = res.ReadbackFailed,
                            ["readback_failures"] = res.ReadbackFailures, ["t_start"] = t0, ["t_end"] = Unix()
                        };
                        log.WriteRaw(MiniJson.Write(rec));
                        yield return visible && res.Mode != "file_fallback" ? delay : 0f;
                    }

                    var boundary = Boundary(commit, commitSteps, writes, deletes, fallback, mismatchDir);
                    boundary["seconds"] = sw.Elapsed.TotalSeconds;
                    boundary["t"] = Unix();
                    failures += (int)boundary["unrecovered"];
                    log.WriteRaw(MiniJson.Write(boundary));
                    Debug.Log("[LiaoZhaiReplay] " + MiniJson.Write(boundary["counts"]));
                    yield return visible ? delay : 0f;
                    if (commit.id == until) break;
                }
                if (until == null)
                {
                    // Same end-state check as the file-level replay.
                    var fin = new OrderedDict { ["type"] = "final", ["end_commit"] = plan.end_commit };
                    var counts = new Dictionary<string, int>();
                    var bad = new List<string>();
                    foreach (var f in plan.final_check)
                    {
                        var actual = ReplayCommon.Sha256File(ReplayCommon.Abs(f.path));
                        bool ok = f.expect == "match" ? actual == f.sha256 && actual == f.replay_sha256
                                : f.expect == "changed_later" ? actual == f.replay_sha256 && actual != f.sha256
                                : actual == null;
                        var key = f.expect + (ok ? "_ok" : "_failed");
                        counts[key] = counts.TryGetValue(key, out var n) ? n + 1 : 1;
                        if (!ok && bad.Count < 100) bad.Add(f.path);
                    }
                    fin["counts"] = counts.ToDictionary(k => k.Key, k => (object)k.Value);
                    fin["unexpected"] = bad;
                    fin["total_seconds"] = total.Elapsed.TotalSeconds;
                    fin["t"] = Unix();
                    failures += bad.Count;
                    log.WriteRaw(MiniJson.Write(fin));
                    Debug.Log("[LiaoZhaiReplay] final " + MiniJson.Write(fin["counts"]));
                }
            }
            if (handshake != null)
                File.WriteAllText(Path.Combine(handshake, "done"), Unix().ToString("F3"));
            exitCode = failures == 0 ? 0 : 2;
            if (visible) yield return 2f;   // let the recorder catch the last frame
        }

        /// <summary>
        /// Files the commit changes that no step covers on its own: folder .meta files (with the folder), and .meta
        /// files of assets that already exist (GUID and importer settings as committed). .meta files of assets the
        /// commit creates go in with the asset; those of moved assets after the move.
        /// </summary>
        static List<object> Support(FileReplay.PlanCommit commit, List<OrderedDict> steps,
                                    Dictionary<string, FileReplay.PlanFile> writes, Dictionary<string, string> fallback,
                                    HashSet<string> metaDone)
        {
            var targets = new HashSet<string>(steps.Select(s => (string)s.Get("target")));
            var moved = new HashSet<string>(steps.Where(s => (string)s.Get("op") == "asset.move")
                                                 .Select(s => (string)s.Get("target")));
            var outLog = new List<object>();
            bool any = false;
            // Files the feature edits through APIs start from their state in the commit's parent: other people's
            // commits may have changed them since the feature last touched them.
            foreach (var f in writes.Values.Where(f => f.parent_sha256 != null && !fallback.ContainsKey(f.path)
                                                       && targets.Contains(f.path) && !CreatedHere(steps, f.path)))
            {
                var abs = ReplayCommon.Abs(f.path);
                if (ReplayCommon.Sha256File(abs) == f.parent_sha256) continue;
                File.Copy(f.parent_blob, abs, true);
                outLog.Add(new OrderedDict { ["path"] = f.path, ["why"] = "synced_to_parent: changed outside the feature since its last feature commit" });
                any = true;
            }
            foreach (var f in writes.Values.OrderBy(f => f.path, StringComparer.Ordinal))
            {
                string why = null;
                var owner = f.path.EndsWith(".meta", StringComparison.Ordinal) ? f.path.Substring(0, f.path.Length - 5) : f.path;
                if (fallback.TryGetValue(f.path, out var fb) || fallback.TryGetValue(owner, out fb))
                    why = "file_fallback: " + fb;    // written from the commit up front, so API edits can reference it
                else if (f.path.EndsWith(".meta", StringComparison.Ordinal))
                {
                    var asset = owner;
                    if (moved.Contains(asset)) continue;
                    bool folder = File.ReadAllText(f.blob).Contains("folderAsset: yes");
                    if (folder)
                    {
                        Directory.CreateDirectory(ReplayCommon.Abs(asset));
                        why = "folder .meta";
                    }
                    else if (File.Exists(ReplayCommon.Abs(asset)) && !CreatedHere(steps, asset))
                        why = "importer .meta of an existing asset";
                    else if (!targets.Contains(asset))
                        why = "importer .meta of an asset without steps";
                    else continue;
                }
                else if (!targets.Contains(f.path))
                    why = "file without steps";
                else if (why == null) continue;
                var abs = ReplayCommon.Abs(f.path);
                Directory.CreateDirectory(Path.GetDirectoryName(abs));
                File.Copy(f.blob, abs, true);
                metaDone.Add(f.path);
                outLog.Add(new OrderedDict { ["path"] = f.path, ["why"] = why });
                any = true;
            }
            if (any)
            {
                AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
                StepOps.ClearCache();
            }
            return outLog;
        }

        static bool IsImport(string op) =>
            op == "asset.create" || op == "asset.import" || op == "asset.replace" || op.StartsWith("table.")
            || op == "code.change" || op == "file.edit";

        static bool CreatedHere(List<OrderedDict> steps, string asset) =>
            steps.Any(s => (string)s.Get("target") == asset && ((string)s.Get("op") == "asset.create"
                                                                || (string)s.Get("op") == "asset.import"));

        static void RunStep(OrderedDict step, FileReplay.PlanCommit commit, Dictionary<string, FileReplay.PlanFile> writes,
                            Dictionary<string, string> fallback, HashSet<string> metaDone, StepResult res)
        {
            var op = (string)step.Get("op");
            var target = (string)step.Get("target");
            if (fallback.TryGetValue(target, out var why))
            {
                res.Mode = "file_fallback";
                res.FallbackReason = StepOps.WhyNotApi(step) ?? "another step on this file: " + why;
                return;
            }
            switch (op)
            {
                case "object.set": res.Mode = "api"; StepOps.ObjectSet(step, res); break;
                case "object.remove": res.Mode = "api"; StepOps.ObjectRemove(step, res); break;
                case "prefab.override": res.Mode = "api"; StepOps.PrefabOverride(step, res); break;
                case "importer.set": res.Mode = "api"; StepOps.ImporterSet(step, res); break;
                case "asset.delete": res.Mode = "api"; StepOps.AssetDelete(step, res); break;
                case "asset.move":
                    res.Mode = "api";
                    StepOps.AssetMove(step, res);
                    // A rename that also changed the .meta: the committed .meta follows the move.
                    if (writes.TryGetValue(target + ".meta", out var meta) && !metaDone.Contains(meta.path)
                        && ReplayCommon.Sha256File(ReplayCommon.Abs(meta.path)) != meta.sha256)
                    {
                        File.Copy(meta.blob, ReplayCommon.Abs(meta.path), true);
                        AssetDatabase.ImportAsset(target, ImportAssetOptions.ForceUpdate);
                        res.Actions.Add("committed .meta written after the move");
                    }
                    if (writes.ContainsKey(target + ".meta")) metaDone.Add(target + ".meta");
                    break;
                default:
                    // asset.create / asset.import / asset.replace / table.* / code.change / file.edit
                    res.Mode = "import";
                    if (!writes.TryGetValue(target, out var file))
                    {
                        res.Errors.Add("no committed file for " + target);
                        return;
                    }
                    string metaBlob = null;
                    if (writes.TryGetValue(target + ".meta", out var m) && !metaDone.Contains(m.path))
                    {
                        metaBlob = m.blob;
                        metaDone.Add(m.path);
                    }
                    StepOps.ImportFile(target, file.blob, metaBlob, res);
                    if (op == "table.edit" || op == "table.create")
                        res.Actions.Add("cells not edited through Excel; the project's 导表 export was not run (see docs)");
                    break;
            }
        }

        static OrderedDict Boundary(FileReplay.PlanCommit commit, List<OrderedDict> steps,
                                    Dictionary<string, FileReplay.PlanFile> writes, List<string> deletes,
                                    Dictionary<string, string> fallback, string mismatchDir)
        {
            AssetDatabase.SaveAssets();
            if (EditorSceneManager.GetActiveScene().isDirty)
                EditorSceneManager.SaveOpenScenes();
            if (!string.IsNullOrEmpty(EditorSceneManager.GetActiveScene().path))
            {
                // Close scenes the API steps opened before files are verified and restored on disk.
                EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
                StepOps.ClearCache();
            }
            var modeOf = new Dictionary<string, string>();
            foreach (var g in steps.GroupBy(s => (string)s.Get("target")))
            {
                var ops = g.Select(s => (string)s.Get("op")).ToList();
                modeOf[g.Key] = fallback.ContainsKey(g.Key) ? "file_fallback"
                              : ops.All(o => o.StartsWith("asset.c") || o.StartsWith("asset.i") || o == "asset.replace"
                                             || o.StartsWith("table.") || o == "code.change" || o == "file.edit")
                                  ? "import" : "api";
            }
            var files = new List<object>();
            var counts = new Dictionary<string, int>();
            var restore = new List<FileReplay.PlanFile>();
            foreach (var f in writes.Values.OrderBy(f => f.path, StringComparer.Ordinal))
            {
                var asset = f.path.EndsWith(".meta") ? f.path.Substring(0, f.path.Length - 5) : f.path;
                var mode = modeOf.TryGetValue(f.path, out var mm) ? mm
                         : f.path.EndsWith(".meta") && modeOf.TryGetValue(asset, out var am)
                             ? (am == "file_fallback" ? "file_fallback" : "meta") : "support";
                var actual = ReplayCommon.Sha256File(ReplayCommon.Abs(f.path));
                string outcome;
                if (actual == f.sha256) outcome = "exact";
                else if (mode == "file_fallback") { outcome = "fallback"; restore.Add(f); }
                else
                {
                    outcome = "mismatch";
                    restore.Add(f);
                    if (actual != null)
                    {
                        var keep = Path.Combine(mismatchDir, commit.id, f.path);
                        Directory.CreateDirectory(Path.GetDirectoryName(keep));
                        File.Copy(ReplayCommon.Abs(f.path), keep, true);
                    }
                }
                var key = mode + "_" + outcome;
                counts[key] = counts.TryGetValue(key, out var n) ? n + 1 : 1;
                files.Add(new OrderedDict { ["path"] = f.path, ["mode"] = mode, ["outcome"] = outcome,
                                            ["sha256_replay"] = actual, ["sha256_commit"] = f.sha256 });
            }
            int strayDeleted = 0;
            foreach (var d in deletes.Where(d => !writes.ContainsKey(d)))
            {
                var abs = ReplayCommon.Abs(d);
                if (!File.Exists(abs)) continue;
                File.Delete(abs);
                ReplayCommon.PruneEmptyDirs(Path.GetDirectoryName(abs));
                strayDeleted++;
            }
            foreach (var f in restore)
            {
                var abs = ReplayCommon.Abs(f.path);
                Directory.CreateDirectory(Path.GetDirectoryName(abs));
                File.Copy(f.blob, abs, true);
            }
            int unrecovered = 0;
            if (restore.Count > 0 || strayDeleted > 0)
            {
                AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
                StepOps.ClearCache();
                foreach (var f in restore)
                    if (ReplayCommon.Sha256File(ReplayCommon.Abs(f.path)) != f.sha256) unrecovered++;
            }
            Status.Exact += counts.Where(k => k.Key.EndsWith("_exact")).Sum(k => k.Value);
            Status.Mismatch += counts.Where(k => k.Key.EndsWith("_mismatch")).Sum(k => k.Value);
            Status.Fallback += counts.Where(k => k.Key.EndsWith("_fallback")).Sum(k => k.Value);
            EditorUtility.UnloadUnusedAssetsImmediate();
            return new OrderedDict
            {
                ["type"] = "commit", ["id"] = commit.id, ["sha"] = commit.sha,
                ["counts"] = counts.ToDictionary(k => k.Key, k => (object)k.Value),
                ["restored_from_commit"] = restore.Count, ["stray_deleted"] = strayDeleted,
                ["unrecovered"] = unrecovered, ["files"] = files
            };
        }

        /// <summary>Visible mode: select and ping what the step changed so the Project window and Inspector show it.</summary>
        static void Show(OrderedDict step)
        {
            var target = (string)step.Get("target");
            UnityEngine.Object obj = null;
            if (((OrderedDict)step.Get("params"))?.Get("object") is OrderedDict o && !target.EndsWith(".unity"))
            {
                StepOps.Objects(target).TryGetValue(Convert.ToInt64(o.Get("file_id")), out obj);
                if (obj is Component c) obj = c.gameObject;
            }
            var main = AssetDatabase.LoadMainAssetAtPath(target);
            if (main != null) EditorGUIUtility.PingObject(main);
            Selection.activeObject = obj != null ? obj : main;
        }
    }
}
