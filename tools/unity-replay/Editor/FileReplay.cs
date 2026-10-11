using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using Debug = UnityEngine.Debug;

namespace Superposition.LiaoZhaiReplay
{
    /// <summary>
    /// Stage 2, file-level replay: for each feature commit in order, writes that commit's in-scope files into the
    /// project (blob by blob, prepared by Tools~/replay.py), lets the AssetDatabase import them, and checks every
    /// touched file's SHA-256 against the commit. Unity must not rewrite any of them.
    ///
    ///   Unity.exe -batchmode -projectPath &lt;start&gt; -executeMethod Superposition.LiaoZhaiReplay.FileReplay.Run
    ///             -replayPlan plan.json -replayLog replay-log.jsonl [-replayUntil c005]
    /// </summary>
    public static class FileReplay
    {
        [Serializable]
        public class PlanFile
        {
            public string action;   // "write" or "delete"
            public string path;     // project-relative, forward slashes
            public string blob;     // absolute path of the staged blob (write)
            public string sha256;   // expected SHA-256 of the file after the commit (write)
            public string status;   // git status letter(s): A, M, R100, D
            public string parent_blob;    // M only: the file in the commit's parent
            public string parent_sha256;
        }

        [Serializable]
        public class PlanCommit
        {
            public string id;
            public string sha;
            public string time;
            public PlanFile[] files;
        }

        [Serializable]
        public class FinalCheck
        {
            public string path;
            public string sha256;   // file at the end commit (null if absent there)
            public string replay_sha256;  // file after its last feature commit (null if the feature removed it)
            public string expect;   // "match", "changed_later" (outside the feature), "absent", "absent_readded_later"
        }

        [Serializable]
        public class Plan
        {
            public string feature;
            public string start_commit;
            public string end_commit;
            public PlanCommit[] commits;
            public FinalCheck[] final_check;
        }

        [Serializable]
        class CommitLog
        {
            public string type = "commit";
            public string id, sha, time;
            public int files_written, files_deleted;
            public int base_differs_from_parent;   // modified files changed outside the feature before this commit
            public string[] base_differs;
            public double apply_seconds, import_seconds, verify_seconds;
            public int hash_ok, hash_mismatch, delete_ok, delete_failed;
            public string[] mismatches;
            public int import_errors, import_warnings;
            public string[] errors, warnings;
            public int assets_loaded, assets_not_loadable;
            public string[] not_loadable;
            public int prefabs_checked, prefabs_with_missing_scripts, missing_scripts;
            public string[] missing_script_prefabs;
        }

        [Serializable]
        class FinalLog
        {
            public string type = "final";
            public string end_commit;
            public int checked_files, match, match_expected, changed_later_expected, changed_later_as_expected;
            public int absent_expected, absent_ok, unexpected;
            public string[] unexpected_detail;
            public double total_seconds;
        }

        public static void Run()
        {
            int code = 1;
            try
            {
                code = Execute(ReplayCommon.Arg("-replayPlan"), ReplayCommon.Arg("-replayLog"),
                               ReplayCommon.Arg("-replayUntil"));
            }
            catch (Exception e)
            {
                Debug.LogException(e);
            }
            EditorApplication.Exit(code);
        }

        public static int Execute(string planPath, string logPath, string until)
        {
            var plan = JsonUtility.FromJson<Plan>(File.ReadAllText(planPath));
            var total = Stopwatch.StartNew();
            int failures = 0;
            using (var log = new JsonlWriter(logPath))
            {
                foreach (var c in plan.commits)
                {
                    var rec = ApplyCommit(c);
                    failures += rec.hash_mismatch + rec.delete_failed;
                    log.Write(rec);
                    Debug.Log($"[LiaoZhaiReplay] {c.id} written={rec.files_written} deleted={rec.files_deleted} " +
                              $"hash_ok={rec.hash_ok} mismatch={rec.hash_mismatch} import_errors={rec.import_errors} " +
                              $"import={rec.import_seconds:F1}s");
                    if (c.id == until)
                        return failures == 0 ? 0 : 2;
                }
                var fin = Final(plan);
                fin.total_seconds = total.Elapsed.TotalSeconds;
                failures += fin.unexpected;
                log.Write(fin);
                Debug.Log($"[LiaoZhaiReplay] final: checked={fin.checked_files} match={fin.match} " +
                          $"changed_later={fin.changed_later_as_expected}/{fin.changed_later_expected} " +
                          $"absent={fin.absent_ok}/{fin.absent_expected} unexpected={fin.unexpected}");
            }
            return failures == 0 ? 0 : 2;
        }

        static CommitLog ApplyCommit(PlanCommit c)
        {
            var rec = new CommitLog { id = c.id, sha = c.sha, time = c.time };
            var sw = Stopwatch.StartNew();
            var deletes = c.files.Where(f => f.action == "delete").ToList();
            var writes = c.files.Where(f => f.action == "write").ToList();

            // Deletes first: a rename deletes its old path, and the new path may sit in a folder the commit removes.
            foreach (var f in deletes)
            {
                var abs = ReplayCommon.Abs(f.path);
                if (File.Exists(abs))
                    File.Delete(abs);
                rec.files_deleted++;
            }
            foreach (var f in deletes)
                ReplayCommon.PruneEmptyDirs(Path.GetDirectoryName(ReplayCommon.Abs(f.path)));
            var differs = writes.Where(f => f.parent_sha256 != null
                                            && ReplayCommon.Sha256File(ReplayCommon.Abs(f.path)) != f.parent_sha256)
                                .Select(f => f.path).ToList();
            rec.base_differs_from_parent = differs.Count;
            rec.base_differs = differs.Take(40).ToArray();
            foreach (var f in writes)
            {
                var abs = ReplayCommon.Abs(f.path);
                Directory.CreateDirectory(Path.GetDirectoryName(abs));
                File.Copy(f.blob, abs, true);
                rec.files_written++;
            }
            rec.apply_seconds = sw.Elapsed.TotalSeconds;

            sw.Restart();
            using (var cap = new LogCapture())
            {
                AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
                rec.import_errors = cap.ErrorCount;
                rec.import_warnings = cap.WarningCount;
                rec.errors = cap.Errors.ToArray();
                rec.warnings = cap.Warnings.ToArray();
            }
            rec.import_seconds = sw.Elapsed.TotalSeconds;

            sw.Restart();
            var mismatches = new List<string>();
            foreach (var f in writes)
            {
                var actual = ReplayCommon.Sha256File(ReplayCommon.Abs(f.path));
                if (actual == f.sha256)
                    rec.hash_ok++;
                else
                {
                    rec.hash_mismatch++;
                    mismatches.Add($"{f.path} expected={f.sha256} actual={actual ?? "missing"}");
                }
            }
            foreach (var f in deletes)
            {
                if (writes.Any(w => w.path == f.path))
                    continue;
                if (File.Exists(ReplayCommon.Abs(f.path)))
                {
                    rec.delete_failed++;
                    mismatches.Add($"{f.path} expected=absent actual=present");
                }
                else
                    rec.delete_ok++;
            }
            rec.mismatches = mismatches.ToArray();
            CheckAssets(writes, rec);
            rec.verify_seconds = sw.Elapsed.TotalSeconds;
            return rec;
        }

        /// <summary>Loads every written asset and counts missing MonoBehaviour scripts on prefabs.</summary>
        static void CheckAssets(List<PlanFile> writes, CommitLog rec)
        {
            var notLoadable = new List<string>();
            var missing = new List<string>();
            foreach (var f in writes)
            {
                if (f.path.EndsWith(".meta", StringComparison.OrdinalIgnoreCase))
                    continue;
                var main = AssetDatabase.LoadMainAssetAtPath(f.path);
                if (main == null)
                {
                    rec.assets_not_loadable++;
                    if (notLoadable.Count < 40)
                        notLoadable.Add(f.path);
                    continue;
                }
                rec.assets_loaded++;
                if (main is GameObject go && f.path.EndsWith(".prefab", StringComparison.OrdinalIgnoreCase))
                {
                    rec.prefabs_checked++;
                    int n = go.GetComponentsInChildren<Transform>(true)
                              .Sum(t => GameObjectUtility.GetMonoBehavioursWithMissingScriptCount(t.gameObject));
                    if (n > 0)
                    {
                        rec.prefabs_with_missing_scripts++;
                        rec.missing_scripts += n;
                        if (missing.Count < 40)
                            missing.Add($"{f.path} ({n})");
                    }
                }
            }
            rec.not_loadable = notLoadable.ToArray();
            rec.missing_script_prefabs = missing.ToArray();
            EditorUtility.UnloadUnusedAssetsImmediate();
        }

        static FinalLog Final(Plan plan)
        {
            var fin = new FinalLog { end_commit = plan.end_commit };
            var bad = new List<string>();
            foreach (var f in plan.final_check)
            {
                fin.checked_files++;
                var actual = ReplayCommon.Sha256File(ReplayCommon.Abs(f.path));
                switch (f.expect)
                {
                    case "match":
                        fin.match_expected++;
                        if (actual == f.sha256 && actual == f.replay_sha256) fin.match++;
                        else bad.Add($"{f.path} expect=match end={f.sha256} actual={actual ?? "missing"}");
                        break;
                    case "changed_later":
                        // The file's last feature change is in place, but a later commit outside the feature
                        // changed it before the end commit, so it must differ from the end commit.
                        fin.changed_later_expected++;
                        if (actual == f.replay_sha256 && actual != f.sha256) fin.changed_later_as_expected++;
                        else bad.Add($"{f.path} expect=changed_later end={f.sha256} actual={actual ?? "missing"}");
                        break;
                    case "absent":
                    case "absent_readded_later":  // removed by the feature, added back outside it before the end
                        fin.absent_expected++;
                        if (actual == null) fin.absent_ok++;
                        else bad.Add($"{f.path} expect=absent actual={actual}");
                        break;
                }
            }
            fin.unexpected = bad.Count;
            fin.unexpected_detail = bad.Take(100).ToArray();
            return fin;
        }
    }
}
