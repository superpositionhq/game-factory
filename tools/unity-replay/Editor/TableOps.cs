using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Reflection;
using System.Xml;
using UnityEditor;
using Object = UnityEngine.Object;

namespace Superposition.LiaoZhaiReplay
{
    /// <summary>
    /// table.edit through the project's own pipeline: the cells are edited in the workbook, read back with the
    /// project's Excel reader (ExcelDataReader), and the project's 导表 export (LiaoZhaiRL.Tools.Excel.FeishuImporter)
    /// is run before and after the edit. The database delta it produces is compared with the delta of the real
    /// export commit (FileReplay.TableExport), since the replay project lacks other people's table changes.
    ///
    /// The export is the importer's own sequence (ExecuteExecelFile per workbook, the DIALOG merge, ImportBG per
    /// table, FKImport, which saves the BGDatabase) without its table examiner: the examiner's dialogs would answer
    /// "发送" in batchmode and post to the team's chat through FeishuImporter.SendMessage.
    /// Everything is called by reflection: the project's editor assembly cannot be referenced from a package.
    /// </summary>
    public static class TableOps
    {
        const string Folder = "Assets/LiaoZhaiRL/墨境导表文件夹";

        public static void TableEdit(OrderedDict step, FileReplay.TableExport export, StepResult res)
        {
            var target = (string)step.Get("target");
            var p = (OrderedDict)step.Get("params");
            var cells = ((List<object>)p.Get("cells")).Cast<OrderedDict>().ToList();
            if (p.Get("truncated") is bool t && t)
                res.Errors.Add("table.edit truncated: only the listed cells are edited");
            var xlsx = ReplayCommon.Abs(target);

            foreach (var c in cells)
                CheckCell(xlsx, c, "before", res);

            bool compare = export != null && !string.IsNullOrEmpty(export.sha);
            string dbAbs = compare ? ReplayCommon.Abs(export.path) : null;
            byte[] dbOriginal = compare && File.Exists(dbAbs) ? File.ReadAllBytes(dbAbs) : null;
            try
            {
                byte[] db0 = null;
                if (compare)
                {
                    db0 = Export(dbAbs, res);
                    res.Actions.Add($"导表 export before the edit: {db0?.Length ?? 0} bytes");
                }

                foreach (var c in cells)
                    EditCell(xlsx, (string)c.Get("sheet"), Convert.ToInt32(c.Get("row")), Convert.ToInt32(c.Get("col")),
                             c.Get("after"));
                res.Actions.Add($"workbook XML: {cells.Count} cell(s) set");
                foreach (var c in cells)
                    CheckCell(xlsx, c, "after", res);

                if (!compare)
                {
                    res.Actions.Add("no export commit found for this table edit; export not compared");
                    return;
                }
                var db1 = Export(dbAbs, res);
                res.Actions.Add($"导表 export after the edit: {db1?.Length ?? 0} bytes");
                if (db0 != null && db1 != null)
                {
                    // The database starts with a value that changes on every save, so bytes are compared by content:
                    // the size change, and how often each edited cell's old and new text occurs, before vs after,
                    // in the replay's exports and in the real export commit.
                    var rb = File.ReadAllBytes(export.before_blob);
                    var ra = File.ReadAllBytes(export.after_blob);
                    var mine = new List<string> { $"size {db1.Length - db0.Length:+0;-0}" };
                    var real = new List<string> { $"size {ra.Length - rb.Length:+0;-0}" };
                    foreach (var c in cells)
                        foreach (var which in new[] { "before", "after" })
                        {
                            var text = Convert.ToString(c.Get(which) ?? "", CultureInfo.InvariantCulture);
                            if (text.Length == 0) continue;
                            var bytes = System.Text.Encoding.UTF8.GetBytes(text);
                            mine.Add($"{which} \"{text}\" {Count(db1, bytes) - Count(db0, bytes):+0;-0}");
                            real.Add($"{which} \"{text}\" {Count(ra, bytes) - Count(rb, bytes):+0;-0}");
                        }
                    bool same = mine.SequenceEqual(real);
                    res.Actions.Add($"export {(same ? "matches" : "differs from")} commit {export.sha.Substring(0, 10)} " +
                                    $"\"{export.message}\": replay [{string.Join(", ", mine)}], commit [{string.Join(", ", real)}]");
                    if (same) res.ReadbackOk++;
                    else res.Fail("导表 export change", string.Join(", ", real), string.Join(", ", mine));
                }
            }
            finally
            {
                // The database is not a feature file: put it back as it was before the replay's exports.
                if (dbOriginal != null)
                {
                    File.WriteAllBytes(dbAbs, dbOriginal);
                    AssetDatabase.ImportAsset(export.path, ImportAssetOptions.ForceUpdate);
                }
            }
        }

        // ---------- workbook ----------

        static void CheckCell(string xlsx, OrderedDict c, string which, StepResult res)
        {
            var got = ReadCell(xlsx, (string)c.Get("sheet"), Convert.ToInt32(c.Get("row")), Convert.ToInt32(c.Get("col")), res);
            var want = c.Get(which);
            if (Convert.ToString(got ?? "", CultureInfo.InvariantCulture) == Convert.ToString(want ?? "", CultureInfo.InvariantCulture))
                res.ReadbackOk++;
            else
                res.Fail($"{c.Get("sheet")}!R{c.Get("row")}C{c.Get("col")} ({which})", want, got);
        }

        /// <summary>A cell as the project's importer reads it (ExcelDataReader, row and column 1-based).</summary>
        static object ReadCell(string xlsx, string sheet, int row, int col, StepResult res)
        {
            var factory = FindType("ExcelDataReader.ExcelReaderFactory");
            if (factory == null) { res.Errors.Add("ExcelDataReader not loaded"); return null; }
            var create = factory.GetMethods().First(m => m.Name == "CreateReader" && m.GetParameters().Length == 2);
            using (var stream = File.Open(xlsx, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
            using (var reader = (System.Data.IDataReader)create.Invoke(null, new object[] { stream, null }))
            {
                var nameProp = reader.GetType().GetProperty("Name");
                do
                {
                    if ((string)nameProp.GetValue(reader) != sheet) continue;
                    for (int r = 1; reader.Read(); r++)
                        if (r == row)
                            return col - 1 < reader.FieldCount ? reader.GetValue(col - 1) : null;
                    return null;
                } while (reader.NextResult());
            }
            res.Errors.Add("sheet not found: " + sheet);
            return null;
        }

        /// <summary>Sets one cell in the sheet XML of an .xlsx (inline string, or number for numeric values).</summary>
        static void EditCell(string xlsx, string sheet, int row, int col, object value)
        {
            const string ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main";
            const string rns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships";
            using (var fs = new FileStream(xlsx, FileMode.Open, FileAccess.ReadWrite))
            using (var zip = new ZipArchive(fs, ZipArchiveMode.Update))
            {
                var wb = Load(zip, "xl/workbook.xml");
                var m = new XmlNamespaceManager(wb.NameTable);
                m.AddNamespace("x", ns);
                m.AddNamespace("r", rns);
                var sheetEl = (XmlElement)wb.SelectSingleNode($"//x:sheets/x:sheet[@name='{sheet}']", m);
                var rid = sheetEl.GetAttribute("id", rns);
                var rels = Load(zip, "xl/_rels/workbook.xml.rels");
                var rm = new XmlNamespaceManager(rels.NameTable);
                rm.AddNamespace("p", "http://schemas.openxmlformats.org/package/2006/relationships");
                var targetPath = ((XmlElement)rels.SelectSingleNode($"//p:Relationship[@Id='{rid}']", rm)).GetAttribute("Target");
                var entryName = targetPath.StartsWith("/") ? targetPath.Substring(1) : "xl/" + targetPath;

                var doc = Load(zip, entryName);
                var sm = new XmlNamespaceManager(doc.NameTable);
                sm.AddNamespace("x", ns);
                var reference = ColumnName(col) + row.ToString(CultureInfo.InvariantCulture);
                var data = (XmlElement)doc.SelectSingleNode("//x:sheetData", sm);
                var rowEl = (XmlElement)data.SelectSingleNode($"x:row[@r='{row}']", sm);
                if (rowEl == null)
                {
                    rowEl = doc.CreateElement("row", ns);
                    rowEl.SetAttribute("r", row.ToString(CultureInfo.InvariantCulture));
                    data.AppendChild(rowEl);
                }
                var cell = (XmlElement)rowEl.SelectSingleNode($"x:c[@r='{reference}']", sm);
                if (cell == null)
                {
                    cell = doc.CreateElement("c", ns);
                    cell.SetAttribute("r", reference);
                    rowEl.AppendChild(cell);
                }
                var style = cell.GetAttribute("s");
                cell.RemoveAll();
                cell.SetAttribute("r", reference);
                if (style.Length > 0) cell.SetAttribute("s", style);
                if (value is long || value is double)
                {
                    var v = doc.CreateElement("v", ns);
                    v.InnerText = Convert.ToString(value, CultureInfo.InvariantCulture);
                    cell.AppendChild(v);
                }
                else if (value != null)
                {
                    cell.SetAttribute("t", "inlineStr");
                    var isEl = doc.CreateElement("is", ns);
                    var tEl = doc.CreateElement("t", ns);
                    tEl.InnerText = Convert.ToString(value, CultureInfo.InvariantCulture);
                    isEl.AppendChild(tEl);
                    cell.AppendChild(isEl);
                }
                Save(zip, entryName, doc);
            }
        }

        static string ColumnName(int col)
        {
            var s = "";
            for (; col > 0; col = (col - 1) / 26)
                s = (char)('A' + (col - 1) % 26) + s;
            return s;
        }

        static XmlDocument Load(ZipArchive zip, string name)
        {
            var doc = new XmlDocument();
            using (var s = zip.GetEntry(name).Open())
                doc.Load(s);
            return doc;
        }

        static void Save(ZipArchive zip, string name, XmlDocument doc)
        {
            zip.GetEntry(name).Delete();
            using (var s = zip.CreateEntry(name, CompressionLevel.Optimal).Open())
                doc.Save(s);
        }

        // ---------- the project's 导表 export ----------

        static byte[] Export(string dbAbs, StepResult res)
        {
            var t = FindType("LiaoZhaiRL.Tools.Excel.FeishuImporter");
            if (t == null) { res.Errors.Add("FeishuImporter not found"); return null; }
            var imp = Activator.CreateInstance(t);
            var exec = t.GetMethod("ExecuteExecelFile");
            var importBG = t.GetMethod("ImportBG");
            var fkImport = t.GetMethod("FKImport");
            var folder = Path.GetFullPath(ReplayCommon.Abs(Folder));    // backslash paths, as the importer expects
            var files = new DirectoryInfo(folder).GetFiles()
                .Where(f => !f.FullName.Contains(".meta") && !f.FullName.Contains("~")).Select(f => f.FullName);

            var data = new List<object>();
            var dialog = new List<object>();
            foreach (var file in files)
                foreach (var kv in (IEnumerable)exec.Invoke(imp, new object[] { file }))
                {
                    if (((string)Get(Key(kv), "tableName")).Contains("DIALOG")) dialog.Add(kv);
                    else data.Add(kv);
                }

            // FeishuImporter.ImportTableFromLocalFileAsync: all DIALOG sheets merge into the first one.
            if (dialog.Count > 0)
            {
                var k0 = Key(dialog[0]);
                Set(k0, "tableName", "DIALOG_CONTENT");
                Set(k0, "tableCNName", "对话_文本");
                var f0 = (IList)Get(k0, "dataFields");
                for (int i = 1; i < dialog.Count; i++)
                {
                    var ki = Key(dialog[i]);
                    var fi = (IList)Get(ki, "dataFields");
                    for (int j = 0; j < fi.Count; j++)
                    {
                        try { AddRange((IList)Get(f0[j], "dataValues"), (IList)Get(fi[j], "dataValues")); }
                        catch (Exception) { /* the importer logs and continues */ }
                        AddRange((IList)Get(k0, "extremeRowIndexList"), (IList)Get(ki, "extremeRowIndexList"));
                    }
                }
                var v0 = (IList)Value(dialog[0]);
                for (int i = 1; i < dialog.Count; i++)
                {
                    var vi = (IList)Value(dialog[i]);
                    for (int j = 0; j < vi.Count; j++)
                        AddRange((IList)Get(v0[j], "dataValues"), (IList)Get(vi[j], "dataValues"));
                }
                data.Add(dialog[0]);
            }

            var fk = (IList)Activator.CreateInstance(fkImport.GetParameters()[0].ParameterType);
            using (var cap = new LogCapture())
            {
                foreach (var kv in data)
                    if (importBG.Invoke(imp, new[] { Key(kv), Value(kv) }) is IList added)
                        foreach (var x in added) fk.Add(x);
                fkImport.Invoke(imp, new object[] { fk });     // ends with BGRepo.Save(), which only serializes
                // DatabaseImporterEditor then saves through the BGDatabase window (SaveBGDataRepo); this is the
                // same save without the window. Code generation (Generated.cs) is skipped: it recompiles scripts.
                var backups = Path.Combine(ReplayCommon.ProjectRoot, "BGDatabaseAutoBackups");
                var before = Directory.Exists(backups) ? new HashSet<string>(Directory.GetFiles(backups, "*", SearchOption.AllDirectories)) : new HashSet<string>();
                var saver = FindType("BansheeGz.BGDatabase.Editor.BGRepoSaver");
                saver.GetMethod("SaveRepo", BindingFlags.Public | BindingFlags.Static).Invoke(null, new object[] { null });
                if (Directory.Exists(backups))
                    foreach (var f in Directory.GetFiles(backups, "*", SearchOption.AllDirectories))
                        if (!before.Contains(f)) File.Delete(f);
                if (cap.ErrorCount > 0)
                    res.Actions.Add($"export logged {cap.ErrorCount} error(s), first: {cap.Errors.FirstOrDefault()}");
            }
            return File.Exists(dbAbs) ? File.ReadAllBytes(dbAbs) : null;
        }

        static object Key(object kv) => kv.GetType().GetProperty("Key").GetValue(kv);
        static object Value(object kv) => kv.GetType().GetProperty("Value").GetValue(kv);

        static object Get(object o, string name)
        {
            var t = o.GetType();
            var f = t.GetField(name, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            return f != null ? f.GetValue(o) : t.GetProperty(name, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance)?.GetValue(o);
        }

        static void Set(object o, string name, object v)
        {
            var t = o.GetType();
            var f = t.GetField(name, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
            if (f != null) f.SetValue(o, v);
            else t.GetProperty(name, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance)?.SetValue(o, v);
        }

        static void AddRange(IList to, IList from)
        {
            foreach (var x in from.Cast<object>().ToList()) to.Add(x);
        }

        static Type FindType(string name) =>
            AppDomain.CurrentDomain.GetAssemblies().Select(a => a.GetType(name, false)).FirstOrDefault(x => x != null);

        // ---------- database content ----------

        static int Count(byte[] hay, byte[] needle)
        {
            int n = 0;
            for (int i = 0; i + needle.Length <= hay.Length; i++)
            {
                int j = 0;
                while (j < needle.Length && hay[i + j] == needle[j]) j++;
                if (j == needle.Length) { n++; i += needle.Length - 1; }
            }
            return n;
        }
    }
}
