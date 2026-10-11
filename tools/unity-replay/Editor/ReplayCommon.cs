using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using UnityEngine;

namespace Superposition.LiaoZhaiReplay
{
    /// <summary>Command-line arguments, hashing, log capture and JSONL output shared by the replayers.</summary>
    public static class ReplayCommon
    {
        public static string Arg(string name, string fallback = null)
        {
            var args = Environment.GetCommandLineArgs();
            for (int i = 0; i < args.Length - 1; i++)
                if (args[i] == name)
                    return args[i + 1];
            return fallback;
        }

        public static bool Flag(string name) => Array.IndexOf(Environment.GetCommandLineArgs(), name) >= 0;

        /// <summary>Project root (the folder holding Assets/), with forward slashes and no trailing slash.</summary>
        public static string ProjectRoot => Path.GetDirectoryName(Application.dataPath).Replace('\\', '/');

        public static string Abs(string projectRelative) => Path.Combine(ProjectRoot, projectRelative);

        public static string Sha256File(string path)
        {
            if (!File.Exists(path))
                return null;
            using (var sha = SHA256.Create())
            using (var f = File.OpenRead(path))
                return Hex(sha.ComputeHash(f));
        }

        public static string Sha256Bytes(byte[] data)
        {
            using (var sha = SHA256.Create())
                return Hex(sha.ComputeHash(data));
        }

        static string Hex(byte[] h)
        {
            var sb = new StringBuilder(h.Length * 2);
            foreach (var b in h)
                sb.Append(b.ToString("x2"));
            return sb.ToString();
        }

        /// <summary>Removes empty folders upward from <paramref name="dir"/> while they are inside Assets/.</summary>
        public static void PruneEmptyDirs(string dir)
        {
            var assets = Path.GetFullPath(Application.dataPath);
            while (!string.IsNullOrEmpty(dir) && Directory.Exists(dir)
                   && Path.GetFullPath(dir).StartsWith(assets, StringComparison.OrdinalIgnoreCase)
                   && Path.GetFullPath(dir).Length > assets.Length
                   && Directory.GetFileSystemEntries(dir).Length == 0)
            {
                Directory.Delete(dir);
                dir = Path.GetDirectoryName(dir);
            }
        }
    }

    /// <summary>Collects editor log messages of warning level and above while active.</summary>
    public sealed class LogCapture : IDisposable
    {
        public readonly List<string> Errors = new List<string>();
        public readonly List<string> Warnings = new List<string>();
        public int ErrorCount, WarningCount;
        const int Keep = 40;

        public LogCapture() => Application.logMessageReceivedThreaded += OnLog;

        void OnLog(string message, string stack, LogType type)
        {
            lock (this)
            {
                if (type == LogType.Warning)
                {
                    WarningCount++;
                    if (Warnings.Count < Keep)
                        Warnings.Add(Trim(message));
                }
                else if (type != LogType.Log)
                {
                    ErrorCount++;
                    if (Errors.Count < Keep)
                        Errors.Add(type + ": " + Trim(message));
                }
            }
        }

        static string Trim(string s) => s.Length > 600 ? s.Substring(0, 600) + "…" : s;

        public void Dispose() => Application.logMessageReceivedThreaded -= OnLog;
    }

    /// <summary>Appends one JSON object per line, UTF-8 without BOM, flushed after every line.</summary>
    public sealed class JsonlWriter : IDisposable
    {
        readonly StreamWriter w;

        public JsonlWriter(string path, bool append = false)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path)));
            w = new StreamWriter(path, append, new UTF8Encoding(false));
        }

        public void Write(object record)
        {
            w.Write(JsonUtility.ToJson(record));
            w.Write('\n');
            w.Flush();
        }

        public void WriteRaw(string json)
        {
            w.Write(json);
            w.Write('\n');
            w.Flush();
        }

        public void Dispose() => w.Dispose();
    }
}
