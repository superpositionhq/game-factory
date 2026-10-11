using System.IO;
using UnityEditor;
using UnityEngine;

namespace Superposition.LiaoZhaiReplay
{
    /// <summary>
    /// The on-screen panel of a visible replay (stage 4): current commit, step, op, target and how it ran, so the
    /// recorded editor video can be read without the log. Video capture itself is external (Tools~/replay.py starts
    /// ffmpeg on the editor window and aligns step ids to video time from the step log's timestamps).
    /// </summary>
    public sealed class ReplayWindow : EditorWindow
    {
        GUIStyle big, mono;

        public static void Open()
        {
            // Docked as a tab next to the Scene view, inside the main editor window: the recorder captures that one
            // window, and the Project window and Inspector stay visible beside it.
            var w = GetWindow<ReplayWindow>("LiaoZhai Replay", true, typeof(SceneView));
            w.minSize = new Vector2(420, 260);
            w.Show();
        }

        public static void RepaintAll()
        {
            foreach (var w in Resources.FindObjectsOfTypeAll<ReplayWindow>())
                w.Repaint();
        }

        void OnGUI()
        {
            big ??= new GUIStyle(EditorStyles.boldLabel) { fontSize = 16, wordWrap = true };
            mono ??= new GUIStyle(EditorStyles.label) { font = Font.CreateDynamicFontFromOSFont("Consolas", 12), richText = false };
            var s = StepReplay.Status;
            GUILayout.Label($"Commit {s.Commit}  ({s.CommitIndex}/{s.CommitCount})   Step {s.StepId}  ({s.StepIndex}/{s.StepCount})", big);
            GUILayout.Label(s.CommitMessage, EditorStyles.wordWrappedLabel);
            EditorGUILayout.Space();
            GUILayout.Label($"{s.Op}   [{s.Mode}]", big);
            GUILayout.Label(s.Target, EditorStyles.wordWrappedMiniLabel);
            GUILayout.Label(s.Detail, EditorStyles.wordWrappedLabel);
            EditorGUILayout.Space();
            GUILayout.Label($"Files at commit boundaries — exact: {s.Exact}   mismatch→restored: {s.Mismatch}   from commit (fallback): {s.Fallback}");
            var r = GUILayoutUtility.GetRect(position.width - 8, 6);
            EditorGUI.ProgressBar(r, s.StepCount == 0 ? 0 : (float)s.StepIndex / s.StepCount, "");
            EditorGUILayout.Space();
            foreach (var line in s.Recent)
                GUILayout.Label(line, mono);
        }
    }
}
